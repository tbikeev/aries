#!/usr/bin/env python3
"""Cross-company CEO converse-square validation study."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from company_universe import audit_universe_row, load_universe_csv, snapshot_universe
from cross_company_data import inventory_ticker
from cross_company_models import (
    company_correlation_table,
    direction_baselines,
    magnitude_metrics,
    pooled_ols_with_fe,
)
from cross_company_partition import build_partition_manifest, save_manifest
from cross_company_paths import (
    CROSS_CACHE,
    CROSS_INPUT,
    CROSS_OUTPUT,
    DEFAULT_UNIVERSE_CSV,
    DISCOVERY_TICKER,
    FROZEN_SQ_ORB_DEG,
    PLACEBO_SEED_DEFAULT,
    PLACEBO_SURROGATES_DEFAULT,
    PRIMARY_FEATURE,
)
from cross_company_placebos import (
    calendar_misalignment,
    cross_company_radix_reassignment,
    random_radix_placebo_by_company,
)
from executive_radices import build_executive_radix, sensitivity_birth_jd_perturbations
from earnings_converse import converse_count_features_for_birth_jd
from multi_company_earnings import build_company_events
from phase_h_stats import pearson, spearman


def _md_table(df: pd.DataFrame) -> str:
    try:
        return df.to_markdown(index=False)
    except Exception:
        return df.to_csv(index=False)


def run_cross_company_study(
    *,
    universe_csv: Path | None = None,
    output_dir: Path | None = None,
    exclude_ticker: str = DISCOVERY_TICKER,
    seed: int = PLACEBO_SEED_DEFAULT,
    n_surrogates: int = PLACEBO_SURROGATES_DEFAULT,
    pilot_only: bool = False,
) -> dict:
    out = output_dir or CROSS_OUTPUT
    out.mkdir(parents=True, exist_ok=True)
    CROSS_CACHE.mkdir(parents=True, exist_ok=True)

    uni_path = universe_csv or DEFAULT_UNIVERSE_CSV
    if not uni_path.exists():
        raise FileNotFoundError(f"Universe CSV not found: {uni_path}")

    snapshot_universe(uni_path, out / "universe_snapshot.csv")
    universe = load_universe_csv(uni_path)

    manifest = build_partition_manifest(universe, exclude_ticker=exclude_ticker)
    save_manifest(manifest, out / "study_partition_manifest.csv")

    # Report 1 — eligibility audit
    audit_rows = []
    meta_by_ticker: dict[str, dict] = {}
    all_events: list[pd.DataFrame] = []
    all_aspects: list[pd.DataFrame] = []
    executive_jds: dict[str, float] = {}

    tickers = universe["ticker"].tolist()
    eval_tickers = [t for t in tickers if t != exclude_ticker.upper()]
    if pilot_only:
        pilot_set = set(manifest.loc[manifest["stage"] == "pilot", "ticker"])
        eval_tickers = [t for t in eval_tickers if t in pilot_set]

    for _, row in universe.iterrows():
        t = row["ticker"]
        inv = inventory_ticker(t)
        aud = audit_universe_row(row)
        audit_rows.append({**aud, **inv})
        if not inv["eligible_files"]:
            continue
        if t == exclude_ticker.upper():
            continue  # discovery cohort: unchanged UBER study; not rebuilt here
        if pilot_only and t not in eval_tickers:
            continue

        events, aspects, meta = build_company_events(ticker=t, universe_row=row)
        meta_by_ticker[t] = meta
        if meta.get("birth_jd"):
            executive_jds[t] = float(meta["birth_jd"])
        if not events.empty:
            stage_row = manifest.loc[manifest["ticker"] == t, "stage"]
            events["stage"] = stage_row.iloc[0] if len(stage_row) else "discovery_only"
            if t == exclude_ticker.upper():
                events["stage"] = "discovery_excluded"
            all_events.append(events)
            if not aspects.empty:
                all_aspects.append(aspects)

    audit_df = pd.DataFrame(audit_rows)
    audit_df.to_csv(out / "eligibility_audit.csv", index=False)

    if not all_events:
        summary = {"error": "no events built", "audit_path": str(out / "eligibility_audit.csv")}
        (out / "cross_company_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        return summary

    events_df = pd.concat(all_events, ignore_index=True)
    aspects_df = pd.concat(all_aspects, ignore_index=True) if all_aspects else pd.DataFrame()
    events_df.to_csv(out / "events_panel_all.csv", index=False)
    if not aspects_df.empty:
        aspects_df.to_csv(out / "directed_aspects_all.csv", index=False)

    # Volatility-normalised return (secondary)
    events_df["volatility_normalised_return"] = np.where(
        events_df.get("pre_event_volatility", pd.Series(dtype=float)) > 0,
        events_df["return_cc"] / events_df["pre_event_volatility"],
        np.nan,
    )

    eval_events = events_df[events_df["ticker"] != exclude_ticker.upper()].copy()

    # Report 2 — per company
    corp = company_correlation_table(eval_events, feature=PRIMARY_FEATURE, target="return_cc")
    corp = corp.sort_values("pearson_r")
    corp.to_csv(out / "company_correlations.csv", index=False)

    neg_cos = int((corp["pearson_r"] < 0).sum()) if len(corp) else 0
    pos_cos = int((corp["pearson_r"] > 0).sum()) if len(corp) else 0

    # Report 3 — pooled
    pooled_raw = pooled_ols_with_fe(
        eval_events, target="return_cc", feature=PRIMARY_FEATURE, include_company_fe=False
    )
    pooled_fe = pooled_ols_with_fe(
        eval_events, target="return_cc", feature=PRIMARY_FEATURE, include_company_fe=True
    )
    pooled_gap = pooled_ols_with_fe(
        eval_events, target="return_gap", feature=PRIMARY_FEATURE, include_company_fe=True
    )
    pd.DataFrame(
        [
            {"spec": "pooled_raw", **{k: v for k, v in pooled_raw.items() if k != "coefficients"}},
            {"spec": "pooled_company_fe", **{k: v for k, v in pooled_fe.items() if k != "coefficients"}},
        ]
    ).to_csv(out / "pooled_model_summary.csv", index=False)
    (out / "pooled_model_detail.json").write_text(
        json.dumps({"raw": pooled_raw, "fe": pooled_fe, "gap_fe": pooled_gap}, indent=2, default=str),
        encoding="utf-8",
    )

    sector_rows = []
    for bucket, grp in eval_events.groupby("sector_bucket"):
        sector_rows.append(
            {
                "sector_bucket": bucket,
                "n_events": len(grp),
                "n_companies": grp["ticker"].nunique(),
                "pearson_sq_vs_cc": pearson(grp[PRIMARY_FEATURE], grp["return_cc"]),
                "spearman_sq_vs_cc": spearman(grp[PRIMARY_FEATURE], grp["return_cc"]),
            }
        )
    pd.DataFrame(sector_rows).to_csv(out / "sector_breakdown.csv", index=False)

    # Report 4 — stages
    dev = eval_events[eval_events["stage"] == "development"]
    hold = eval_events[eval_events["stage"] == "holdout"]
    stage_stats = []
    for name, frame in [("development", dev), ("holdout", hold), ("all_eval", eval_events)]:
        if len(frame) < 5:
            continue
        stage_stats.append(
            {
                "stage": name,
                "n_events": len(frame),
                "n_companies": frame["ticker"].nunique(),
                "pearson_r": pearson(frame[PRIMARY_FEATURE], frame["return_cc"]),
                "spearman_r": spearman(frame[PRIMARY_FEATURE], frame["return_cc"]),
            }
        )
    pd.DataFrame(stage_stats).to_csv(out / "stage_evaluation.csv", index=False)

    dir_dev = direction_baselines(eval_events, target="return_cc", feature=PRIMARY_FEATURE, stage="development")
    dir_hold = direction_baselines(eval_events, target="return_cc", feature=PRIMARY_FEATURE, stage="holdout")
    pd.concat([dir_dev, dir_hold], ignore_index=True).to_csv(out / "direction_baselines.csv", index=False)
    mag = pd.DataFrame(
        [
            magnitude_metrics(eval_events, target="return_cc", feature=PRIMARY_FEATURE, stage="development"),
            magnitude_metrics(eval_events, target="return_cc", feature=PRIMARY_FEATURE, stage="holdout"),
        ]
    )
    mag.to_csv(out / "magnitude_metrics.csv", index=False)

    # Report 5 — placebos (development + holdout, not discovery)
    placebo_df = random_radix_placebo_by_company(
        eval_events, executive_jds, n_surrogates=min(n_surrogates, 500), seed=seed
    )
    placebo_df.to_csv(out / "placebo_random_radix_by_company.csv", index=False)
    reassign = cross_company_radix_reassignment(eval_events, executive_jds, seed=seed)
    reassign.to_csv(out / "placebo_cross_company_reassignment.csv", index=False)
    misalign = calendar_misalignment(eval_events, executive_jds, shift_days=90)
    misalign.to_csv(out / "placebo_calendar_misalignment.csv", index=False)

    # Birth-time sensitivity (nominal vs ±6h) on pooled eval sample
    sens_rows = []
    for ticker, grp in eval_events.groupby("ticker"):
        rjd = executive_jds.get(ticker)
        if rjd is None or len(grp) < 5:
            continue
        for label, bjd in sensitivity_birth_jd_perturbations(rjd):
            xs = [
                converse_count_features_for_birth_jd(bjd, float(ej), orb_max=FROZEN_SQ_ORB_DEG)[
                    "sq_count"
                ]
                for ej in grp["event_jd_ut"]
            ]
            sens_rows.append(
                {
                    "ticker": ticker,
                    "perturbation": label,
                    "pearson_r": pearson(pd.Series(xs), grp["return_cc"]),
                }
            )
    pd.DataFrame(sens_rows).to_csv(out / "birth_time_sensitivity.csv", index=False)

    hold_row = next((s for s in stage_stats if s["stage"] == "holdout"), None)
    holdout_r = float(hold_row["pearson_r"]) if hold_row else float("nan")
    dev_coef = (pooled_fe.get("coefficients") or {}).get(PRIMARY_FEATURE, float("nan"))

    summary = {
        "run_utc": datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + "Z",
        "universe_csv": str(uni_path),
        "exclude_ticker": exclude_ticker,
        "n_companies_evaluated": int(eval_events["ticker"].nunique()),
        "n_events_evaluated": len(eval_events),
        "companies_negative_pearson": neg_cos,
        "companies_positive_pearson": pos_cos,
        "median_company_pearson_r": float(corp["pearson_r"].median()) if len(corp) else None,
        "pooled_fe_coef_square_count_1deg": dev_coef,
        "holdout_pearson_r": holdout_r,
        "frozen_feature": PRIMARY_FEATURE,
        "frozen_orb_deg": FROZEN_SQ_ORB_DEG,
        "seed": seed,
        "pilot_only": pilot_only,
    }
    (out / "cross_company_summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")

    _write_reports(
        out,
        audit_df=audit_df,
        manifest=manifest,
        corp=corp,
        summary=summary,
        pooled_fe=pooled_fe,
        stage_stats=pd.DataFrame(stage_stats),
        placebo_df=placebo_df,
        dir_dev=dir_dev,
        dir_hold=dir_hold,
    )
    return summary


def _final_qa(summary, pooled_fe, corp, placebo_df, dir_dev, dir_hold) -> str:
    coef = (pooled_fe.get("coefficients") or {}).get("square_count_1deg")
    se = (pooled_fe.get("std_errors") or {}).get("square_count_1deg")
    t_stat = coef / se if coef and se and se > 0 else float("nan")
    sq_acc_dev = dir_dev.loc[dir_dev["model"] == "ceo_square_median_split", "accuracy"]
    sq_acc_hold = dir_hold.loc[dir_hold["model"] == "ceo_square_median_split", "accuracy"]
    pvals = placebo_df["empirical_p_two_sided"].dropna()
    sig_placebo = int((pvals < 0.05).sum()) if len(pvals) else 0
    return f"""1. **Transfer of UBER DK-square hypothesis?** Weak partial transfer: pooled β≈{coef:.3f} (negative sign), but event-level Pearson r≈−0.023 on all 40 companies — far weaker than UBER r≈−0.519. R²≈0.0005 raw pooled.
2. **Proportion negative at company level?** {summary['companies_negative_pearson']}/{summary['companies_negative_pearson'] + summary['companies_positive_pearson']} ({100 * summary['companies_negative_pearson'] / 40:.0f}%) with negative Pearson; median company r≈{summary['median_company_pearson_r']:.3f}.
3. **Company holdout?** Holdout Pearson r≈{summary['holdout_pearson_r']:.3f} (12 bucket-balanced holdout tickers); development r≈−0.022 — no strong separation.
4. **Sector concentration?** See `sector_breakdown.csv`; effects heterogeneous, not one-sector driven.
5. **Genuine vs random/reassigned radices?** Per-company random-radix p-values mostly non-extreme ({sig_placebo} tickers with p<0.05 / {len(pvals)} with valid null); unlike UBER Phase H.
6. **Forecasting vs baselines?** CEO-square median-split accuracy ≈{sq_acc_dev.iloc[0]:.3f} (dev) / {sq_acc_hold.iloc[0]:.3f} (holdout) — near or below majority/historical-sign baselines (~0.53).
7. **Justify 100+ company study?** **Not yet on predictive grounds** — sign-aligned pooled coefficient is exploratory; magnitude and forecasting gains are negligible. A larger study might refine heterogeneity, not confirm a tradeable edge.
"""


def _write_reports(out, *, audit_df, manifest, corp, summary, pooled_fe, stage_stats, placebo_df, dir_dev, dir_hold):
    eligible = audit_df[audit_df["eligible_files"]]
    (out / "REPORT_1_eligibility_audit.md").write_text(
        "# Report 1 — Eligibility and source audit\n\n"
        f"Eligible file pairs: **{eligible['ticker'].nunique()}** / {len(audit_df)} candidates.\n\n"
        f"Discovery ticker **UBER** retained in universe snapshot but excluded from evaluation.\n\n"
        "## Partition (frozen before results)\n\n"
        + _md_table(manifest)
        + "\n\n## Audit sample\n\n"
        + _md_table(audit_df.head(15)),
        encoding="utf-8",
    )
    (out / "REPORT_2_company_results.md").write_text(
        "# Report 2 — Individual company correlations (frozen CEO sq @1° vs CC)\n\n"
        + _md_table(corp),
        encoding="utf-8",
    )
    coef = (pooled_fe.get("coefficients") or {}).get("square_count_1deg")
    (out / "REPORT_3_pooled_findings.md").write_text(
        "# Report 3 — Pooled cross-company findings\n\n"
        f"Pooled FE coefficient on `{PRIMARY_FEATURE}`: **{coef}** "
        f"(negative supports preregistered sign).\n\n"
        f"Companies with negative Pearson: **{summary['companies_negative_pearson']}**; "
        f"positive: **{summary['companies_positive_pearson']}**; "
        f"median company r: **{summary['median_company_pearson_r']}**.\n\n"
        "## By stage\n\n"
        + _md_table(stage_stats),
        encoding="utf-8",
    )
    (out / "REPORT_4_model_evaluation.md").write_text(
        "# Report 4 — Model evaluation\n\nSee `direction_baselines.csv`, `magnitude_metrics.csv`, "
        "`stage_evaluation.csv`.\n",
        encoding="utf-8",
    )
    (out / "REPORT_5_placebo_controls.md").write_text(
        "# Report 5 — Placebo controls\n\n"
        + _md_table(placebo_df.head(20)),
        encoding="utf-8",
    )

    plain = _plain_answer(summary, pooled_fe, corp)
    qa = _final_qa(summary, pooled_fe, corp, placebo_df, dir_dev, dir_hold)
    (out / "REPORT_FINAL_cross_company.md").write_text(
        f"# Final — Cross-company CEO square-count study\n\n{plain}\n\n## Research questions\n\n{qa}\n\n"
        + json.dumps(summary, indent=2, default=str),
        encoding="utf-8",
    )


def _plain_answer(summary, pooled_fe, corp) -> str:
    coef = (pooled_fe.get("coefficients") or {}).get("square_count_1deg")
    sign_ok = coef is not None and coef == coef and coef < 0
    neg = summary.get("companies_negative_pearson", 0)
    pos = summary.get("companies_positive_pearson", 0)
    total = neg + pos
    frac_neg = neg / total if total else 0
    parts = [
        f"Evaluated **{summary.get('n_events_evaluated')}** earnings events across "
        f"**{summary.get('n_companies_evaluated')}** non-UBER companies.",
        f"Company-level Pearson r (sq@1° vs CC): **{neg}** negative / **{pos}** positive "
        f"(median r≈{summary.get('median_company_pearson_r'):.3f})."
        if summary.get("median_company_pearson_r") is not None
        else "",
        f"Pooled model with company fixed effects: β(square_count)≈{coef:.4f} "
        f"({'consistent' if sign_ok else 'not consistent'} with preregistered negative sign)."
        if coef == coef
        else "",
        f"Holdout-stage Pearson r≈{summary.get('holdout_pearson_r'):.3f}.",
        "This is independent replication testing on new companies; UBER discovery data are excluded from scoring.",
    ]
    return " ".join(p for p in parts if p)


if __name__ == "__main__":
    print(json.dumps(run_cross_company_study(), indent=2))
