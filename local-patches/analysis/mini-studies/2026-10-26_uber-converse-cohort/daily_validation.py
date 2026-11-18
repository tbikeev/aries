"""Stratified correlations and embargoed validation for daily panel."""

from __future__ import annotations

import numpy as np
import pandas as pd

from daily_market import FORWARD_EMBARGO_SESSIONS
from earnings_paths import FROZEN_FEATURE_SPECS, FROZEN_ORB_THRESHOLDS_DEG

def _orb_tag(orb: float) -> str:
    return "orb" + str(orb).replace(".", "")


FROZEN_DAILY_COLUMNS = (
    [f"DK_sq_count_{_orb_tag(o)}" for o in FROZEN_ORB_THRESHOLDS_DEG]
    + [f"FT_sq_count_{_orb_tag(o)}" for o in FROZEN_ORB_THRESHOLDS_DEG]
    + [f"INC_sq_count_{_orb_tag(o)}" for o in FROZEN_ORB_THRESHOLDS_DEG]
    + [f"tight_aspect_count_{_orb_tag(o)}" for o in FROZEN_ORB_THRESHOLDS_DEG]
)


def label_strata(df: pd.DataFrame, earnings_sessions: set[str]) -> pd.DataFrame:
    out = df.copy()
    out["stratum"] = "ordinary"
    out.loc[out["session"].isin(earnings_sessions), "stratum"] = "earnings_reaction"
    abs_roll = out["abs_r_cc_pct"].rolling(20, min_periods=10).median()
    out["high_vol_day"] = out["abs_r_cc_pct"] > abs_roll
    out.loc[out["high_vol_day"], "stratum"] = out.loc[out["high_vol_day"], "stratum"].where(
        out["stratum"] != "earnings_reaction", "earnings_reaction"
    )
    return out


def stratum_correlations(df: pd.DataFrame, target: str = "r_cc_pct") -> pd.DataFrame:
    rows = []
    for stratum, grp in df.groupby("stratum"):
        for col in FROZEN_DAILY_COLUMNS:
            if col not in grp.columns or grp[col].nunique() <= 1:
                continue
            rows.append(
                {
                    "stratum": stratum,
                    "feature": col,
                    "target": target,
                    "n": len(grp),
                    "pearson_r": float(grp[col].corr(grp[target])),
                }
            )
    return pd.DataFrame(rows).sort_values(["stratum", "feature"])


def chronological_split_correlation(
    df: pd.DataFrame,
    *,
    feature: str,
    target: str = "r_cc_pct",
    train_frac: float = 0.7,
    embargo_sessions: int = FORWARD_EMBARGO_SESSIONS,
) -> dict:
    d = df.sort_values("session").reset_index(drop=True)
    n = len(d)
    cut = int(n * train_frac)
    train = d.iloc[:cut]
    test_start = cut + embargo_sessions
    if test_start >= n:
        return {"error": "insufficient test after embargo", "n": n}
    test = d.iloc[test_start:]
    r_train = float(train[feature].corr(train[target]))
    r_test = float(test[feature].corr(test[target])) if test[feature].nunique() > 1 else float("nan")
    return {
        "feature": feature,
        "target": target,
        "n_train": len(train),
        "n_test": len(test),
        "embargo_sessions": embargo_sessions,
        "corr_train": r_train,
        "corr_test": r_test,
    }


def circular_shift_permutation(
    df: pd.DataFrame,
    feature: str,
    *,
    target: str = "r_cc_pct",
    n_perm: int = 1999,
    seed: int = 42,
) -> dict:
    """Block-style null: circularly shift target series (preserves autocorrelation)."""
    rng = np.random.default_rng(seed)
    y = df.sort_values("session")[target].to_numpy(dtype=float)
    x = df.sort_values("session")[feature].to_numpy(dtype=float)
    obs = float(np.corrcoef(x, y)[0, 1])
    n = len(y)
    count = 0
    for _ in range(n_perm):
        k = int(rng.integers(1, n))
        yp = np.roll(y, k)
        rp = float(np.corrcoef(x, yp)[0, 1])
        if abs(rp) >= abs(obs):
            count += 1
    return {
        "feature": feature,
        "target": target,
        "observed_r": obs,
        "null": "circular_shift",
        "p_two_sided": (count + 1) / (n_perm + 1),
        "n_perm": n_perm,
    }


def max_stat_search_permutation(
    df: pd.DataFrame,
    features: list[str],
    *,
    target: str = "r_cc_pct",
    n_perm: int = 999,
    seed: int = 42,
) -> dict:
    """
    Multiple-testing-aware null: under label shuffle, max |r| across frozen features.
    Compare to observed max |r| (same feature set).
    """
    rng = np.random.default_rng(seed)
    d = df.sort_values("session").reset_index(drop=True)
    y = d[target].to_numpy(dtype=float)
    obs_stats = []
    for col in features:
        if col not in d.columns:
            continue
        x = d[col].to_numpy(dtype=float)
        obs_stats.append(abs(float(np.corrcoef(x, y)[0, 1])))
    obs_max = max(obs_stats) if obs_stats else float("nan")
    count = 0
    cols_present = [c for c in features if c in d.columns]
    xs = [d[c].to_numpy(dtype=float) for c in cols_present]
    for _ in range(n_perm):
        yp = rng.permutation(y)
        m = 0.0
        for x in xs:
            m = max(m, abs(float(np.corrcoef(x, yp)[0, 1])))
        if m >= obs_max:
            count += 1
    per_feature = {
        col: float(d[col].corr(d[target]))
        for col in cols_present
        if d[col].nunique() > 1
    }
    return {
        "observed_max_abs_r": obs_max,
        "per_feature_r": per_feature,
        "p_max_stat_shuffle": (count + 1) / (n_perm + 1),
        "n_features": len(cols_present),
        "n_perm": n_perm,
        "note": "Compares best |r| among frozen features to shuffle null (not full mining search).",
    }


def episode_adjusted_n(df: pd.DataFrame, episode_df: pd.DataFrame) -> dict:
    return {
        "n_trading_sessions": len(df),
        "n_slow_body_episodes_orb1": len(episode_df),
        "sessions_per_episode_mean": float(len(df) / len(episode_df)) if len(episode_df) else None,
    }
