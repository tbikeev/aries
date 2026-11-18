"""Incremental models L / D / L+D / L+R / L+N (exploratory)."""

from __future__ import annotations

import numpy as np
import pandas as pd


def _ols_fit(y: np.ndarray, X: np.ndarray) -> tuple[np.ndarray, float]:
    Xd = np.column_stack([np.ones(len(y)), X])
    beta, _, _, _ = np.linalg.lstsq(Xd, y, rcond=None)
    pred = Xd @ beta
    ss_res = float(np.sum((y - pred) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    return beta, r2


def _partial_corr(x: np.ndarray, y: np.ndarray, Z: np.ndarray) -> float:
    def resid(a, B):
        Bm = np.column_stack([np.ones(len(a)), B])
        b, _, _, _ = np.linalg.lstsq(Bm, a, rcond=None)
        return a - Bm @ b

    if Z.ndim == 1:
        Z = Z.reshape(-1, 1)
    return float(np.corrcoef(resid(x, Z), resid(y, Z))[0, 1])


def loo_r2(y: np.ndarray, X: np.ndarray) -> float:
    preds = []
    for i in range(len(y)):
        mask = np.arange(len(y)) != i
        Xdm = np.column_stack([np.ones(mask.sum()), X[mask]])
        beta, _, _, _ = np.linalg.lstsq(Xdm, y[mask], rcond=None)
        preds.append(float(np.dot([1.0, *X[i]], beta)))
    ss_res = float(np.sum((y - np.array(preds)) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    return 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")


def run_incremental_models(df: pd.DataFrame, target: str = "r_cc_pct") -> pd.DataFrame:
    cols = {
        "L": ["DK_sq_count_orb10"],
        "D": ["DK_par_count_orb05", "DK_cpar_count_orb05"],
        "L+D": ["DK_sq_count_orb10", "DK_par_count_orb05", "DK_cpar_count_orb05"],
        "L+R": ["DK_sq_count_orb10", "DK_double_activation_count"],
        "L+N": ["DK_sq_count_orb10", "network_both_endpoints"],
    }
    sub = df.dropna(subset=[target])
    y = sub[target].to_numpy(float)
    rows = []
    base_r2 = None
    for name, feats in cols.items():
        use = [f for f in feats if f in sub.columns]
        if not use:
            continue
        X = sub[use].to_numpy(float)
        beta, r2 = _ols_fit(y, X)
        if name == "L":
            base_r2 = r2
        row = {
            "model": name,
            "target": target,
            "features": ",".join(use),
            "n": len(y),
            "r2_in_sample": r2,
            "delta_r2_vs_L": r2 - base_r2 if base_r2 is not None and name != "L" else 0.0,
            "loo_r2": loo_r2(y, X) if len(y) >= 8 else float("nan"),
        }
        if name == "L+D" and "DK_sq_count_orb10" in use:
            z = sub[[c for c in use if c != "DK_sq_count_orb10"]].to_numpy(float)
            if z.shape[1]:
                row["partial_corr_DK_sq_given_decl"] = _partial_corr(
                    sub["DK_sq_count_orb10"].to_numpy(float), y, z
                )
        rows.append(row)
    return pd.DataFrame(rows)
