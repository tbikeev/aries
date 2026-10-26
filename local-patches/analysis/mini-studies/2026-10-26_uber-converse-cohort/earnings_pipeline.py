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
from earnings_models import feasibility_report, walk_forward_direction
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
        "run_utc": datetime.utcnow().isoformat() + "Z",
    }
    (out / "run_settings.json").write_text(json.dumps(settings, indent=2, default=str), encoding="utf-8")

    earnings = load_earnings_csv(epath)
    ohlc = load_ohlc_csv(opath)
    settings["ohlc_close_adj_max_diff"] = ohlc.attrs.get("close_adj_max_diff")
    reactions = build_reactions(earnings, ohlc)
    react_df = reactions_to_dataframe(reactions)
    react_df.to_csv(out / "earnings_reactions_all.csv", index=False)

    neg, pos, chron = top_extremes(reactions, top_negative=top_negative, top_positive=top_positive)
    neg.to_csv(out / "leaderboard_top_negative.csv", index=False)
    pos.to_csv(out / "leaderboard_top_positive.csv", index=False)
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

    wf = walk_forward_direction(feat_df, react_df[~react_df["excluded"]], feature_cols=[])
    (out / "walk_forward_baseline.json").write_text(
        json.dumps({"folds": wf.folds, "summary": wf.summary}, indent=2),
        encoding="utf-8",
    )
    feas = feasibility_report(react_df)

    _write_report_a(out, neg, pos)
    _write_report_b(out, neg, pos, aspects_df, decl_df)
    _write_report_c(out, cmp_df)
    _write_report_d(out, rank_df, mined)
    _write_report_e(out, feas, wf.summary)

    summary = {
        "output_dir": str(out),
        "valid_reactions": int((~react_df["excluded"]).sum()),
        "excluded": int(react_df["excluded"].sum()),
        "extreme_neg": len(neg),
        "extreme_pos": len(pos),
        "aspect_rows": len(aspects_df),
        "feasibility": feas,
    }
    (out / "pipeline_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def _write_report_a(out: Path, neg: pd.DataFrame, pos: pd.DataFrame) -> None:
    lines = ["# Report A — Earnings reaction leaderboard", ""]
    lines.append("## Top negative (close-to-close %)")
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


def _write_report_e(out: Path, feas, wf_summary) -> None:
    (out / "REPORT_E_predictive_feasibility.md").write_text(
        "# Report E — Predictive feasibility\n\n"
        + json.dumps({"feasibility": feas, "walk_forward_baseline": wf_summary}, indent=2),
        encoding="utf-8",
    )


def _df_md(df: pd.DataFrame) -> str:
    if df.empty:
        return "(empty)"
    try:
        return df.to_markdown(index=False)
    except Exception:
        return df.to_csv(index=False)


if __name__ == "__main__":
    run_earnings_study()
