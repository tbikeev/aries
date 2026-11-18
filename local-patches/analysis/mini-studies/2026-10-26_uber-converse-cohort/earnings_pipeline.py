#!/usr/bin/env python3
"""UBER earnings-reaction converse cohort pipeline."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from configuration_miner import compare_extreme_groups, mine_configurations
from earnings_converse import extract_converse_features, registry_snapshot
from earnings_loader import load_earnings_csv
from earnings_models import (
    feasibility_report,
    walk_forward_direction,
    walk_forward_feature_model,
    walk_forward_large_move_direction,
    walk_forward_volatility_baseline,
)
from fixed_features import MODEL_A_FEATURES, MODEL_B_FEATURES, build_model_feature_frames
from robustness_checks import (
    leave_one_out_correlations,
    leave_one_out_summary,
    merge_features_outcomes,
    orb_sensitivity,
    permutation_correlation_test,
    subset_correlations,
)
from temporal_persistence import flagged_outer_planet_signatures, persistence_summary
from earnings_paths import EARNINGS_OUTPUT, resolve_earnings_csv, resolve_ohlc_csv
from extreme_events import top_extremes
from feature_reduction import build_event_feature_matrix, rank_feature_groups
from market_reactions import build_reactions, load_ohlc_csv, reactions_to_dataframe
from radix import RADIX_COHORT

COHORTS = ("FT", "INC", "DK")


def run_earnings_study(
    *,
    earnings_csv: Path | None = None,
    ohlc_csv: Path | None = None,
    output_dir: Path | None = None,
    top_positive: int = 10,
    top_negative: int = 10,
) -> dict:
    out = output_dir or EARNINGS_OUTPUT
    out.mkdir(parents=True, exist_ok=True)

    epath = resolve_earnings_csv(earnings_csv)
    opath = resolve_ohlc_csv(ohlc_csv)
    settings = {
        "earnings_csv": str(epath),
        "ohlc_csv": str(opath),
        "price_basis": "adjusted_close",
        "reaction_event_time": "09:30 America/New_York",
        "cohorts": list(COHORTS),
        "radix": {
            k: {
                "key": v.key,
                "label": v.label,
                "utc": f"{v.year}-{v.month:02d}-{v.day:02d} {v.hour:02d}:{v.minute:02d} UTC",
                "birth_time_uncertain": v.birth_time_uncertain,
            }
            for k, v in RADIX_COHORT.items()
        },
        "run_utc": datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + "Z",
    }
    (out / "run_settings.json").write_text(json.dumps(settings, indent=2, default=str), encoding="utf-8")

    earnings = load_earnings_csv(epath)
    ohlc = load_ohlc_csv(opath)
    settings["ohlc_close_adj_max_diff"] = ohlc.attrs.get("close_adj_max_diff")
    reactions = build_reactions(earnings, ohlc)
    react_df = reactions_to_dataframe(reactions)
    react_df.to_csv(out / "earnings_reactions_all.csv", index=False)

    neg, pos, chron = top_extremes(reactions, top_negative=top_negative, top_positive=top_positive)
    neg3, pos3, _ = top_extremes(reactions, top_negative=3, top_positive=3)
    neg.to_csv(out / "leaderboard_top_negative.csv", index=False)
    pos.to_csv(out / "leaderboard_top_positive.csv", index=False)
    neg3.to_csv(out / "leaderboard_top3_negative.csv", index=False)
    pos3.to_csv(out / "leaderboard_top3_positive.csv", index=False)
    chron.to_csv(out / "earnings_chronological.csv", index=False)

    aspect_parts: list[pd.DataFrame] = []
    decl_parts: list[pd.DataFrame] = []
    for r in reactions:
        if r.excluded or r.event_datetime_utc is None:
            continue
        from earnings_converse import event_jd_from_datetime

        ejd = event_jd_from_datetime(r.event_datetime_utc)
        rd = str(r.report_date)
        rs = str(r.reaction_session)
        for cohort in COHORTS:
            block = extract_converse_features(
                cohort,
                ejd,
                report_date=rd,
                reaction_session=rs,
            )
            aspect_parts.append(pd.DataFrame(block["aspect_rows"]))
            decl_parts.append(pd.DataFrame(block["decl_rows"]))

    aspects_df = pd.concat(aspect_parts, ignore_index=True) if aspect_parts else pd.DataFrame()
    decl_df = pd.concat(decl_parts, ignore_index=True) if decl_parts else pd.DataFrame()
    aspects_df.to_csv(out / "converse_radix_aspects_all_events.csv", index=False)
    decl_df.to_csv(out / "converse_radix_declination_all_events.csv", index=False)
    pd.DataFrame(registry_snapshot()).to_csv(out / "cohort_registry_snapshot.csv", index=False)

    extreme_dates = set(neg["report_date"].astype(str)) | set(pos["report_date"].astype(str))
    neg_dates = set(neg["report_date"].astype(str))
    pos_dates = set(pos["report_date"].astype(str))

    mined = mine_configurations(aspects_df, extreme_dates)
    mined.to_csv(out / "configuration_mine_extremes.csv", index=False)
    cmp_df = compare_extreme_groups(aspects_df, neg_dates, pos_dates)
    cmp_df.to_csv(out / "configuration_pos_vs_neg.csv", index=False)

    feat_df = build_event_feature_matrix(aspects_df)
    feat_df.to_csv(out / "event_astrology_feature_matrix.csv", index=False)
    rank_df = rank_feature_groups(feat_df, react_df[~react_df["excluded"]])
    rank_df.to_csv(out / "feature_reduction_ranking.csv", index=False)

    valid_react = react_df[~react_df["excluded"]]
    wf = walk_forward_direction(feat_df, valid_react, feature_cols=[])
    (out / "walk_forward_baseline.json").write_text(
        json.dumps({"folds": wf.folds, "summary": wf.summary}, indent=2),
        encoding="utf-8",
    )
    feas = feasibility_report(react_df)

    core_features = [
        "DK_sq_count",
        "tight_aspect_count",
        "FT_sq_count",
        "INC_sq_count",
    ]
    merged_core = merge_features_outcomes(feat_df, valid_react)
    loo_detail = leave_one_out_correlations(merged_core, core_features)
    loo_detail.to_csv(out / "robustness_leave_one_out.csv", index=False)
    loo_sum = leave_one_out_summary(loo_detail)
    loo_sum.to_csv(out / "robustness_leave_one_out_summary.csv", index=False)
    orb_sens = orb_sensitivity(aspects_df, valid_react, core_features)
    orb_sens.to_csv(out / "robustness_orb_sensitivity.csv", index=False)
    subset = subset_correlations(
        aspects_df, valid_react, exclude_report_dates=extreme_dates, features=core_features
    )
    subset.to_csv(out / "robustness_exclude_top10x2.csv", index=False)
    perm_rows = []
    for feat in ("DK_sq_count", "tight_aspect_count"):
        for target in ("r_cc_pct", "abs_r_cc_pct"):
            perm_rows.append(
                permutation_correlation_test(merged_core, feat, target=target, n_perm=4999)
            )
    pd.DataFrame(perm_rows).to_csv(out / "robustness_permutation_tests.csv", index=False)

    run_df, persist_sum = persistence_summary(aspects_df, orb_max=1.0)
    run_df.to_csv(out / "aspect_persistence_runs.csv", index=False)
    persist_sum.to_csv(out / "aspect_persistence_summary.csv", index=False)
    flagged = flagged_outer_planet_signatures(persist_sum)
    flagged.to_csv(out / "aspect_persistence_slow_body_flags.csv", index=False)

    model_frames = build_model_feature_frames(aspects_df)
    wf_models = {}
    for name, cols, frame in (
        ("model_a_sq_counts", list(MODEL_A_FEATURES), model_frames["full"]),
        ("model_b_density_dk_sq", list(MODEL_B_FEATURES), model_frames["full"]),
        (
            "model_c_preselected_sigs",
            ["preselected_sig_count", "preselected_sig_orb_sum"],
            model_frames["full"],
        ),
    ):
        res = walk_forward_feature_model(
            frame, valid_react, feature_cols=cols, model_name=name
        )
        wf_models[name] = res.summary
        (out / f"walk_forward_{name}.json").write_text(
            json.dumps({"folds": res.folds, "summary": res.summary}, indent=2),
            encoding="utf-8",
        )
    wf_vol = walk_forward_volatility_baseline(valid_react)
    (out / "walk_forward_baseline_volatility.json").write_text(
        json.dumps({"folds": wf_vol.folds, "summary": wf_vol.summary}, indent=2),
        encoding="utf-8",
    )
    wf_large = walk_forward_large_move_direction(
        model_frames["full"],
        valid_react,
        feature_cols=list(MODEL_B_FEATURES),
        model_name="model_b_large_moves_only",
    )
    (out / "walk_forward_model_b_large_moves.json").write_text(
        json.dumps({"folds": wf_large.folds, "summary": wf_large.summary}, indent=2),
        encoding="utf-8",
    )

    _write_report_a(out, neg, pos, neg3, pos3, len(valid_react))
    _write_report_b(out, neg, pos, aspects_df, decl_df)
    _write_report_c(out, cmp_df)
    _write_report_d(out, rank_df, mined)
    _write_report_e(out, feas, wf.summary, wf_models, wf_vol.summary)
    _write_report_f(
        out,
        loo_sum=loo_sum,
        orb_sens=orb_sens,
        subset=subset,
        perm_rows=perm_rows,
        flagged=flagged,
        persist_sum=persist_sum,
        run_df=run_df,
    )

    summary = {
        "output_dir": str(out),
        "valid_reactions": int((~react_df["excluded"]).sum()),
        "excluded": int(react_df["excluded"].sum()),
        "extreme_neg": len(neg),
        "extreme_pos": len(pos),
        "aspect_rows": len(aspects_df),
        "feasibility": feas,
        "robustness": {
            "loo": loo_sum.to_dict(orient="records"),
            "permutation": perm_rows,
        },
        "walk_forward_models": wf_models,
    }
    (out / "pipeline_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def _write_report_a(
    out: Path,
    neg: pd.DataFrame,
    pos: pd.DataFrame,
    neg3: pd.DataFrame,
    pos3: pd.DataFrame,
    n_valid: int,
) -> None:
    overlap = len(set(neg["report_date"].astype(str)) | set(pos["report_date"].astype(str)))
    lines = [
        "# Report A — Earnings reaction leaderboard",
        "",
        f"Valid reactions: **{n_valid}**. Top-10 + top-10 extremes overlap **{overlap}** events "
        f"({100 * overlap / n_valid:.1f}% of sample) — use top-3 tables below for sharper descriptives.",
        "",
    ]
    lines.append("## Top 3 negative (declared selective threshold)")
    lines.append(_df_md(neg3[["rank", "report_date", "reaction_session", "r_cc_pct"]]))
    lines.append("## Top 3 positive")
    lines.append(_df_md(pos3[["rank", "report_date", "reaction_session", "r_cc_pct"]]))
    lines.append("## Top 10 negative (close-to-close %)")
    lines.append(_df_md(neg[["rank", "report_date", "reaction_session", "r_cc_pct", "r_gap_pct", "r_2d_pct", "r_5d_pct", "eps_surprise_pct"]]))
    lines.append("## Top positive")
    lines.append(_df_md(pos[["rank", "report_date", "reaction_session", "r_cc_pct", "r_gap_pct", "r_2d_pct", "r_5d_pct", "eps_surprise_pct"]]))
    (out / "REPORT_A_leaderboard.md").write_text("\n".join(lines), encoding="utf-8")


def _write_report_b(out: Path, neg, pos, aspects_df, decl_df) -> None:
    lines = ["# Report B — Per extreme event configurations", ""]
    for label, frame in (("Negative", neg), ("Positive", pos)):
        lines.append(f"## {label} extremes")
        for _, row in frame.iterrows():
            rd = str(row["report_date"])
            lines.append(f"### {rd} reaction {row['reaction_session']} CC={row['r_cc_pct']:.2f}%")
            sub = aspects_df[
                (aspects_df["report_date"].astype(str) == rd) & (aspects_df["best_orb"] <= 1.0)
            ].sort_values("best_orb")
            lines.append("Top longitude (≤1°):")
            for _, a in sub.head(12).iterrows():
                lines.append(
                    f"- {a['radix_key']} {a['from_body']} {a['best_aspect']} {a['to_body']} orb {a['best_orb']:.3f}°"
                )
            dsub = decl_df[
                (decl_df["report_date"].astype(str) == rd)
                & ((decl_df["par_delta_deg"] <= 1.0) | (decl_df["cpar_delta_deg"] <= 1.0))
            ].sort_values("par_delta_deg")
            lines.append("Tight declination:")
            for _, d in dsub.head(6).iterrows():
                lines.append(
                    f"- {d['radix_key']} {d['conv_body']} par {d['par_delta_deg']:.2f}° / cpar {d['cpar_delta_deg']:.2f}° → {d['radix_body']}"
                )
            lines.append("")
    (out / "REPORT_B_per_event.md").write_text("\n".join(lines), encoding="utf-8")


def _write_report_c(out: Path, cmp_df: pd.DataFrame) -> None:
    top = cmp_df.head(30)
    (out / "REPORT_C_pos_vs_neg.md").write_text(
        "# Report C — Positive vs negative configuration comparison\n\n" + _df_md(top),
        encoding="utf-8",
    )


def _write_report_d(out: Path, rank_df, mined) -> None:
    (out / "REPORT_D_feature_reduction.md").write_text(
        "# Report D — Feature reduction (exploratory)\n\n## Correlation with CC return\n"
        + _df_md(rank_df.head(20))
        + "\n\n## Frequent in extremes\n"
        + _df_md(mined.head(20)),
        encoding="utf-8",
    )


def _write_report_e(out: Path, feas, wf_summary, wf_models, vol_summary) -> None:
    (out / "REPORT_E_predictive_feasibility.md").write_text(
        "# Report E — Predictive feasibility\n\n"
        + json.dumps(
            {
                "feasibility": feas,
                "walk_forward_majority_sign_baseline": wf_summary,
                "walk_forward_fixed_feature_models_exploratory": wf_models,
                "walk_forward_volatility_baseline": vol_summary,
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def _write_report_f(
    out: Path,
    *,
    loo_sum,
    orb_sens,
    subset,
    perm_rows,
    flagged,
    persist_sum,
    run_df,
) -> None:
    lines = [
        "# Report F — Robustness and temporal persistence",
        "",
        "Exploratory statistics on N≈26; permutation p-values are approximate.",
        "",
        "## Leave-one-out (correlation with CC return)",
        _df_md(loo_sum),
        "",
        "## Orb threshold sensitivity",
        _df_md(orb_sens),
        "",
        "## Correlations excluding top-10 positive + top-10 negative",
        _df_md(subset),
        "",
        "## Permutation tests (4999 shuffles, seed=42)",
        _df_md(pd.DataFrame(perm_rows)),
        "",
        "## Slow-body signatures: event hits vs independent earnings-quarter runs",
        _df_md(flagged.head(25) if not flagged.empty else persist_sum.head(15)),
        "",
        "## Longest consecutive earnings-quarter activation runs (≤1°)",
        _df_md(run_df.head(20)),
    ]
    (out / "REPORT_F_robustness_persistence.md").write_text("\n".join(lines), encoding="utf-8")


def _df_md(df: pd.DataFrame) -> str:
    if df.empty:
        return "(empty)"
    try:
        return df.to_markdown(index=False)
    except Exception:
        return df.to_csv(index=False)


if __name__ == "__main__":
    run_earnings_study()
