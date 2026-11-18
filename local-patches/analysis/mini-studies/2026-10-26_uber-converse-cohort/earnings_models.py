"""Chronological feasibility checks (no leakage from reaction OHLC)."""

from __future__ import annotations

import json
from dataclasses import dataclass

import numpy as np
import pandas as pd

from market_reactions import report_date_key


def _merge_outcomes(feature_df: pd.DataFrame, reactions_df: pd.DataFrame) -> pd.DataFrame:
    feat = feature_df.copy()
    cols = ["report_date", "r_cc_pct", "return_sign", "abs_r_cc_pct"]
    optional = ["volume_ratio_20d"]
    react_cols = [c for c in cols + optional if c in reactions_df.columns]
    react = reactions_df[react_cols].copy()
    feat["report_date"] = feat["report_date"].map(report_date_key)
    react["report_date"] = react["report_date"].map(report_date_key)
    return feat.merge(react, on="report_date", how="inner").sort_values("report_date")


def _train_zscore(train: pd.Series, value: float) -> float:
    mu = float(train.mean())
    sd = float(train.std(ddof=0))
    if sd <= 1e-12:
        return 0.0
    return (value - mu) / sd


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
    df = _merge_outcomes(feature_df, reactions_df[~reactions_df["excluded"]])
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
        "extreme_share_of_valid": round(20 / n, 4) if n else None,
        "high_dimensional_risk": n < 40,
        "recommendation": (
            "Use 20 extremes for hypothesis generation only; evaluate patterns on all "
            f"{n} reactions with chronological splits and permutation tests before any predictive claim."
        ),
    }


def walk_forward_feature_model(
    feature_df: pd.DataFrame,
    reactions_df: pd.DataFrame,
    *,
    feature_cols: list[str],
    min_train: int = 8,
    model_name: str = "astro",
) -> WalkForwardResult:
    """
    Chronological walk-forward using train-only correlations (exploratory if features were chosen post-hoc).
    Direction score: sum(sign(corr_train) * zscore(feature)).
    Magnitude: train MAE for |r_cc| using same score split at train median.
    """
    df = _merge_outcomes(feature_df, reactions_df[~reactions_df["excluded"]])
    folds: list[dict] = []
    for i in range(min_train, len(df)):
        train = df.iloc[:i]
        test = df.iloc[i : i + 1]
        score = 0.0
        for col in feature_cols:
            if col not in train.columns:
                continue
            c = train[col].corr(train["r_cc_pct"])
            if pd.isna(c):
                continue
            score += float(np.sign(c)) * _train_zscore(train[col], float(test[col].iloc[0]))
        pred_sign = int(np.sign(score)) if score != 0 else 1
        actual_sign = int(test["return_sign"].iloc[0])
        train_scores = []
        for _, row in train.iterrows():
            s = 0.0
            for col in feature_cols:
                if col not in train.columns:
                    continue
                c = train[col].corr(train["r_cc_pct"])
                if pd.isna(c):
                    continue
                s += float(np.sign(c)) * _train_zscore(train[col], float(row[col]))
            train_scores.append(s)
        med = float(np.median(train_scores))
        abs_train = train["abs_r_cc_pct"]
        pred_abs = float(abs_train[pd.Series(train_scores) >= med].mean())
        if pd.isna(pred_abs):
            pred_abs = float(abs_train.mean())
        actual_abs = float(test["abs_r_cc_pct"].iloc[0])
        folds.append(
            {
                "model": model_name,
                "test_report_date": str(test["report_date"].iloc[0]),
                "pred_sign": pred_sign,
                "actual_sign": actual_sign,
                "direction_correct": pred_sign == actual_sign,
                "pred_abs_r_cc": pred_abs,
                "actual_abs_r_cc": actual_abs,
                "abs_error": abs(pred_abs - actual_abs),
                "score": score,
            }
        )
    dir_acc = float(np.mean([f["direction_correct"] for f in folds])) if folds else 0.0
    mae = float(np.mean([f["abs_error"] for f in folds])) if folds else float("nan")
    mae_baseline = float(np.mean([f["actual_abs_r_cc"] for f in folds])) if folds else float("nan")
    summary = {
        "model": model_name,
        "features": feature_cols,
        "n_events": len(df),
        "n_folds": len(folds),
        "direction_accuracy": dir_acc,
        "mae_abs_r_cc": mae,
        "mae_baseline_predict_train_mean_abs": mae_baseline,
        "note": "Exploratory on same sample if features were selected after viewing outcomes.",
    }
    return WalkForwardResult(folds=folds, summary=summary)


def walk_forward_volatility_baseline(
    reactions_df: pd.DataFrame,
    *,
    min_train: int = 8,
) -> WalkForwardResult:
    """Predict |r_cc| with train mean; direction with majority sign."""
    react = reactions_df[~reactions_df["excluded"]].copy()
    react["report_date"] = react["report_date"].map(report_date_key)
    df = react.dropna(subset=["r_cc_pct", "abs_r_cc_pct"]).sort_values("report_date")
    folds = []
    for i in range(min_train, len(df)):
        train = df.iloc[:i]
        test = df.iloc[i : i + 1]
        pred_abs = float(train["abs_r_cc_pct"].mean())
        majority = int(np.sign(train["return_sign"].mean())) or 1
        folds.append(
            {
                "test_report_date": str(test["report_date"].iloc[0]),
                "pred_abs_r_cc": pred_abs,
                "actual_abs_r_cc": float(test["abs_r_cc_pct"].iloc[0]),
                "abs_error": abs(pred_abs - float(test["abs_r_cc_pct"].iloc[0])),
                "direction_correct": majority == int(test["return_sign"].iloc[0]),
            }
        )
    summary = {
        "model": "baseline_history_mean_abs",
        "n_folds": len(folds),
        "direction_accuracy": float(np.mean([f["direction_correct"] for f in folds])) if folds else 0,
        "mae_abs_r_cc": float(np.mean([f["abs_error"] for f in folds])) if folds else float("nan"),
    }
    return WalkForwardResult(folds=folds, summary=summary)


def walk_forward_large_move_direction(
    feature_df: pd.DataFrame,
    reactions_df: pd.DataFrame,
    *,
    feature_cols: list[str],
    min_train: int = 8,
    model_name: str = "astro_large_move",
) -> WalkForwardResult:
    """Question B: direction accuracy only when |r_cc| >= train 75th percentile of |r_cc|."""
    df = _merge_outcomes(feature_df, reactions_df[~reactions_df["excluded"]])
    folds = []
    for i in range(min_train, len(df)):
        train = df.iloc[:i]
        test = df.iloc[i : i + 1]
        thresh = float(train["abs_r_cc_pct"].quantile(0.75))
        if float(test["abs_r_cc_pct"].iloc[0]) < thresh:
            continue
        score = 0.0
        for col in feature_cols:
            c = train[col].corr(train["r_cc_pct"])
            if pd.isna(c):
                continue
            score += float(np.sign(c)) * _train_zscore(train[col], float(test[col].iloc[0]))
        pred_sign = int(np.sign(score)) if score != 0 else 1
        actual_sign = int(test["return_sign"].iloc[0])
        folds.append(
            {
                "model": model_name,
                "test_report_date": str(test["report_date"].iloc[0]),
                "train_abs_p75": thresh,
                "actual_abs_r_cc": float(test["abs_r_cc_pct"].iloc[0]),
                "direction_correct": pred_sign == actual_sign,
            }
        )
    summary = {
        "model": model_name,
        "features": feature_cols,
        "n_folds_large_moves_only": len(folds),
        "direction_accuracy": float(np.mean([f["direction_correct"] for f in folds])) if folds else 0,
    }
    return WalkForwardResult(folds=folds, summary=summary)
