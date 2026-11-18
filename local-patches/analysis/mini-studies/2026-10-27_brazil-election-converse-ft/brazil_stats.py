"""Cross-sectional stats (N≈11, exploratory)."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from brazil_paths import UBER_STUDY

sys.path.insert(0, str(UBER_STUDY))
from phase_h_stats import pearson, spearman  # noqa: E402


def correlation_table(features: pd.DataFrame, returns: pd.DataFrame) -> pd.DataFrame:
    merged = features.merge(
        returns[returns["ticker"].isin(features["ticker"])][["ticker", "return_cc_pct"]],
        on="ticker",
        how="inner",
    )
    merged = merged.dropna(subset=["return_cc_pct"])
    cols = [
        "c2r_sq_count_1deg",
        "c2r_sq_opp_count_1deg",
        "c2r_hard_count_1deg",
        "c2c_sq_count_1deg",
        "c2c_sq_opp_count_1deg",
        "c2c_hard_count_1deg",
        "c2r_decl_contact_count_1deg",
        "c2c_decl_contact_count_1deg",
    ]
    rows = []
    y = merged["return_cc_pct"].astype(float)
    for c in cols:
        if c not in merged.columns:
            continue
        x = merged[c].astype(float)
        rows.append(
            {
                "feature": c,
                "pearson_r": pearson(x, y),
                "spearman_rho": spearman(x, y),
                "n": len(merged),
            }
        )
    return pd.DataFrame(rows)


def leave_one_out_correlations(features: pd.DataFrame, returns: pd.DataFrame, feature: str) -> pd.DataFrame:
    merged = features.merge(returns[["ticker", "return_cc_pct"]], on="ticker")
    rows = []
    for drop in merged["ticker"]:
        sub = merged[merged["ticker"] != drop]
        x = sub[feature].astype(float)
        y = sub["return_cc_pct"].astype(float)
        rows.append(
            {
                "dropped_ticker": drop,
                "feature": feature,
                "pearson_r": pearson(x, y) if len(sub) >= 3 else float("nan"),
            }
        )
    return pd.DataFrame(rows)


def loser_resilient_ranks(features: pd.DataFrame, returns: pd.DataFrame) -> pd.DataFrame:
    merged = features.merge(returns[["ticker", "return_cc_pct"]], on="ticker")
    merged = merged.sort_values("return_cc_pct")
    losers = set(merged.head(4)["ticker"])
    resilient = set(merged.tail(3)["ticker"])
    rows = []
    for label, grp in (("losers_bottom4", losers), ("resilient_top3", resilient)):
        sub = merged[merged["ticker"].isin(grp)]
        rows.append(
            {
                "group": label,
                "tickers": ",".join(sorted(grp)),
                "mean_return_cc_pct": float(sub["return_cc_pct"].mean()),
                "mean_c2r_hard_1deg": float(sub["c2r_hard_count_1deg"].mean()),
                "mean_c2c_hard_1deg": float(sub["c2c_hard_count_1deg"].mean()),
                "mean_c2r_sq_1deg": float(sub["c2r_sq_count_1deg"].mean()),
            }
        )
    return pd.DataFrame(rows)
