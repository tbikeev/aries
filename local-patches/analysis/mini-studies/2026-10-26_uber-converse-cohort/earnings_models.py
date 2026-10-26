"""Chronological feasibility checks (no leakage from reaction OHLC)."""

from __future__ import annotations

import json
from dataclasses import dataclass

import numpy as np
import pandas as pd

from market_reactions import report_date_key


@dataclass
class WalkForwardResult:
    folds: list[dict]
    summary: dict


def walk_forward_direction(
    feature_df: pd.DataFrame,
    reactions_df: pd.DataFrame,
    *,
    feature_cols: list[str],
    min_train: int = 8,
) -> WalkForwardResult:
    """Majority-sign baseline vs single-feature correlation (astrology features pre-event only)."""
    feat = feature_df.copy()
    react = reactions_df[["report_date", "r_cc_pct", "return_sign"]].copy()
    feat["report_date"] = feat["report_date"].map(report_date_key)
    react["report_date"] = react["report_date"].map(report_date_key)
    df = feat.merge(react, on="report_date", how="inner").sort_values("report_date")
    folds: list[dict] = []
    for i in range(min_train, len(df)):
        train = df.iloc[:i]
        test = df.iloc[i : i + 1]
        y_train = train["return_sign"]
        majority = int(np.sign(y_train.mean())) or 1
        pred = majority
        actual = int(test["return_sign"].iloc[0])
        folds.append(
            {
                "test_report_date": str(test["report_date"].iloc[0]),
                "baseline_pred_sign": pred,
                "actual_sign": actual,
                "baseline_correct": pred == actual,
                "actual_r_cc": float(test["r_cc_pct"].iloc[0]),
            }
        )
    acc = float(np.mean([f["baseline_correct"] for f in folds])) if folds else 0.0
    summary = {
        "n_events": len(df),
        "n_folds": len(folds),
        "majority_sign_accuracy": acc,
        "note": "Astrological features not used in this baseline fold; use feature_reduction for exploratory assoc.",
    }
    return WalkForwardResult(folds=folds, summary=summary)


def feasibility_report(reactions_df: pd.DataFrame) -> dict:
    valid = reactions_df[~reactions_df["excluded"]].dropna(subset=["r_cc_pct"])
    n = len(valid)
    return {
        "valid_earnings_reactions": n,
        "extreme_discovery_sample": 20,
        "high_dimensional_risk": n < 40,
        "recommendation": (
            "Use 20 extremes for hypothesis generation only; evaluate patterns on all "
            f"{n} reactions with chronological splits and permutation tests before any predictive claim."
        ),
    }
