"""Tests A/B/C, placebos, walk-forward for BR-2."""

from __future__ import annotations

import numpy as np
import pandas as pd

from brazil_paths import BR2_PLACEBO_SEED, DISCOVERY_EVENT_DATE, UBER_STUDY
from br2_panel import STABLE_SUBUNIVERSE

import sys

sys.path.insert(0, str(UBER_STUDY))
from phase_h_stats import pearson, spearman  # noqa: E402


def _ewz_market_col(df: pd.DataFrame) -> str:
    if "ewz_return_adj_pct" in df.columns and df["ewz_return_adj_pct"].notna().any():
        return "ewz_return_adj_pct"
    return "ewz_return_cc_pct"


def _episode_aggregates(panel: pd.DataFrame, *, validation_only: bool = True) -> pd.DataFrame:
    p = panel.copy()
    if validation_only:
        p = p[p["validation_eligible"] & ~p["discovery_only"]]
    rows = []
    for (ed, eid), grp in p.groupby(["event_date", "episode_id"]):
        rows.append(
            {
                "event_date": ed,
                "episode_id": eid,
                "ewz_return_adj_pct": grp["ewz_return_adj_pct"].iloc[0]
                if "ewz_return_adj_pct" in grp
                else grp["ewz_return_cc_pct"].iloc[0],
                "ewz_return_cc_pct": grp["ewz_return_cc_pct"].iloc[0],
                "n_tickers": len(grp),
                "mean_c2c_hard": grp["c2c_hard_count"].mean(),
                "median_c2c_hard": grp["c2c_hard_count"].median(),
                "mean_c2c_sq_opp": grp["c2c_sq_opp_count"].mean(),
                "frac_c2c_sq_opp_ge1": float((grp["c2c_sq_opp_count"] >= 1).mean()),
                "mean_c2r_hard": grp["c2r_hard_count"].mean(),
                "mean_pct_c2c_hard": grp.get("pct_c2c_hard", pd.Series(dtype=float)).mean()
                if "pct_c2c_hard" in grp
                else float("nan"),
            }
        )
    return pd.DataFrame(rows)


def market_direction_results(panel: pd.DataFrame, pct: pd.DataFrame | None = None) -> pd.DataFrame:
    if pct is not None and not pct.empty:
        panel = panel.merge(
            pct[["ticker", "event_date", "pct_c2c_hard", "pct_c2r_hard"]],
            on=["ticker", "event_date"],
            how="left",
        )
    ep = _episode_aggregates(panel, validation_only=False)
    val = _episode_aggregates(panel, validation_only=True)
    rows = []

    def block(df, label):
        if len(df) < 3:
            return
        ycol = _ewz_market_col(df)
        y = df[ycol].astype(float)
        for feat, col in (
            ("mean_c2c_hard", "mean_c2c_hard"),
            ("mean_c2c_sq_opp", "mean_c2c_sq_opp"),
            ("mean_c2r_hard", "mean_c2r_hard"),
        ):
            x = df[col].astype(float)
            rows.append(
                {
                    "sample": label,
                    "feature": feat,
                    "pearson_r": pearson(x, y),
                    "spearman_rho": spearman(x, y),
                    "n_episodes": len(df),
                }
            )
        crashes = df[df[ycol] < 0]
        rallies = df[df[ycol] > 0]
        if len(crashes) and len(rallies):
            rows.append(
                {
                    "sample": label,
                    "feature": "mean_c2c_hard_crash_vs_rally",
                    "pearson_r": float(crashes["mean_c2c_hard"].mean() - rallies["mean_c2c_hard"].mean()),
                    "spearman_rho": float("nan"),
                    "n_episodes": len(df),
                    "crash_mean": float(crashes["mean_c2c_hard"].mean()),
                    "rally_mean": float(rallies["mean_c2c_hard"].mean()),
                }
            )

    block(ep, "all_episodes_including_discovery")
    block(val, "validation_excl_2026_10_26")
    # LOO on validation episodes
    for drop in val["event_date"].unique():
        sub = val[val["event_date"] != drop]
        if len(sub) < 3:
            continue
        x = sub["mean_c2c_hard"].astype(float)
        y = sub[_ewz_market_col(sub)].astype(float)
        rows.append(
            {
                "sample": "loo_validation",
                "feature": f"mean_c2c_hard_drop_{drop}",
                "pearson_r": pearson(x, y),
                "spearman_rho": spearman(x, y),
                "n_episodes": len(sub),
            }
        )
    # Bootstrap
    rng = np.random.default_rng(BR2_PLACEBO_SEED)
    xs = val["mean_c2c_hard"].astype(float).to_numpy()
    ys = val[_ewz_market_col(val)].astype(float).to_numpy()
    boots = []
    for _ in range(400):
        idx = rng.integers(0, len(xs), size=len(xs))
        if np.std(xs[idx]) < 1e-12:
            continue
        boots.append(float(np.corrcoef(xs[idx], ys[idx])[0, 1]))
    if boots:
        rows.append(
            {
                "sample": "validation_excl_2026_10_26",
                "feature": "mean_c2c_hard_bootstrap_ci",
                "pearson_r": float(np.median(boots)),
                "spearman_rho": float(np.quantile(boots, 0.025)),
                "n_episodes": len(val),
                "bootstrap_hi": float(np.quantile(boots, 0.975)),
            }
        )
    return pd.DataFrame(rows)


def cross_sectional_abnormal_results(panel: pd.DataFrame) -> pd.DataFrame:
    val = panel[panel["validation_eligible"] & ~panel["discovery_only"]]
    per_event = []
    for ed, grp in val.groupby("event_date"):
        x = grp["c2c_sq_opp_count"].astype(float)
        y = grp["return_abnormal_pp"].astype(float)
        per_event.append(
            {
                "event_date": ed,
                "spearman_abnormal_vs_c2c_sq_opp": spearman(x, y),
                "pearson_abnormal_vs_c2c_sq_opp": pearson(x, y),
                "n_tickers": len(grp),
            }
        )
    return pd.DataFrame(per_event)


def cross_section_summary(df: pd.DataFrame) -> dict:
    if df.empty:
        return {}
    return {
        "median_spearman_across_episodes": float(df["spearman_abnormal_vs_c2c_sq_opp"].median()),
        "n_negative_assoc": int((df["spearman_abnormal_vs_c2c_sq_opp"] < 0).sum()),
        "n_positive_assoc": int((df["spearman_abnormal_vs_c2c_sq_opp"] > 0).sum()),
        "n_episodes": len(df),
    }


def c2c_vs_c2r_comparison(panel: pd.DataFrame) -> pd.DataFrame:
    val = panel[panel["validation_eligible"] & ~panel["discovery_only"]]
    ep = _episode_aggregates(val, validation_only=False)
    y = ep[_ewz_market_col(ep)].astype(float)
    rows = []
    for name, col in (("c2c_hard", "mean_c2c_hard"), ("c2r_hard", "mean_c2r_hard")):
        x = ep[col].astype(float)
        rows.append({"model": name, "pearson_r": pearson(x, y), "spearman_rho": spearman(x, y), "n": len(ep)})
    # Combined: simple average of standardized features
    if len(ep) >= 3:
        zc = (ep["mean_c2c_hard"] - ep["mean_c2c_hard"].mean()) / (ep["mean_c2c_hard"].std() + 1e-12)
        zr = (ep["mean_c2r_hard"] - ep["mean_c2r_hard"].mean()) / (ep["mean_c2r_hard"].std() + 1e-12)
        comb = zc + zr
        rows.append(
            {
                "model": "combined_z_c2c_plus_c2r",
                "pearson_r": pearson(comb, y),
                "spearman_rho": spearman(comb, y),
                "n": len(ep),
            }
        )
    return pd.DataFrame(rows)


def walk_forward_episode_results(panel: pd.DataFrame) -> pd.DataFrame:
    val = panel[panel["validation_eligible"] & ~panel["discovery_only"]]
    ep = _episode_aggregates(val, validation_only=False).sort_values("event_date")
    rows = []
    for k in range(5, len(ep)):
        train = ep.iloc[:k]
        test = ep.iloc[k : k + 1]
        xtr = train["mean_c2c_hard"].astype(float)
        ycol = _ewz_market_col(train)
        ytr = train[ycol].astype(float)
        r = pearson(xtr, ytr)
        pred_sign = -1 if r < 0 else 1
        actual = float(test[ycol].iloc[0])
        rows.append(
            {
                "test_event_date": test["event_date"].iloc[0],
                "train_n_episodes": k,
                "train_pearson": r,
                "predicted_sign": pred_sign,
                "actual_sign": int(np.sign(actual)),
                "correct": int(np.sign(actual) == pred_sign),
            }
        )
    return pd.DataFrame(rows)


def episode_independent_subsample(panel: pd.DataFrame) -> pd.DataFrame:
    """One row per episode (worst EWZ day in cluster) for independence check."""
    val = panel[panel["validation_eligible"] & ~panel["discovery_only"]]
    picks = []
    for _, grp in val.groupby("episode_id"):
        ycol = _ewz_market_col(grp)
        dates = grp.groupby("event_date")[ycol].first()
        picks.append(str(dates.idxmin()))
    sub = val[val["event_date"].isin(picks)]
    ep = _episode_aggregates(sub, validation_only=False)
    y = ep[_ewz_market_col(ep)].astype(float)
    x = ep["mean_c2c_hard"].astype(float)
    return pd.DataFrame(
        [
            {
                "sample": "one_day_per_episode_min_ewz",
                "pearson_r": pearson(x, y),
                "spearman_rho": spearman(x, y),
                "n_episodes": len(ep),
            }
        ]
    )
