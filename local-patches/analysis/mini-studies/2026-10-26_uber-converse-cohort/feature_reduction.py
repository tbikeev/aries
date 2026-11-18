"""Feature-space reduction (interpretable groups)."""

from __future__ import annotations

import pandas as pd

from market_reactions import report_date_key


def build_event_feature_matrix(
    aspects_df: pd.DataFrame,
    *,
    orb_max: float = 1.0,
) -> pd.DataFrame:
    """One row per earnings event: counts of tight aspects by cohort and aspect type."""
    tight = aspects_df[aspects_df["best_orb"] <= orb_max].copy()
    rows = []
    for (report_date, reaction_session), grp in tight.groupby(["report_date", "reaction_session"]):
        row = {
            "report_date": report_date_key(report_date),
            "reaction_session": report_date_key(reaction_session),
            "tight_aspect_count": len(grp),
            "min_orb": float(grp["best_orb"].min()),
            "mean_orb": float(grp["best_orb"].mean()),
        }
        for rk in ("FT", "INC", "DK"):
            sub = grp[grp["radix_key"] == rk]
            row[f"{rk}_tight_count"] = len(sub)
            for asp in ("conj", "sq", "tri", "opp", "sext"):
                row[f"{rk}_{asp}_count"] = int((sub["best_aspect"] == asp).sum())
        rows.append(row)
    return pd.DataFrame(rows)


def rank_feature_groups(feature_df: pd.DataFrame, reactions_df: pd.DataFrame) -> pd.DataFrame:
    feat = feature_df.copy()
    react = reactions_df[["report_date", "r_cc_pct", "return_sign"]].copy()
    feat["report_date"] = feat["report_date"].map(report_date_key)
    react["report_date"] = react["report_date"].map(report_date_key)
    merged = feat.merge(react, on="report_date", how="inner")
    cols = [c for c in merged.columns if c.endswith("_count") or c == "tight_aspect_count"]
    rows = []
    for col in cols:
        if merged[col].nunique() <= 1:
            continue
        corr = merged[col].corr(merged["r_cc_pct"])
        rows.append(
            {
                "feature": col,
                "corr_with_r_cc": corr,
                "mean_when_up": merged.loc[merged["return_sign"] > 0, col].mean(),
                "mean_when_down": merged.loc[merged["return_sign"] < 0, col].mean(),
            }
        )
    return pd.DataFrame(rows).sort_values("corr_with_r_cc", key=abs, ascending=False)
