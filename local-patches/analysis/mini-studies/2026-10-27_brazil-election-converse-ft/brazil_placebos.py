"""Date-shift, radix-shift, and random FT placebos for the election event."""

from __future__ import annotations

import numpy as np
import pandas as pd

from brazil_paths import PLACEBO_SEED
from converse_features import feature_vector, event_jd_from_local
from brazil_paths import EVENT_LOCAL, ORB_PRIMARY

DAY = 1.0
DATE_SHIFTS = (-180, -90, -30, 30, 90, 180)
RADIX_SHIFTS = (-180, -90, -30, 30, 90, 180)


def _hard_c2r_1deg(ft_jd: float, event_jd: float, ticker: str) -> float:
    fv = feature_vector(ticker, ft_jd, event_jd)
    return float(fv.get("c2r_hard_count_1deg", 0))


def run_placebos(
    ft_jds: dict[str, float],
    event_jd: float,
    *,
    n_random: int = 200,
    seed: int = PLACEBO_SEED,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    obs = {t: _hard_c2r_1deg(jd, event_jd, t) for t, jd in ft_jds.items()}
    obs_mean = float(np.mean(list(obs.values()))) if obs else float("nan")

    for shift in DATE_SHIFTS:
        ej = event_jd + shift * DAY
        vals = [_hard_c2r_1deg(jd, ej, t) for t, jd in ft_jds.items()]
        rows.append(
            {
                "placebo_type": "date_shift_days",
                "shift": shift,
                "mean_c2r_hard_1deg": float(np.mean(vals)),
                "observed_election_mean": obs_mean,
            }
        )

    for shift in RADIX_SHIFTS:
        vals = [_hard_c2r_1deg(jd + shift * DAY, event_jd, t) for t, jd in ft_jds.items()]
        rows.append(
            {
                "placebo_type": "radix_shift_days",
                "shift": shift,
                "mean_c2r_hard_1deg": float(np.mean(vals)),
                "observed_election_mean": obs_mean,
            }
        )

    null_means = []
    for i in range(n_random):
        surrogate = {}
        for t, real in ft_jds.items():
            offset = float(rng.uniform(-365 * 40, 365 * 40))
            surrogate[t] = real + offset
        vals = [_hard_c2r_1deg(surrogate[t], event_jd, t) for t in ft_jds]
        null_means.append(float(np.mean(vals)))
    null_arr = np.asarray(null_means)
    pct = float((np.sum(null_arr >= obs_mean) + 1) / (len(null_arr) + 1)) if len(null_arr) else float("nan")
    rows.append(
        {
            "placebo_type": "random_ft_jd",
            "shift": f"n={n_random}, seed={seed}",
            "mean_c2r_hard_1deg": float(np.median(null_arr)),
            "observed_election_mean": obs_mean,
            "empirical_p_ge_observed": pct,
        }
    )
    return pd.DataFrame(rows)
