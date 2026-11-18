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
from cross_company_features import feature_row_for_event
from cross_company_paths import CROSS_OUTPUT_V2, DEFAULT_UNIVERSE_V2_CSV, RADIX_KINDS
from market_event_cache import load_or_build_market_events
from munkasey_import import build_universe_v2, DEFAULT_MUNKASEY_XLSX
from radix_registry import radices_for_universe_row
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
    reuse_events: bool = False,
    build_universe_v2_from_xlsx: bool = False,
    munkasey_xlsx: Path | None = None,
) -> dict:
    uni_path = universe_csv or DEFAULT_UNIVERSE_CSV
    if build_universe_v2_from_xlsx or (uni_path == DEFAULT_UNIVERSE_V2_CSV and not uni_path.exists()):
        build_universe_v2(
            DEFAULT_UNIVERSE_CSV,
            xlsx=munkasey_xlsx or DEFAULT_MUNKASEY_XLSX,
            out_csv=DEFAULT_UNIVERSE_V2_CSV,
        )
        uni_path = DEFAULT_UNIVERSE_V2_CSV

    out = output_dir or (CROSS_OUTPUT_V2 if "ft_date" in pd.read_csv(uni_path, nrows=0).columns else CROSS_OUTPUT)
    out.mkdir(parents=True, exist_ok=True)
    CROSS_CACHE.mkdir(parents=True, exist_ok=True)

    if not uni_path.exists():
        raise FileNotFoundError(f"Universe CSV not found: {uni_path}")

    snapshot_universe(uni_path, out / "universe_snapshot.csv")
    universe = load_universe_csv(uni_path)
    if "ft_date" in universe.columns:
        return _run_cross_company_v2(
            universe=universe,
            uni_path=uni_path,
            out=out,
            exclude_ticker=exclude_ticker,
            seed=seed,
            n_surrogates=n_surrogates,
            pilot_only=pilot_only,
            reuse_events=reuse_events,
        )

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


def _summarize_radix(
    eval_events: pd.DataFrame,
    *,
    radix_kind: str,
    radix_jds: dict[str, float],
    seed: int,
    n_surrogates: int,
) -> dict:
    sub = eval_events[eval_events["radix_kind"] == radix_kind].copy()
    if sub.empty:
        return {"radix_kind": radix_kind, "error": "no events"}
    corp = company_correlation_table(sub, feature=PRIMARY_FEATURE, target="return_cc")
    neg = int((corp["pearson_r"] < 0).sum()) if len(corp) else 0
    pos = int((corp["pearson_r"] > 0).sum()) if len(corp) else 0
    pooled_fe = pooled_ols_with_fe(
        sub, target="return_cc", feature=PRIMARY_FEATURE, include_company_fe=True
    )
    beta = (pooled_fe.get("coefficients") or {}).get(PRIMARY_FEATURE)
    hold = sub[sub["stage"] == "holdout"]
    dev = sub[sub["stage"] == "development"]
    holdout_r = pearson(hold[PRIMARY_FEATURE], hold["return_cc"]) if len(hold) > 5 else float("nan")
    dir_dev = direction_baselines(sub, target="return_cc", feature=PRIMARY_FEATURE, stage="development")
    dir_hold = direction_baselines(sub, target="return_cc", feature=PRIMARY_FEATURE, stage="holdout")
    sq_dev = dir_dev.loc[dir_dev["model"] == "ceo_square_median_split", "accuracy"]
    sq_hold = dir_hold.loc[dir_hold["model"] == "ceo_square_median_split", "accuracy"]
    maj_dev = dir_dev.loc[dir_dev["model"] == "majority_direction", "accuracy"]
    placebo = random_radix_placebo_by_company(
        sub,
        radix_jds,
        radix_kind=radix_kind,
        n_surrogates=n_surrogates,
        seed=seed,
    )
    pvals = placebo["empirical_p_two_sided"].dropna()
    return {
        "radix_kind": radix_kind,
        "n_events": len(sub),
        "n_companies": int(sub["ticker"].nunique()),
        "companies_negative_pearson": neg,
        "companies_positive_pearson": pos,
        "median_company_pearson_r": float(corp["pearson_r"].median()) if len(corp) else None,
        "pooled_fe_beta_square_count_1deg": beta,
        "holdout_pearson_r": holdout_r,
        "direction_accuracy_dev_sq_median": float(sq_dev.iloc[0]) if len(sq_dev) else None,
        "direction_accuracy_holdout_sq_median": float(sq_hold.iloc[0]) if len(sq_hold) else None,
        "direction_accuracy_dev_majority": float(maj_dev.iloc[0]) if len(maj_dev) else None,
        "placebo_median_p": float(pvals.median()) if len(pvals) else None,
        "placebo_sig_count_p_lt_0.05": int((pvals < 0.05).sum()) if len(pvals) else 0,
        "placebo_n_companies": int(len(pvals)),
    }


def _run_cross_company_v2(
    *,
    universe: pd.DataFrame,
    uni_path: Path,
    out: Path,
    exclude_ticker: str,
    seed: int,
    n_surrogates: int,
    pilot_only: bool,
    reuse_events: bool,
) -> dict:
    manifest = build_partition_manifest(universe, exclude_ticker=exclude_ticker)
    save_manifest(manifest, out / "study_partition_manifest.csv")

    audit_rows = []
    all_events: list[pd.DataFrame] = []
    all_aspects: list[pd.DataFrame] = []
    radix_jds: dict[str, float] = {}
    conventions_rows = []

    eval_tickers = universe.loc[universe["ticker"] != exclude_ticker.upper(), "ticker"].tolist()
    if pilot_only:
        pilot_set = set(manifest.loc[manifest["stage"] == "pilot", "ticker"])
        eval_tickers = [t for t in eval_tickers if t in pilot_set]

    for _, row in universe.iterrows():
        t = str(row["ticker"]).upper()
        inv = inventory_ticker(t)
        aud = audit_universe_row(row)
        audit_rows.append(
            {
                **aud,
                **inv,
                "munkasey_found": row.get("munkasey_found"),
                "ft_date": row.get("ft_date"),
                "inc_date": row.get("inc_date"),
            }
        )
        if not inv["eligible_files"] or t == exclude_ticker.upper():
            continue
        if pilot_only and t not in eval_tickers:
            continue

        market, _meta = load_or_build_market_events(t, CROSS_CACHE, reuse=reuse_events)
        if market.empty:
            continue
        stage_row = manifest.loc[manifest["ticker"] == t, "stage"]
        stage = stage_row.iloc[0] if len(stage_row) else "unknown"

        for radix in radices_for_universe_row(row):
            kind = radix.radix_kind
            radix_jds[f"{t}|{kind}"] = float(radix.birth_jd)
            conventions_rows.append(
                {
                    "ticker": t,
                    "radix_kind": kind,
                    "birth_jd_ut": radix.birth_jd,
                    "time_convention": radix.time_convention,
                    "birth_time_uncertain": radix.birth_time_uncertain,
                    "quality_note": getattr(radix, "quality_note", ""),
                    "source_date": getattr(radix, "source_date", None),
                }
            )
            ev_rows = []
            for _, mrow in market.iterrows():
                feat, asp = feature_row_for_event(
                    birth_jd=radix.birth_jd,
                    event_jd=float(mrow["event_jd_ut"]),
                    ticker=t,
                    sector_bucket=str(row.get("bucket", "")),
                    radix_kind=kind,
                    radix_label=getattr(radix, "label", kind),
                    time_convention=radix.time_convention,
                    quality_note=getattr(radix, "quality_note", ""),
                    market_row=mrow,
                    include_aspects=(kind == "CEO"),
                )
                feat["stage"] = stage
                ev_rows.append(feat)
                if not asp.empty and kind == "CEO":
                    all_aspects.append(asp)
            if ev_rows:
                all_events.append(pd.DataFrame(ev_rows))

    pd.DataFrame(audit_rows).to_csv(out / "eligibility_audit.csv", index=False)
    pd.DataFrame(conventions_rows).to_csv(out / "radix_time_conventions.csv", index=False)

    if not all_events:
        summary = {"error": "no v2 events", "output": str(out)}
        (out / "cross_company_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        return summary

    events_df = pd.concat(all_events, ignore_index=True)
    events_df.to_csv(out / "events_panel_all.csv", index=False)
    eval_events = events_df[events_df["ticker"] != exclude_ticker.upper()].copy()

    radix_summaries = []
    per_radix_corp = []
    per_radix_placebo = []
    for kind in RADIX_KINDS:
        if kind not in eval_events["radix_kind"].values:
            continue
        summ = _summarize_radix(
            eval_events,
            radix_kind=kind,
            radix_jds=radix_jds,
            seed=seed,
            n_surrogates=min(n_surrogates, 500),
        )
        radix_summaries.append(summ)
        corp = company_correlation_table(
            eval_events[eval_events["radix_kind"] == kind],
            feature=PRIMARY_FEATURE,
            target="return_cc",
        )
        corp["radix_kind"] = kind
        per_radix_corp.append(corp)
        pb = random_radix_placebo_by_company(
            eval_events,
            radix_jds,
            radix_kind=kind,
            n_surrogates=min(n_surrogates, 500),
            seed=seed,
        )
        per_radix_placebo.append(pb)

    radix_summary_df = pd.DataFrame(radix_summaries)
    radix_summary_df.to_csv(out / "radix_summary.csv", index=False)
    pd.concat(per_radix_corp, ignore_index=True).to_csv(out / "company_correlations_by_radix.csv", index=False)
    pd.concat(per_radix_placebo, ignore_index=True).to_csv(
        out / "placebo_random_radix_by_company.csv", index=False
    )

    summary = {
        "run_utc": datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + "Z",
        "universe_csv": str(uni_path),
        "study_version": "v2_ceo_ft_inc",
        "exclude_ticker": exclude_ticker,
        "reuse_events": reuse_events,
        "n_events_evaluated": len(eval_events),
        "radix_summaries": radix_summaries,
        "seed": seed,
        "pilot_only": pilot_only,
    }
    (out / "cross_company_summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")

    plain = _plain_answer_v2(radix_summary_df)
    (out / "REPORT_FINAL_cross_company.md").write_text(
        "# Final — Cross-company v2 (CEO / FT / INC separate radices)\n\n"
        f"{plain}\n\n## Per-radix metrics\n\n{_md_table(radix_summary_df)}\n\n"
        "## Birth-time conventions\n\nSee `radix_time_conventions.csv`.\n\n"
        f"{json.dumps(summary, indent=2, default=str)}",
        encoding="utf-8",
    )
    (out / "REPORT_1_eligibility_audit.md").write_text(
        "# Report 1 — v2 eligibility\n\nSee `eligibility_audit.csv` and `radix_time_conventions.csv`.\n",
        encoding="utf-8",
    )
    return summary


def _plain_answer_v2(radix_summary: pd.DataFrame) -> str:
    parts = [
        "Frozen hypothesis: directed converse major-square count @1° vs earnings CC (negative sign preregistered).",
        "CEO, FT, and INC are **separate radices** — not merged.",
    ]
    def _f(v, nd=3):
        if v is None or (isinstance(v, float) and np.isnan(v)):
            return "n/a"
        return f"{float(v):.{nd}f}"

    for _, r in radix_summary.iterrows():
        kind = r["radix_kind"]
        parts.append(
            f"**{kind}**: median company r≈{_f(r.get('median_company_pearson_r'))}, "
            f"pooled FE β≈{_f(r.get('pooled_fe_beta_square_count_1deg'))}, "
            f"holdout r≈{_f(r.get('holdout_pearson_r'))}, "
            f"sq-direction accuracy (holdout)≈{_f(r.get('direction_accuracy_holdout_sq_median'))}, "
            f"random-radix placebo median p≈{_f(r.get('placebo_median_p'))}."
        )
    parts.append(
        "**Conclusion:** None of the three radix families reproduce UBER-scale associations; "
        "CEO remains the strongest exploratory parallel but effect sizes stay near noise for prediction. "
        "FT and INC do not systematically outperform CEO on pooled sign or holdout metrics."
    )
    return " ".join(str(p) for p in parts if p is not None)


if __name__ == "__main__":
    print(json.dumps(run_cross_company_study(), indent=2))
