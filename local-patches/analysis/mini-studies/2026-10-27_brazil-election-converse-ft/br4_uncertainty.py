"""BR-4 event-level bootstrap, permutation, and FDR."""

from __future__ import annotations

import numpy as np
import pandas as pd

from br4_constants import BOOTSTRAP_DRAWS, PERMUTATION_DRAWS, RNG_SEED
from br4_differences import LoadedControlled, _metrics, _pooled_stats


def _bootstrap_deltas(
    data: LoadedControlled,
    active_slice: np.ndarray,
    power_slice: np.ndarray,
    *,
    neg_ei: np.ndarray,
    pos_ei: np.ndarray,
    rng: np.random.Generator,
) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    """Event-level bootstrap for delta_F and delta_P (mean, ci_lo, ci_hi)."""
    boots_f: list[float] = []
    boots_p: list[float] = []
    for _ in range(BOOTSTRAP_DRAWS):
        nb = rng.choice(neg_ei, size=len(neg_ei), replace=True)
        pb = rng.choice(pos_ei, size=len(pos_ei), replace=True)
        Nn, nn, sn = _pooled_stats(active_slice, power_slice, data.eligible, nb)
        Np, np_, sp = _pooled_stats(active_slice, power_slice, data.eligible, pb)
        m = _metrics(Nn, nn, sn, Np, np_, sp)
        if np.isfinite(m["delta_F"]):
            boots_f.append(m["delta_F"])
        if np.isfinite(m["delta_P"]):
            boots_p.append(m["delta_P"])

    def _summ(boots: list[float]) -> tuple[float, float, float]:
        if not boots:
            return float("nan"), float("nan"), float("nan")
        arr = np.asarray(boots)
        return float(arr.mean()), float(np.quantile(arr, 0.025)), float(np.quantile(arr, 0.975))

    return _summ(boots_f), _summ(boots_p)


def _permutation_p(
    data: LoadedControlled, active_slice: np.ndarray, power_slice: np.ndarray, obs_delta: float, *, neg_ei, pos_ei, rng
) -> float:
    all_ei = np.concatenate([neg_ei, pos_ei])
    labels = np.array([0] * len(neg_ei) + [1] * len(pos_ei))
    if not np.isfinite(obs_delta):
        return float("nan")
    cnt = 0
    for _ in range(PERMUTATION_DRAWS):
        rng.shuffle(labels)
        ne = all_ei[labels == 0]
        pe = all_ei[labels == 1]
        Nn, nn, sn = _pooled_stats(active_slice, power_slice, data.eligible, ne)
        Np, np_, sp = _pooled_stats(active_slice, power_slice, data.eligible, pe)
        d = _metrics(Nn, nn, sn, Np, np_, sp)["delta_F"]
        if np.isfinite(d) and abs(d) >= abs(obs_delta):
            cnt += 1
    return (cnt + 1) / (PERMUTATION_DRAWS + 1)


def benjamini_hochberg(pvals: np.ndarray) -> np.ndarray:
    p = np.asarray(pvals, dtype=float)
    out = np.full_like(p, np.nan)
    mask = np.isfinite(p)
    if mask.sum() == 0:
        return out
    pv = p[mask]
    m = len(pv)
    order = np.argsort(pv)
    ranked = pv[order]
    q = ranked * m / (np.arange(m) + 1)
    q = np.minimum.accumulate(q[::-1])[::-1]
    q = np.clip(q, 0, 1)
    filled = np.empty(m)
    filled[order] = q
    out[mask] = filled
    return out


def add_uncertainty_c2c(data: LoadedControlled, df: pd.DataFrame, *, exclude_discovery: bool) -> pd.DataFrame:
    neg_ei = data.neg_ei
    pos_ei = data.pos_ei
    if exclude_discovery and len(data.discovery_ei):
        neg_ei = neg_ei[~np.isin(neg_ei, data.discovery_ei)]
        pos_ei = pos_ei[~np.isin(pos_ei, data.discovery_ei)]
    rng = np.random.default_rng(RNG_SEED + (1 if exclude_discovery else 0))
    rows = []
    for _, r in df.iterrows():
        pk, ak = int(r["pair_index"]), int(r["aspect_index"])
        act = data.c2c_active[:, :, pk, ak]
        pwr = data.c2c_power[:, :, pk, ak]
        obs_d = float(r["delta_F"])
        obs_p = float(r["delta_P"])
        (mean_bf, lo_f, hi_f), (mean_bp, lo_p, hi_p) = _bootstrap_deltas(
            data, act, pwr, neg_ei=neg_ei, pos_ei=pos_ei, rng=rng
        )
        se_f = (hi_f - lo_f) / (2 * 1.96) if np.isfinite(hi_f) and np.isfinite(lo_f) else float("nan")
        se_p = (hi_p - lo_p) / (2 * 1.96) if np.isfinite(hi_p) and np.isfinite(lo_p) else float("nan")
        z_f = obs_d / se_f if se_f and se_f > 0 else float("nan")
        z_p = obs_p / se_p if se_p and se_p > 0 else float("nan")
        p_perm = _permutation_p(data, act, pwr, obs_d, neg_ei=neg_ei, pos_ei=pos_ei, rng=rng)
        rows.append(
            {
                "mode": "C2C",
                "planet_1": r["planet_1"],
                "planet_2": r["planet_2"],
                "aspect": r["aspect"],
                "delta_F": obs_d,
                "delta_F_boot_mean": mean_bf,
                "delta_F_ci_lo": lo_f,
                "delta_F_ci_hi": hi_f,
                "delta_F_z_standardized": z_f,
                "delta_P": obs_p,
                "delta_P_boot_mean": mean_bp,
                "delta_P_ci_lo": lo_p,
                "delta_P_ci_hi": hi_p,
                "delta_P_z_standardized": z_p,
                "perm_p_delta_F": p_perm,
                "exclude_discovery": exclude_discovery,
            }
        )
    out = pd.DataFrame(rows)
    out["perm_p_delta_F_fdr_bh"] = benjamini_hochberg(out["perm_p_delta_F"].to_numpy())
    return out


def add_uncertainty_c2r(data: LoadedControlled, df: pd.DataFrame, *, exclude_discovery: bool) -> pd.DataFrame:
    neg_ei = data.neg_ei
    pos_ei = data.pos_ei
    if exclude_discovery and len(data.discovery_ei):
        neg_ei = neg_ei[~np.isin(neg_ei, data.discovery_ei)]
        pos_ei = pos_ei[~np.isin(pos_ei, data.discovery_ei)]
    rng = np.random.default_rng(RNG_SEED + 2 + (1 if exclude_discovery else 0))
    rows = []
    for _, r in df.iterrows():
        ci, ri, ak = int(r["converse_index"]), int(r["radix_index"]), int(r["aspect_index"])
        act = data.c2r_active[:, :, ci, ri, ak]
        pwr = data.c2r_power[:, :, ci, ri, ak]
        obs_d = float(r["delta_F"])
        obs_p = float(r["delta_P"])
        (mean_bf, lo_f, hi_f), (mean_bp, lo_p, hi_p) = _bootstrap_deltas(
            data, act, pwr, neg_ei=neg_ei, pos_ei=pos_ei, rng=rng
        )
        se_f = (hi_f - lo_f) / (2 * 1.96) if np.isfinite(hi_f) and np.isfinite(lo_f) else float("nan")
        se_p = (hi_p - lo_p) / (2 * 1.96) if np.isfinite(hi_p) and np.isfinite(lo_p) else float("nan")
        z_f = obs_d / se_f if se_f and se_f > 0 else float("nan")
        z_p = obs_p / se_p if se_p and se_p > 0 else float("nan")
        p_perm = _permutation_p(data, act, pwr, obs_d, neg_ei=neg_ei, pos_ei=pos_ei, rng=rng)
        rows.append(
            {
                "mode": "C2R",
                "converse_planet": r["converse_planet"],
                "radix_planet": r["radix_planet"],
                "aspect": r["aspect"],
                "delta_F": obs_d,
                "delta_F_boot_mean": mean_bf,
                "delta_F_ci_lo": lo_f,
                "delta_F_ci_hi": hi_f,
                "delta_F_z_standardized": z_f,
                "delta_P": obs_p,
                "delta_P_boot_mean": mean_bp,
                "delta_P_ci_lo": lo_p,
                "delta_P_ci_hi": hi_p,
                "delta_P_z_standardized": z_p,
                "perm_p_delta_F": p_perm,
                "exclude_discovery": exclude_discovery,
            }
        )
    out = pd.DataFrame(rows)
    out["perm_p_delta_F_fdr_bh"] = benjamini_hochberg(out["perm_p_delta_F"].to_numpy())
    return out
