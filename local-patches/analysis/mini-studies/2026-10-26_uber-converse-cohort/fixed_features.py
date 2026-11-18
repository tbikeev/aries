"""Pre-declared feature sets for fixed walk-forward experiments (exploratory on same N)."""

from __future__ import annotations

import pandas as pd

from aspect_signatures import add_signature_column
from feature_reduction import build_event_feature_matrix
from market_reactions import report_date_key

# Declared before interpreting walk-forward on the same 26 events (hypothesis labels only).
PRESELECTED_SIGNATURES: tuple[str, ...] = (
    "DK|conv:Pluto|radix:Saturn|sext",
    "INC|conv:Neptune|radix:Uranus|sext",
    "DK|conv:Neptune|radix:Neptune|tri",
    "FT|conv:Pluto|radix:Node|opp",
    "FT|conv:Pluto|radix:Sun|tri",
    "DK|conv:Pluto|radix:Uranus|sq",
)

MODEL_A_FEATURES = ("FT_sq_count", "INC_sq_count", "DK_sq_count")
MODEL_B_FEATURES = ("tight_aspect_count", "DK_sq_count")


def preselected_active_count(
    aspects_df: pd.DataFrame,
    *,
    orb_max: float = 1.0,
) -> pd.DataFrame:
    tight = aspects_df[aspects_df["best_orb"] <= orb_max].copy()
    tight = add_signature_column(tight)
    tight["report_date"] = tight["report_date"].map(report_date_key)
    pre = set(PRESELECTED_SIGNATURES)
    rows = []
    for rd, grp in tight.groupby("report_date"):
        active = grp[grp["signature"].isin(pre)]
        rows.append(
            {
                "report_date": rd,
                "preselected_sig_count": int(active["signature"].nunique()),
                "preselected_sig_orb_sum": float((orb_max - active["best_orb"]).clip(lower=0).sum()),
            }
        )
    return pd.DataFrame(rows)


def build_model_feature_frames(
    aspects_df: pd.DataFrame,
    *,
    orb_max: float = 1.0,
) -> dict[str, pd.DataFrame]:
    base = build_event_feature_matrix(aspects_df, orb_max=orb_max)
    pre = preselected_active_count(aspects_df, orb_max=orb_max)
    full = base.merge(pre, on="report_date", how="left").fillna(
        {"preselected_sig_count": 0, "preselected_sig_orb_sum": 0.0}
    )
    return {
        "full": full,
        "model_a": full[list(MODEL_A_FEATURES) + ["report_date"]],
        "model_b": full[list(MODEL_B_FEATURES) + ["report_date"]],
        "model_c": full[
            ["report_date", "preselected_sig_count", "preselected_sig_orb_sum"]
        ],
    }
