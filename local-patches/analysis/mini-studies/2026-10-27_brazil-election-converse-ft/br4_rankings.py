"""BR-4 exploratory ranked cell tables."""

from __future__ import annotations

import pandas as pd


def _merge_unc(pooled: pd.DataFrame, unc: pd.DataFrame, mode: str, *, exclude_discovery: bool) -> pd.DataFrame:
    m = pooled[pooled["mode"] == mode].copy()
    if unc.empty:
        m["exclude_discovery"] = exclude_discovery
        return m
    u = unc[(unc["mode"] == mode) & (unc["exclude_discovery"] == exclude_discovery)].copy()
    if mode == "C2C":
        keys = ["planet_1", "planet_2", "aspect"]
    else:
        keys = ["converse_planet", "radix_planet", "aspect"]
    out = m.merge(u, on=keys, how="left", suffixes=("", "_unc"))
    out["exclude_discovery"] = exclude_discovery
    return out


def _top(m: pd.DataFrame, *, tail: str, metric: str, mode: str, top_n: int) -> pd.DataFrame:
    m = m[m["ranking_eligible"] == True].copy()  # noqa: E712
    if tail == "crash":
        m = m[m["delta_F"] > 0]
        if metric == "frequency":
            m = m.sort_values("delta_F_z_standardized", ascending=False, na_position="last")
        else:
            m = m.sort_values("delta_P_z_standardized", ascending=False, na_position="last")
    else:
        m = m[m["delta_F"] < 0]
        if metric == "frequency":
            m = m.sort_values("delta_F_z_standardized", ascending=True, na_position="last")
        else:
            m = m.sort_values("delta_P_z_standardized", ascending=True, na_position="last")
    m = m.head(top_n)
    m["rank_mode"] = mode
    m["rank_tail"] = tail
    m["rank_metric"] = metric
    return m


def build_rankings(
    c2c_pooled: pd.DataFrame,
    c2r_pooled: pd.DataFrame,
    unc_all: pd.DataFrame,
    *,
    c2c_no_discovery: pd.DataFrame | None = None,
    c2r_no_discovery: pd.DataFrame | None = None,
    top_n: int = 20,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    crash_parts, rally_parts = [], []
    for exclude_discovery in (False, True):
        c2c_src = c2c_no_discovery if exclude_discovery and c2c_no_discovery is not None else c2c_pooled
        c2r_src = c2r_no_discovery if exclude_discovery and c2r_no_discovery is not None else c2r_pooled
        for mode, pooled in (("C2C", c2c_src), ("C2R", c2r_src)):
            m = _merge_unc(pooled, unc_all, mode, exclude_discovery=exclude_discovery)
            for tail in ("crash", "rally"):
                for metric in ("frequency", "power"):
                    block = _top(m, tail=tail, metric=metric, mode=mode, top_n=top_n)
                    (crash_parts if tail == "crash" else rally_parts).append(block)
    return pd.concat(crash_parts, ignore_index=True), pd.concat(rally_parts, ignore_index=True)
