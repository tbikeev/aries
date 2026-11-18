"""Pooled and company-level statistics for cross-company study."""

from __future__ import annotations

import numpy as np
import pandas as pd

from phase_h_stats import bootstrap_ci, correlation_report, leave_one_out_range, pearson, spearman


def company_correlation_table(events: pd.DataFrame, *, feature: str, target: str) -> pd.DataFrame:
    rows = []
    for ticker, grp in events.groupby("ticker"):
        if len(grp) < 5:
            continue
        rep = correlation_report(grp, feature, target)
        rep["ticker"] = ticker
        rep["n_events"] = len(grp)
        rep["sector_bucket"] = grp["sector_bucket"].iloc[0]
        rows.append(rep)
    return pd.DataFrame(rows)


def pooled_ols_with_fe(
    df: pd.DataFrame,
    *,
    target: str,
    feature: str,
    include_company_fe: bool,
) -> dict:
    """Simple OLS: y ~ feature [+ company dummies]. Cluster-robust SE not implemented; report n clusters."""
    sub = df[[target, feature, "ticker"]].dropna()
    if len(sub) < 10:
        return {"n": len(sub), "error": "insufficient rows"}
    y = sub[target].to_numpy(dtype=float)
    x_feat = sub[feature].to_numpy(dtype=float)
    if include_company_fe:
        dummies = pd.get_dummies(sub["ticker"], drop_first=True, dtype=float)
        X = np.column_stack([np.ones(len(sub)), x_feat, dummies.to_numpy()])
        names = ["intercept", feature] + list(dummies.columns)
    else:
        X = np.column_stack([np.ones(len(sub)), x_feat])
        names = ["intercept", feature]
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    y_hat = X @ beta
    resid = y - y_hat
    n, k = X.shape
    if n <= k:
        return {"n": n, "error": "rank deficient"}
    sigma2 = float((resid @ resid) / (n - k))
    try:
        cov = sigma2 * np.linalg.inv(X.T @ X)
        se = np.sqrt(np.diag(cov))
    except np.linalg.LinAlgError:
        se = np.full(k, np.nan)
    out = {
        "n_events": n,
        "n_companies": int(sub["ticker"].nunique()),
        "include_company_fe": include_company_fe,
        "target": target,
        "feature": feature,
        "coefficients": {names[i]: float(beta[i]) for i in range(k)},
        "std_errors": {names[i]: float(se[i]) for i in range(k)},
        "r2_in_sample": float(1 - (resid @ resid) / ((y - y.mean()) @ (y - y.mean()))),
    }
    return out


def direction_baselines(events: pd.DataFrame, *, target: str, feature: str, stage: str) -> pd.DataFrame:
    """Compare sign prediction baselines on development/holdout."""
    sub = events[events["stage"] == stage].dropna(subset=[target, feature]).copy()
    if sub.empty:
        return pd.DataFrame()
    sub["actual_up"] = (sub[target] > 0).astype(int)

    # Majority direction per company on train portion omitted — use global majority for simplicity on stage
    maj = int(sub["actual_up"].mean() >= 0.5)
    sub["pred_maj"] = maj

    hist_mean = sub.groupby("ticker")[target].transform("mean")
    sub["pred_hist_sign"] = (hist_mean > 0).astype(int)

    # Frozen hypothesis: higher squares → lower return → predict down when squares above median
    med = sub[feature].median()
    sub["pred_sq"] = (sub[feature] > med).astype(int)  # 1 = high squares
    sub["pred_sq_direction"] = 1 - sub["pred_sq"]  # predict up when low squares

    def acc(col: str) -> float:
        return float((sub[col] == sub["actual_up"]).mean())

    rows = [
        {"model": "majority_direction", "stage": stage, "accuracy": acc("pred_maj")},
        {"model": "historical_company_mean_sign", "stage": stage, "accuracy": acc("pred_hist_sign")},
        {"model": "ceo_square_median_split", "stage": stage, "accuracy": acc("pred_sq_direction")},
    ]
    return pd.DataFrame(rows)


def magnitude_metrics(events: pd.DataFrame, *, target: str, feature: str, stage: str) -> dict:
    sub = events[events["stage"] == stage].dropna(subset=[target, feature])
    if len(sub) < 5:
        return {}
    y = sub[target]
    hist = sub.groupby("ticker")[target].transform("mean")
    mae_hist = float((y - hist).abs().mean())
    # Naive linear prediction from feature only (not tuned)
    x = sub[feature]
    if x.nunique() <= 1:
        return {"mae_hist_baseline": mae_hist}
    slope = float(np.cov(x, y)[0, 1] / np.var(x))
    intercept = float(y.mean() - slope * x.mean())
    pred = intercept + slope * x
    mae_feat = float((y - pred).abs().mean())
    return {
        "stage": stage,
        "mae_hist_baseline": mae_hist,
        "mae_feature_linear": mae_feat,
        "corr_feature_target": pearson(x, y),
    }
