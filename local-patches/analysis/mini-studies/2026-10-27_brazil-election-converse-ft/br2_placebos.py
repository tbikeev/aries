"""BR-2 placebos targeting episode-level mean C2C hard vs EWZ return correlation."""

from __future__ import annotations

import numpy as np
import pandas as pd

from brazil_paths import BR2_PLACEBO_SEED, UBER_STUDY
from br2_analysis import _episode_aggregates, _ewz_market_col
from br2_features import frozen_feature_bundle
from brazil_historical import trading_session_jd
from datetime import date

import sys

sys.path.insert(0, str(UBER_STUDY))
from phase_h_stats import pearson  # noqa: E402

DAY = 1.0


def _primary_stat(panel: pd.DataFrame) -> float:
    ep = _episode_aggregates(panel[panel["validation_eligible"] & ~panel["discovery_only"]], validation_only=False)
    if len(ep) < 3:
        return float("nan")
    ycol = _ewz_market_col(ep)
    return pearson(ep["mean_c2c_hard"].astype(float), ep[ycol].astype(float))


def run_placebos(panel: pd.DataFrame, ft_jds: dict[str, float], *, n_random: int = 200, n_surrogates: int | None = None) -> pd.DataFrame:
    n_random = n_surrogates or n_random
    rng = np.random.default_rng(BR2_PLACEBO_SEED)
    obs = _primary_stat(panel)
    rows = [{"placebo_type": "genuine", "shift": "0", "primary_pearson_r": obs}]

    # Date shifts on events (recompute features)
    for shift in (-180, -90, -30, 30, 90, 180):
        shifted = _recompute_panel_features(panel, ft_jds, day_offset=shift, rng=None)
        rows.append(
            {
                "placebo_type": "event_date_shift_days",
                "shift": shift,
                "primary_pearson_r": _primary_stat(shifted),
            }
        )

    # Random FT
    null = []
    tickers = sorted(ft_jds.keys())
    for _ in range(n_random):
        sur = {}
        for t in tickers:
            sur[t] = ft_jds[t] + float(rng.uniform(-365 * 40, 365 * 40))
        sh = _recompute_panel_features(panel, sur, day_offset=0, rng=None)
        r = _primary_stat(sh)
        if r == r:
            null.append(r)
    null_arr = np.asarray(null)
    p = float((np.sum(np.abs(null_arr) >= abs(obs)) + 1) / (len(null_arr) + 1)) if len(null_arr) else float("nan")
    rows.append(
        {
            "placebo_type": "random_ft_jd",
            "shift": f"n={n_random}",
            "primary_pearson_r": float(np.median(null_arr)) if len(null_arr) else float("nan"),
            "empirical_p_two_sided_vs_genuine": p,
            "genuine_r": obs,
        }
    )

    # Cross-company reassignment (one draw)
    perm = tickers.copy()
    rng.shuffle(perm)
    mapping = dict(zip(tickers, perm, strict=True))
    reassigned = {t: ft_jds[mapping[t]] for t in tickers}
    rows.append(
        {
            "placebo_type": "cross_company_ft_reassignment",
            "shift": "seed",
            "primary_pearson_r": _primary_stat(_recompute_panel_features(panel, reassigned, 0, None)),
        }
    )

    # Circular shift of EWZ returns among validation episodes
    shuffled = panel.copy()
    val_dates = sorted(shuffled[shuffled["validation_eligible"]]["event_date"].unique())
    ycol = _ewz_market_col(shuffled)
    rets = [shuffled.loc[shuffled["event_date"] == d, ycol].iloc[0] for d in val_dates]
    rets_shift = rets[1:] + rets[:1]
    mapping_r = dict(zip(val_dates, rets_shift, strict=True))
    for d, r in mapping_r.items():
        shuffled.loc[shuffled["event_date"] == d, ycol] = r
        if ycol != "ewz_return_cc_pct":
            shuffled.loc[shuffled["event_date"] == d, "ewz_return_adj_pct"] = r
        shuffled.loc[shuffled["event_date"] == d, "return_abnormal_pp"] = (
            shuffled.loc[shuffled["event_date"] == d, "company_return_cc_pct"] - r
        )
    rows.append(
        {
            "placebo_type": "circular_ewz_return_shift",
            "shift": "1",
            "primary_pearson_r": _primary_stat(shuffled),
        }
    )
    return pd.DataFrame(rows)


def _recompute_panel_features(
    panel: pd.DataFrame,
    ft_jds: dict[str, float],
    day_offset: float,
    rng,
) -> pd.DataFrame:
    out = panel.copy()
    for i, row in out.iterrows():
        t = row["ticker"]
        if t not in ft_jds:
            continue
        ed = date.fromisoformat(row["event_date"])
        ejd = trading_session_jd(ed) + day_offset * DAY
        f = frozen_feature_bundle(ft_jds[t], ejd, use_cache=True)
        for k in ("c2c_hard_count", "c2c_sq_opp_count", "c2r_hard_count", "c2c_sq_count"):
            if k in f:
                out.at[i, k] = f[k]
    return out
