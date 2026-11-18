"""Small-sample correlation diagnostics (exploratory, N=26 earnings)."""

from __future__ import annotations

import numpy as np
import pandas as pd


def pearson(x: pd.Series, y: pd.Series) -> float:
    if len(x) < 3 or x.nunique() <= 1:
        return float("nan")
    return float(x.corr(y, method="pearson"))


def spearman(x: pd.Series, y: pd.Series) -> float:
    if len(x) < 3 or x.nunique() <= 1:
        return float("nan")
    rx = x.rank(method="average")
    ry = y.rank(method="average")
    return float(rx.corr(ry, method="pearson"))


def bootstrap_ci(
    x: np.ndarray,
    y: np.ndarray,
    *,
    n_boot: int = 4000,
    seed: int = 42,
    alpha: float = 0.05,
) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    n = len(x)
    rs = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n)
        if np.std(x[idx]) < 1e-12:
            continue
        rs.append(float(np.corrcoef(x[idx], y[idx])[0, 1]))
    if not rs:
        return float("nan"), float("nan")
    lo = float(np.quantile(rs, alpha / 2))
    hi = float(np.quantile(rs, 1 - alpha / 2))
    return lo, hi


def leave_one_out_range(x: pd.Series, y: pd.Series) -> tuple[float, float]:
    vals = []
    for drop in x.index:
        mask = x.index != drop
        vals.append(pearson(x[mask], y[mask]))
    return float(np.nanmin(vals)), float(np.nanmax(vals))


def permutation_p(x: np.ndarray, y: np.ndarray, *, n_perm: int = 4999, seed: int = 42) -> dict:
    rng = np.random.default_rng(seed)
    obs = float(np.corrcoef(x, y)[0, 1])
    count = 0
    for _ in range(n_perm):
        yp = rng.permutation(y)
        rp = float(np.corrcoef(x, yp)[0, 1])
        if abs(rp) >= abs(obs):
            count += 1
    return {
        "observed_r": obs,
        "p_two_sided_shuffle": (count + 1) / (n_perm + 1),
        "null": "iid_shuffle_returns",
        "n_perm": n_perm,
    }


def correlation_report(df: pd.DataFrame, feature: str, target: str, *, seed: int = 42) -> dict:
    sub = df[[feature, target]].dropna()
    x = sub[feature].to_numpy(dtype=float)
    y = sub[target].to_numpy(dtype=float)
    lo, hi = bootstrap_ci(x, y, seed=seed)
    loo_lo, loo_hi = leave_one_out_range(sub[feature], sub[target])
    perm = permutation_p(x, y, seed=seed)
    return {
        "feature": feature,
        "target": target,
        "n": len(sub),
        "pearson_r": pearson(sub[feature], sub[target]),
        "spearman_rho": spearman(sub[feature], sub[target]),
        "bootstrap_ci_95_lo": lo,
        "bootstrap_ci_95_hi": hi,
        "loo_r_min": loo_lo,
        "loo_r_max": loo_hi,
        **perm,
    }
