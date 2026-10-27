"""Placebo radix tests for cross-company CEO squares."""

from __future__ import annotations

import numpy as np
import pandas as pd

from cross_company_paths import FROZEN_SQ_ORB_DEG, PLACEBO_SEED_DEFAULT
from earnings_converse import converse_count_features_for_birth_jd
from phase_h_stats import pearson


def random_radix_placebo_by_company(
    events: pd.DataFrame,
    executive_jds: dict[str, float],
    *,
    radix_kind: str | None = None,
    n_surrogates: int = 200,
    seed: int = PLACEBO_SEED_DEFAULT,
) -> pd.DataFrame:
    """Per company: compare actual birth_jd sq-return r to random JD offsets."""
    rng = np.random.default_rng(seed)
    frame = events
    if radix_kind is not None and "radix_kind" in events.columns:
        frame = events[events["radix_kind"] == radix_kind]
    rows = []
    for ticker, grp in frame.groupby("ticker"):
        key = ticker
        if radix_kind is not None:
            key = f"{ticker}|{radix_kind}"
        real_jd = executive_jds.get(key) or executive_jds.get(ticker)
        if real_jd is None or len(grp) < 5:
            continue
        y = grp["return_cc"].astype(float).reset_index(drop=True)
        ejds = grp["event_jd_ut"].astype(float).tolist()
        xs = [
            converse_count_features_for_birth_jd(real_jd, ej, orb_max=FROZEN_SQ_ORB_DEG)["sq_count"]
            for ej in ejds
        ]
        x = pd.Series(xs, dtype=float)
        obs_r = pearson(x, y)
        null = []
        for _ in range(n_surrogates):
            offset_days = float(rng.uniform(-365 * 35, 365 * 35))
            sjd = real_jd + offset_days
            xs_s = [
                converse_count_features_for_birth_jd(sjd, ej, orb_max=FROZEN_SQ_ORB_DEG)["sq_count"]
                for ej in ejds
            ]
            xs_series = pd.Series(xs_s, dtype=float)
            if xs_series.nunique() <= 1:
                continue
            rp = pearson(xs_series, y)
            if rp == rp:
                null.append(rp)
        null_arr = np.asarray(null, dtype=float)
        if obs_r != obs_r:
            p = float("nan")
        elif len(null_arr) == 0:
            p = float("nan")
        else:
            p = float((np.sum(np.abs(null_arr) >= abs(obs_r)) + 1) / (len(null_arr) + 1))
        rows.append(
            {
                "ticker": ticker,
                "radix_kind": radix_kind or grp["radix_kind"].iloc[0] if "radix_kind" in grp.columns else "CEO",
                "n_events": len(grp),
                "observed_r": obs_r,
                "null_median": float(np.median(null_arr)) if len(null_arr) else float("nan"),
                "empirical_p_two_sided": p,
                "n_surrogates": n_surrogates,
            }
        )
    return pd.DataFrame(rows)


def cross_company_radix_reassignment(
    events: pd.DataFrame,
    executive_jds: dict[str, float],
    *,
    seed: int = PLACEBO_SEED_DEFAULT,
) -> pd.DataFrame:
    """Permute executive radices across companies; one draw."""
    rng = np.random.default_rng(seed)
    tickers = sorted(events["ticker"].unique())
    perm = tickers.copy()
    rng.shuffle(perm)
    mapping = dict(zip(tickers, perm, strict=True))
    rows = []
    for ticker, grp in events.groupby("ticker"):
        donor = mapping[ticker]
        sjd = executive_jds[donor]
        real_jd = executive_jds[ticker]
        ejds = grp["event_jd_ut"].astype(float).tolist()
        xs = [
            converse_count_features_for_birth_jd(sjd, ej, orb_max=FROZEN_SQ_ORB_DEG)["sq_count"]
            for ej in ejds
        ]
        rows.append(
            {
                "ticker": ticker,
                "donor_ticker": donor,
                "r_reassigned": pearson(
                    pd.Series(xs, dtype=float), grp["return_cc"].astype(float).reset_index(drop=True)
                ),
            }
        )
    return pd.DataFrame(rows)


def calendar_misalignment(
    events: pd.DataFrame,
    executive_jds: dict[str, float],
    *,
    shift_days: int = 90,
) -> pd.DataFrame:
    """Shift event JD by fixed offset while keeping returns (Phase H style)."""
    day = 1.0
    rows = []
    for ticker, grp in events.groupby("ticker"):
        rjd = executive_jds[ticker]
        ejds_real = grp["event_jd_ut"].astype(float).tolist()
        xs_real = [
            converse_count_features_for_birth_jd(rjd, ej, orb_max=FROZEN_SQ_ORB_DEG)["sq_count"]
            for ej in ejds_real
        ]
        ejds_shift = [ej + shift_days * day for ej in ejds_real]
        xs_shift = [
            converse_count_features_for_birth_jd(rjd, ej, orb_max=FROZEN_SQ_ORB_DEG)["sq_count"]
            for ej in ejds_shift
        ]
        rows.append(
            {
                "ticker": ticker,
                "shift_days": shift_days,
                "r_genuine": pearson(
                    pd.Series(xs_real, dtype=float),
                    grp["return_cc"].astype(float).reset_index(drop=True),
                ),
                "r_misaligned": pearson(
                    pd.Series(xs_shift, dtype=float),
                    grp["return_cc"].astype(float).reset_index(drop=True),
                ),
            }
        )
    return pd.DataFrame(rows)
