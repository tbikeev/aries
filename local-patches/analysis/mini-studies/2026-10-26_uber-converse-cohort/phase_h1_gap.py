"""H1: gap vs intraday decomposition (exploratory)."""

from __future__ import annotations

import pandas as pd

from phase_h_stats import correlation_report

FROZEN_FEATURES = (
    "DK_sq_count_orb05",
    "DK_sq_count_orb10",
    "tight_aspect_count_orb05",
    "tight_aspect_count_orb10",
    "FT_sq_count_orb10",
    "INC_sq_count_orb10",
)

TARGETS = (
    "r_cc_pct",
    "r_gap_pct",
    "r_intra_pct",
    "abs_r_gap_pct",
    "abs_r_intra_pct",
)


def run_h1(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    rows = []
    for feat in FROZEN_FEATURES:
        if feat not in df.columns:
            continue
        for target in TARGETS:
            rows.append(correlation_report(df, feat, target))
    corr_df = pd.DataFrame(rows)

    event_rows = df[
        [
            "report_date",
            "timing",
            "reaction_session",
            "r_cc_pct",
            "r_gap_pct",
            "r_intra_pct",
            "DK_sq_count_orb10",
            "tight_aspect_count_orb10",
            "cc_identity_err_bps",
        ]
    ].copy()

    timing_rows = []
    for timing, grp in df.groupby("timing"):
        if len(grp) < 4:
            timing_rows.append(
                {
                    "timing": timing,
                    "n": len(grp),
                    "note": "too_small_for_stable_inference",
                    "DK_sq_orb10_vs_cc": None,
                }
            )
            continue
        timing_rows.append(
            {
                "timing": timing,
                "n": len(grp),
                "note": "",
                "DK_sq_orb10_vs_cc": float(grp["DK_sq_count_orb10"].corr(grp["r_cc_pct"])),
                "DK_sq_orb10_vs_gap": float(grp["DK_sq_count_orb10"].corr(grp["r_gap_pct"])),
                "DK_sq_orb10_vs_intra": float(grp["DK_sq_count_orb10"].corr(grp["r_intra_pct"])),
            }
        )
    timing_df = pd.DataFrame(timing_rows)

    dk_gap = corr_df[
        (corr_df["feature"] == "DK_sq_count_orb10") & (corr_df["target"] == "r_gap_pct")
    ]
    dk_intra = corr_df[
        (corr_df["feature"] == "DK_sq_count_orb10") & (corr_df["target"] == "r_intra_pct")
    ]
    dk_cc = corr_df[
        (corr_df["feature"] == "DK_sq_count_orb10") & (corr_df["target"] == "r_cc_pct")
    ]
    conclusion = {
        "exploratory": True,
        "dk_sq_orb10_pearson_gap": float(dk_gap["pearson_r"].iloc[0]) if len(dk_gap) else None,
        "dk_sq_orb10_pearson_intra": float(dk_intra["pearson_r"].iloc[0]) if len(dk_intra) else None,
        "dk_sq_orb10_pearson_cc": float(dk_cc["pearson_r"].iloc[0]) if len(dk_cc) else None,
        "interpretation_hint": (
            "Compare |r| on gap vs intra; stronger gap suggests overnight repricing channel."
        ),
    }
    return corr_df, event_rows, timing_df, conclusion
