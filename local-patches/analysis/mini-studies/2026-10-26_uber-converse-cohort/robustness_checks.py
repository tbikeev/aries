"""Leave-one-out, orb sensitivity, subset tests, permutation nulls."""

from __future__ import annotations

import numpy as np
import pandas as pd

from feature_reduction import build_event_feature_matrix
from market_reactions import report_date_key

DEFAULT_ORB_GRID = (0.25, 0.5, 1.0, 2.0)


def merge_features_outcomes(
    feature_df: pd.DataFrame,
    reactions_df: pd.DataFrame,
) -> pd.DataFrame:
    feat = feature_df.copy()
    react = reactions_df[
        ["report_date", "r_cc_pct", "return_sign", "abs_r_cc_pct"]
    ].copy()
    feat["report_date"] = feat["report_date"].map(report_date_key)
    react["report_date"] = react["report_date"].map(report_date_key)
    return feat.merge(react, on="report_date", how="inner").sort_values("report_date")


def pearson_corr(x: pd.Series, y: pd.Series) -> float:
    if len(x) < 3 or x.nunique() <= 1:
        return float("nan")
    return float(x.corr(y))


def leave_one_out_correlations(
    merged: pd.DataFrame,
    features: list[str],
) -> pd.DataFrame:
    rows = []
    for feat in features:
        full_r = pearson_corr(merged[feat], merged["r_cc_pct"])
        for drop in merged["report_date"]:
            sub = merged[merged["report_date"] != drop]
            r = pearson_corr(sub[feat], sub["r_cc_pct"])
            rows.append(
                {
                    "feature": feat,
                    "dropped_report_date": drop,
                    "corr_full_sample": full_r,
                    "corr_loo": r,
                    "delta_from_full": r - full_r if pd.notna(r) and pd.notna(full_r) else np.nan,
                }
            )
    return pd.DataFrame(rows)


def leave_one_out_summary(loo_df: pd.DataFrame) -> pd.DataFrame:
    """One row per feature: full corr and LOO range."""
    rows = []
    for feat, grp in loo_df[loo_df["dropped_report_date"] != "__SUMMARY__"].groupby("feature"):
        full = grp["corr_full_sample"].iloc[0]
        loo = grp["corr_loo"]
        rows.append(
            {
                "feature": feat,
                "corr_full": full,
                "corr_loo_min": float(loo.min()),
                "corr_loo_max": float(loo.max()),
                "sign_stable": (loo > 0).all() or (loo < 0).all(),
                "max_abs_delta": float((loo - full).abs().max()),
            }
        )
    return pd.DataFrame(rows).sort_values("corr_full", key=abs, ascending=False)


def orb_sensitivity(
    aspects_df: pd.DataFrame,
    reactions_df: pd.DataFrame,
    features: list[str],
    orb_grid: tuple[float, ...] = DEFAULT_ORB_GRID,
) -> pd.DataFrame:
    rows = []
    react = reactions_df[~reactions_df["excluded"]]
    for orb in orb_grid:
        feat = build_event_feature_matrix(aspects_df, orb_max=orb)
        merged = merge_features_outcomes(feat, react)
        for f in features:
            rows.append(
                {
                    "orb_max_deg": orb,
                    "feature": f,
                    "n": len(merged),
                    "corr_with_r_cc": pearson_corr(merged[f], merged["r_cc_pct"]),
                    "corr_with_abs_r_cc": pearson_corr(merged[f], merged["abs_r_cc_pct"]),
                }
            )
    return pd.DataFrame(rows)


def subset_correlations(
    aspects_df: pd.DataFrame,
    reactions_df: pd.DataFrame,
    *,
    exclude_report_dates: set[str],
    orb_max: float = 1.0,
    features: list[str],
) -> pd.DataFrame:
    feat = build_event_feature_matrix(aspects_df, orb_max=orb_max)
    react = reactions_df[~reactions_df["excluded"]]
    merged = merge_features_outcomes(feat, react)
    excl = {report_date_key(d) for d in exclude_report_dates}
    sub = merged[~merged["report_date"].isin(excl)]
    rows = []
    for f in features:
        rows.append(
            {
                "subset": "excluding_declared_extremes",
                "n": len(sub),
                "feature": f,
                "corr_with_r_cc": pearson_corr(sub[f], sub["r_cc_pct"]),
                "corr_with_abs_r_cc": pearson_corr(sub[f], sub["abs_r_cc_pct"]),
            }
        )
    return pd.DataFrame(rows)


def permutation_correlation_test(
    merged: pd.DataFrame,
    feature: str,
    *,
    target: str = "r_cc_pct",
    n_perm: int = 4999,
    seed: int = 42,
) -> dict:
    rng = np.random.default_rng(seed)
    x = merged[feature].to_numpy(dtype=float)
    y = merged[target].to_numpy(dtype=float)
    obs = float(np.corrcoef(x, y)[0, 1])
    count = 0
    for _ in range(n_perm):
        yp = rng.permutation(y)
        rp = float(np.corrcoef(x, yp)[0, 1])
        if abs(rp) >= abs(obs):
            count += 1
    p = (count + 1) / (n_perm + 1)
    return {
        "feature": feature,
        "target": target,
        "n": len(merged),
        "observed_corr": obs,
        "permutation_p_two_sided": p,
        "n_perm": n_perm,
        "seed": seed,
    }
