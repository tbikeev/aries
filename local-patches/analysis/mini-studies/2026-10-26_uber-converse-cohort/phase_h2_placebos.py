"""H2: genuine cohort vs shifted radix, random surrogates, event misalignment."""

from __future__ import annotations

import numpy as np
import pandas as pd

from converse import mirrored_jd
from earnings_converse import converse_count_features_for_birth_jd
from phase_h_data import event_jd_series
from phase_h_paths import PLACEBO_SEED, PLACEBO_SURROGATE_COUNT, SHIFT_OFFSETS_DAYS
from phase_h_stats import pearson
from radix import RADIX_COHORT

FROZEN_METRICS = (
    ("DK_sq_count_orb10", "DK", 1.0),
    ("FT_sq_count_orb10", "FT", 1.0),
    ("INC_sq_count_orb10", "INC", 1.0),
    ("tight_aspect_count_orb10", "ALL", 1.0),
)


def _counts_for_cohort_set(
    birth_jds: dict[str, float],
    events: list[tuple[str, float]],
    orb: float,
) -> pd.DataFrame:
    rows = []
    for rd, ejd in events:
        tight = 0
        row = {"report_date": rd}
        for key in ("FT", "INC", "DK"):
            c = converse_count_features_for_birth_jd(birth_jds[key], ejd, orb_max=orb)
            row[f"{key}_sq_count_orb10"] = c["sq_count"]
            tight += c["tight_aspect_count"]
        row["tight_aspect_count_orb10"] = tight
        rows.append(row)
    return pd.DataFrame(rows)


def _metric_corr(feat_df: pd.DataFrame, returns: pd.Series, col: str) -> float:
    ret = returns.reset_index()
    ret.columns = ["report_date", "y"]
    m = feat_df.merge(ret, on="report_date", how="inner")
    return pearson(m[col], m["y"])


def run_shifted_radix_placebos(
    df: pd.DataFrame,
    events: list[tuple[str, float]],
) -> pd.DataFrame:
    """Design A: ±offset days on each radix JD (converse shifts by 2Δ at fixed event)."""
    returns = df.set_index("report_date", drop=False)["r_cc_pct"]
    real_jds = {k: RADIX_COHORT[k].birth_jd for k in ("FT", "INC", "DK")}
    real_feat = _counts_for_cohort_set(real_jds, events, 1.0)
    real = {
        "design": "genuine",
        "offset_days": 0,
        "direction": "real",
        "DK_sq_r": _metric_corr(real_feat, returns, "DK_sq_count_orb10"),
        "FT_sq_r": _metric_corr(real_feat, returns, "FT_sq_count_orb10"),
        "INC_sq_r": _metric_corr(real_feat, returns, "INC_sq_count_orb10"),
        "tight_r": _metric_corr(real_feat, returns, "tight_aspect_count_orb10"),
    }
    rows = [real]
    for days in SHIFT_OFFSETS_DAYS:
        for sign in (-1, 1):
            delta = sign * days
            shifted = {k: real_jds[k] + delta for k in real_jds}
            feat = _counts_for_cohort_set(shifted, events, 1.0)
            rows.append(
                {
                    "design": "shifted_radix",
                    "offset_days": delta,
                    "direction": f"{sign:+d}",
                    "DK_sq_r": _metric_corr(feat, returns, "DK_sq_count_orb10"),
                    "FT_sq_r": _metric_corr(feat, returns, "FT_sq_count_orb10"),
                    "INC_sq_r": _metric_corr(feat, returns, "INC_sq_count_orb10"),
                    "tight_r": _metric_corr(feat, returns, "tight_aspect_count_orb10"),
                    "converse_shift_note": f"converse JD moves {2 * delta:+g} days vs genuine at same event",
                }
            )
    return pd.DataFrame(rows)


def run_random_surrogate_placebos(
    df: pd.DataFrame,
    events: list[tuple[str, float]],
    *,
    n_surrogates: int = PLACEBO_SURROGATE_COUNT,
    seed: int = PLACEBO_SEED,
) -> tuple[pd.DataFrame, dict]:
    """Design B: independent random radix JD offsets + joint equal shifts."""
    rng = np.random.default_rng(seed)
    returns = df.set_index("report_date", drop=False)["r_cc_pct"]
    real_jds = {k: RADIX_COHORT[k].birth_jd for k in ("FT", "INC", "DK")}
    real_feat = _counts_for_cohort_set(real_jds, events, 1.0)
    real_dk = _metric_corr(real_feat, returns, "DK_sq_count_orb10")
    real_tight = _metric_corr(real_feat, returns, "tight_aspect_count_orb10")

    indep_dk: list[float] = []
    indep_tight: list[float] = []
    joint_dk: list[float] = []
    joint_tight: list[float] = []

    base_span = 365.25 * 40  # ~40y JD window for offsets
    for i in range(n_surrogates):
        if i and i % 100 == 0:
            print(f"placebo surrogates: {i}/{n_surrogates}", flush=True)
        ind = {
            k: real_jds[k] + float(rng.uniform(-base_span, base_span)) for k in real_jds
        }
        feat_i = _counts_for_cohort_set(ind, events, 1.0)
        indep_dk.append(_metric_corr(feat_i, returns, "DK_sq_count_orb10"))
        indep_tight.append(_metric_corr(feat_i, returns, "tight_aspect_count_orb10"))
        joint_delta = float(rng.uniform(-base_span, base_span))
        joint = {k: real_jds[k] + joint_delta for k in real_jds}
        feat_j = _counts_for_cohort_set(joint, events, 1.0)
        joint_dk.append(_metric_corr(feat_j, returns, "DK_sq_count_orb10"))
        joint_tight.append(_metric_corr(feat_j, returns, "tight_aspect_count_orb10"))

    def rank_summary(null: list[float], obs: float) -> dict:
        arr = np.array(null, dtype=float)
        return {
            "observed_r": obs,
            "null_median": float(np.median(arr)),
            "null_p05": float(np.quantile(arr, 0.05)),
            "null_p95": float(np.quantile(arr, 0.95)),
            "empirical_p_two_sided": float(np.mean(np.abs(arr) >= abs(obs))),
            "rank_percentile": float(np.mean(arr <= obs)),
        }

    summary = {
        "independent_random_radix_DK_sq": rank_summary(indep_dk, real_dk),
        "independent_random_radix_tight": rank_summary(indep_tight, real_tight),
        "joint_shift_DK_sq": rank_summary(joint_dk, real_dk),
        "joint_shift_tight": rank_summary(joint_tight, real_tight),
        "n_surrogates": n_surrogates,
        "seed": seed,
    }
    long_rows = []
    for i, v in enumerate(indep_dk):
        long_rows.append({"family": "independent", "surrogate_id": i, "DK_sq_r": v, "tight_r": indep_tight[i]})
    for i, v in enumerate(joint_dk):
        long_rows.append({"family": "joint_shift", "surrogate_id": i, "DK_sq_r": v, "tight_r": joint_tight[i]})
    return pd.DataFrame(long_rows), summary


def run_event_alignment_placebos(
    df: pd.DataFrame,
    events: list[tuple[str, float]],
) -> tuple[pd.DataFrame, dict]:
    """Design C: circular return reassignment; misaligned event JD (+90d) with true returns."""
    returns = df.set_index("report_date", drop=False)["r_cc_pct"]
    real_jds = {k: RADIX_COHORT[k].birth_jd for k in ("FT", "INC", "DK")}
    feat_real = _counts_for_cohort_set(real_jds, events, 1.0)
    x = feat_real.set_index("report_date")["DK_sq_count_orb10"]
    y = returns

    # Circular shift of returns (preserve dependence structure).
    circ_rs = []
    yv = y.loc[x.index].to_numpy()
    xv = x.to_numpy()
    obs = float(np.corrcoef(xv, yv)[0, 1])
    rng = np.random.default_rng(PLACEBO_SEED)
    for _ in range(1999):
        k = int(rng.integers(1, len(yv)))
        yp = np.roll(yv, k)
        circ_rs.append(float(np.corrcoef(xv, yp)[0, 1]))
    circ = {
        "observed_r": obs,
        "null_median": float(np.median(circ_rs)),
        "empirical_p_two_sided": float(np.mean(np.abs(circ_rs) >= abs(obs))),
        "null": "circular_shift_returns",
    }

    # Misaligned event times (+90 calendar days on JD) while keeping returns on report_date.
    misaligned_events = [(rd, ejd + 90.0) for rd, ejd in events]
    feat_mis = _counts_for_cohort_set(real_jds, misaligned_events, 1.0)
    mis_r = _metric_corr(feat_mis, returns, "DK_sq_count_orb10")

    rows = pd.DataFrame(
        [
            {"control": "genuine_alignment", "DK_sq_r": obs},
            {"control": "event_jd_plus_90d_misaligned", "DK_sq_r": mis_r},
        ]
    )
    return rows, {"circular_return_shift": circ, "misaligned_event_jd_90d": mis_r}
