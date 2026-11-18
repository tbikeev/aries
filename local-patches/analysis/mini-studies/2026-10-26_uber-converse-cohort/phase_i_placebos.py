"""Declination placebo controls (Phase I-F)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from converse import mirrored_jd
from declination_geometry import classify_declination_pair, orb_within
from ephemeris import iter_benchmark_names, positions_at_jd
from phase_i_paths import DECL_ORB_PRIMARY, PLACEBO_SEED_DEFAULT, PLACEBO_SURROGATES_DEFAULT
from phase_h_stats import pearson
from radix import RADIX_COHORT


def dk_decl_features_for_birth_jd(birth_jd: float, event_jd: float, *, orb: float) -> dict:
    cjd = mirrored_jd(birth_jd, event_jd)
    conv = positions_at_jd(cjd, include_optional=False)
    rad = positions_at_jd(birth_jd, include_optional=False)
    bodies = list(iter_benchmark_names())
    par = cpar = total = 0
    double = 0
    for a in bodies:
        d1 = conv[a].declination_deg
        for b in bodies:
            d2 = rad[b].declination_deg
            for kind, orb_val in classify_declination_pair(d1, d2):
                if orb_within(orb_val, orb):
                    total += 1
                    if kind == "par":
                        par += 1
                    else:
                        cpar += 1
    return {"par": par, "cpar": cpar, "total": total}


def placebo_declination_correlations(
    events: list[tuple[str, float]],
    returns: pd.Series,
    *,
    n_surrogates: int = PLACEBO_SURROGATES_DEFAULT,
    seed: int = PLACEBO_SEED_DEFAULT,
) -> dict:
    rng = np.random.default_rng(seed)
    real_jd = RADIX_COHORT["DK"].birth_jd
    real_rows = []
    for rd, ejd in events:
        c = dk_decl_features_for_birth_jd(real_jd, ejd, orb=DECL_ORB_PRIMARY)
        c["report_date"] = rd
        real_rows.append(c)
    real_df = pd.DataFrame(real_rows)
    y = returns.loc[real_df["report_date"]].to_numpy(float)
    obs_par = pearson(real_df["par"], pd.Series(y))
    obs_total = pearson(real_df["total"], pd.Series(y))

    null_par = []
    null_total = []
    span = 365.25 * 40
    for i in range(n_surrogates):
        if i and i % 200 == 0:
            print(f"decl placebo {i}/{n_surrogates}", flush=True)
        bjd = real_jd + float(rng.uniform(-span, span))
        rows = []
        for rd, ejd in events:
            rows.append(dk_decl_features_for_birth_jd(bjd, ejd, orb=DECL_ORB_PRIMARY))
        df = pd.DataFrame(rows)
        null_par.append(pearson(df["par"], pd.Series(y)))
        null_total.append(pearson(df["total"], pd.Series(y)))

    def pack(null, obs):
        arr = np.array(null)
        return {
            "observed_r": obs,
            "null_median": float(np.median(arr)),
            "empirical_p_two_sided": float(np.mean(np.abs(arr) >= abs(obs))),
        }

    return {
        "DK_par_orb05": pack(null_par, obs_par),
        "DK_decl_total_orb05": pack(null_total, obs_total),
        "n_surrogates": n_surrogates,
        "seed": seed,
    }
