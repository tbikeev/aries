"""H4: do FT and INC add information beyond DK (exploratory N=26)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from phase_h_stats import pearson, spearman


def _ols_r2(y: np.ndarray, X: np.ndarray) -> float:
    X = np.column_stack([np.ones(len(y)), X])
    beta, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
    pred = X @ beta
    ss_res = float(np.sum((y - pred) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    return 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")


def _partial_corr(x: np.ndarray, y: np.ndarray, Z: np.ndarray) -> float:
    """Partial correlation x,y | Z (OLS residuals)."""
    def resid(a: np.ndarray, B: np.ndarray) -> np.ndarray:
        Bm = np.column_stack([np.ones(len(a)), B])
        b, _, _, _ = np.linalg.lstsq(Bm, a, rcond=None)
        return a - Bm @ b

    if Z.ndim == 1:
        Z = Z.reshape(-1, 1)
    rx = resid(x, Z)
    ry = resid(y, Z)
    return float(np.corrcoef(rx, ry)[0, 1])


def run_h4(df: pd.DataFrame, target: str = "r_cc_pct") -> dict:
    sub = df.dropna(
        subset=[target, "DK_sq_count_orb10", "FT_sq_count_orb10", "INC_sq_count_orb10"]
    )
    y = sub[target].to_numpy(dtype=float)
    dk = sub["DK_sq_count_orb10"].to_numpy(dtype=float)
    ft = sub["FT_sq_count_orb10"].to_numpy(dtype=float)
    inc = sub["INC_sq_count_orb10"].to_numpy(dtype=float)

    r2_dk = _ols_r2(y, dk.reshape(-1, 1))
    r2_all = _ols_r2(y, np.column_stack([dk, ft, inc]))
    partial_dk = _partial_corr(dk, y, np.column_stack([ft, inc]))
    partial_ft = _partial_corr(ft, y, np.column_stack([dk, inc]))
    partial_inc = _partial_corr(inc, y, np.column_stack([dk, ft]))

    return {
        "exploratory": True,
        "n": len(sub),
        "target": target,
        "pearson_DK": pearson(sub["DK_sq_count_orb10"], sub[target]),
        "pearson_FT": pearson(sub["FT_sq_count_orb10"], sub[target]),
        "pearson_INC": pearson(sub["INC_sq_count_orb10"], sub[target]),
        "r2_DK_only": r2_dk,
        "r2_DK_FT_INC": r2_all,
        "delta_r2_adding_FT_INC": r2_all - r2_dk,
        "partial_corr_DK_given_FT_INC": partial_dk,
        "partial_corr_FT_given_DK_INC": partial_ft,
        "partial_corr_INC_given_DK_FT": partial_inc,
        "note": "Large delta_r2 on N=26 is not validated; signs of FT/INC partials indicate incremental direction only.",
    }
