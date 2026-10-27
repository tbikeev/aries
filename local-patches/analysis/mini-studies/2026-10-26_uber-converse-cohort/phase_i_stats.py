"""Correlation battery with FDR over predefined families."""

from __future__ import annotations

import numpy as np
import pandas as pd

from phase_h_stats import bootstrap_ci, leave_one_out_range, pearson, permutation_p, spearman

EARNINGS_OUTCOMES = (
    "r_cc_pct",
    "r_gap_pct",
    "r_intra_pct",
    "abs_r_cc_pct",
    "abs_r_gap_pct",
)


def predefined_decl_features() -> list[str]:
    cols = []
    for rk in ("DK", "FT", "INC"):
        for metric in ("par_count", "cpar_count", "decl_total", "decl_exact_15arcmin_count"):
            if metric == "decl_exact_15arcmin_count":
                cols.append(f"{rk}_{metric}")
            else:
                for tag in ("orb05", "orb10"):
                    cols.append(f"{rk}_{metric}_{tag}")
    return cols


def correlation_battery(df: pd.DataFrame, features: list[str]) -> pd.DataFrame:
    rows = []
    for feat in features:
        if feat not in df.columns:
            continue
        for target in EARNINGS_OUTCOMES:
            if target not in df.columns:
                continue
            sub = df[[feat, target]].dropna()
            if len(sub) < 4:
                continue
            x = sub[feat].to_numpy(float)
            y = sub[target].to_numpy(float)
            lo, hi = bootstrap_ci(x, y)
            loo_lo, loo_hi = leave_one_out_range(sub[feat], sub[target])
            perm = permutation_p(x, y)
            rows.append(
                {
                    "feature": feat,
                    "target": target,
                    "n": len(sub),
                    "nonzero_feature_events": int((sub[feat] != 0).sum()),
                    "feature_variance": float(sub[feat].var()),
                    "pearson_r": pearson(sub[feat], sub[target]),
                    "spearman_rho": spearman(sub[feat], sub[target]),
                    "bootstrap_ci_95_lo": lo,
                    "bootstrap_ci_95_hi": hi,
                    "loo_r_min": loo_lo,
                    "loo_r_max": loo_hi,
                    "perm_p_shuffle": perm["p_two_sided_shuffle"],
                }
            )
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    out["abs_r"] = out["pearson_r"].abs()
    # BH-FDR across all tests in this battery
    p = out["perm_p_shuffle"].to_numpy()
    order = np.argsort(p)
    ranked = np.empty_like(p)
    m = len(p)
    for i, idx in enumerate(order):
        ranked[idx] = p[idx] * m / (i + 1)
    out["bh_q_value"] = np.minimum.accumulate(ranked[order[::-1]])[::-1][order]
    return out.sort_values("abs_r", ascending=False)
