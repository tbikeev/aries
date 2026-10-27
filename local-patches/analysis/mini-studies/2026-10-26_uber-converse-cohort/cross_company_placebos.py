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
    n_surrogates: int = 200,
    seed: int = PLACEBO_SEED_DEFAULT,
) -> pd.DataFrame:
    """Per company: compare actual birth_jd sq-return r to random JD offsets."""
    rng = np.random.default_rng(seed)
    rows = []
    for ticker, grp in events.groupby("ticker"):
        real_jd = executive_jds.get(ticker)
        if real_jd is None or len(grp) < 5:
            continue
        y = grp["return_cc"]
        ejds = grp["event_jd_ut"].astype(float).tolist()
        xs = []
        for ej in ejds:
            xs.append(
                converse_count_features_for_birth_jd(real_jd, ej, orb_max=FROZEN_SQ_ORB_DEG)[
                    "sq_count"
                ]
            )
        x = pd.Series(xs, index=grp.index)
        obs_r = pearson(x, y)
        null = []
        for _ in range(n_surrogates):
            offset_days = int(rng.integers(-365 * 35, 365 * 35))
            sjd = real_jd + float(offset_days)
            xs_s = []
            for ej in ejds:
                xs_s.append(
                    converse_count_features_for_birth_jd(sjd, ej, orb_max=FROZEN_SQ_ORB_DEG)[
                        "sq_count"
                    ]
                )
            null.append(pearson(pd.Series(xs_s), y))
        null_arr = np.array([v for v in null if v == v])
        p = float((np.sum(np.abs(null_arr) >= abs(obs_r)) + 1) / (len(null_arr) + 1)) if len(null_arr) else float("nan")
        rows.append(
            {
                "ticker": ticker,
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
                "r_reassigned": pearson(pd.Series(xs), grp["return_cc"]),
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
                "r_genuine": pearson(pd.Series(xs_real), grp["return_cc"]),
                "r_misaligned": pearson(pd.Series(xs_shift), grp["return_cc"]),
            }
        )
    return pd.DataFrame(rows)
