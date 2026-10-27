"""Converse transits for earnings reaction timestamps."""

from __future__ import annotations

from datetime import datetime

from aspects import ORB_THRESHOLDS, full_directed_aspect_matrix, orb_for_named_aspect
from cohort import COHORT_PAIRS, build_cohort_registry
from converse import jd_to_utc_tuple, mirrored_jd, utc_to_jd
from ephemeris import iter_benchmark_names, positions_at_jd
from radix import RADIX_COHORT

ORB_LABELS = ("le_15arcmin", "le_30arcmin", "le_1deg", "le_2deg")
ORB_LIMITS = (0.25, 0.5, 1.0, 2.0)


def event_jd_from_datetime(dt: datetime) -> float:
    return utc_to_jd(
        dt.year,
        dt.month,
        dt.day,
        dt.hour,
        dt.minute,
        dt.second,
    )


def converse_utc_for_event(radix_key: str, event_jd: float) -> tuple[int, int, int, int, int, int]:
    birth_jd = RADIX_COHORT[radix_key].birth_jd
    return jd_to_utc_tuple(mirrored_jd(birth_jd, event_jd))


def extract_converse_features(
    radix_key: str,
    event_jd: float,
    *,
    report_date: str,
    reaction_session: str,
) -> dict:
    r = RADIX_COHORT[radix_key]
    cjd = mirrored_jd(r.birth_jd, event_jd)
    conv = positions_at_jd(cjd, include_optional=False)
    rad = positions_at_jd(r.birth_jd, include_optional=False)
    conv_lon = {k: p.longitude_deg for k, p in conv.items()}
    rad_lon = {k: p.longitude_deg for k, p in rad.items()}
    conv_decl = {k: p.declination_deg for k, p in conv.items()}
    rad_decl = {k: p.declination_deg for k, p in rad.items()}
    bodies = list(iter_benchmark_names())

    matrix = full_directed_aspect_matrix(conv_lon, rad_lon, body_names=bodies)
    aspect_rows = []
    for row in matrix:
        best = row["best_aspect"]
        best_orb = row["best_orb"]
        buckets = {}
        for label, limit in zip(ORB_LABELS, ORB_LIMITS, strict=True):
            buckets[label] = best_orb <= limit + 1e-12
        aspect_rows.append(
            {
                "report_date": report_date,
                "reaction_session": reaction_session,
                "radix_key": radix_key,
                "converse_jd_ut": cjd,
                "from_body": row["from_body"],
                "to_body": row["to_body"],
                "best_aspect": best,
                "best_orb": best_orb,
                **buckets,
            }
        )

    decl_rows = []
    for a in bodies:
        for b in bodies:
            d1, d2 = conv_decl[a], rad_decl[b]
            par = abs(d1 - d2)
            cpar = abs(d1 + d2)
            decl_rows.append(
                {
                    "report_date": report_date,
                    "reaction_session": reaction_session,
                    "radix_key": radix_key,
                    "conv_body": a,
                    "radix_body": b,
                    "par_delta_deg": par,
                    "cpar_delta_deg": cpar,
                    "par_le_1deg": par <= 1.0,
                    "cpar_le_1deg": cpar <= 1.0,
                }
            )

    return {
        "aspect_rows": aspect_rows,
        "decl_rows": decl_rows,
        "converse_jd": cjd,
        "converse_utc": converse_utc_for_event(radix_key, event_jd),
    }


def converse_count_features_for_birth_jd(birth_jd: float, event_jd: float, *, orb_max: float) -> dict[str, int]:
    """Directed-aspect counts for arbitrary radix JD (placebo cohorts)."""
    cjd = mirrored_jd(birth_jd, event_jd)
    conv = positions_at_jd(cjd, include_optional=False)
    rad = positions_at_jd(birth_jd, include_optional=False)
    conv_lon = {k: p.longitude_deg for k, p in conv.items()}
    rad_lon = {k: p.longitude_deg for k, p in rad.items()}
    matrix = full_directed_aspect_matrix(conv_lon, rad_lon, body_names=list(iter_benchmark_names()))
    tight = [row for row in matrix if row["best_orb"] <= orb_max + 1e-12]
    counts = {
        "tight_aspect_count": len(tight),
        "conj_count": 0,
        "sq_count": 0,
        "sext_count": 0,
        "tri_count": 0,
        "opp_count": 0,
    }
    for row in tight:
        asp = row["best_aspect"]
        key = f"{asp}_count"
        if key in counts:
            counts[key] += 1
    return counts


def converse_count_features(radix_key: str, event_jd: float, *, orb_max: float) -> dict[str, int]:
    """Lightweight directed-aspect counts for daily panel (no full row export)."""
    r = RADIX_COHORT[radix_key]
    return converse_count_features_for_birth_jd(r.birth_jd, event_jd, orb_max=orb_max)


def slow_body_active_signatures(
    radix_key: str, event_jd: float, *, orb_max: float
) -> list[tuple[str, float]]:
    """Active ≤orb directed pairs where converse body is outer (for episode tracking)."""
    from temporal_persistence import SLOW_CONVERS_BODIES

    r = RADIX_COHORT[radix_key]
    cjd = mirrored_jd(r.birth_jd, event_jd)
    conv = positions_at_jd(cjd, include_optional=False)
    rad = positions_at_jd(r.birth_jd, include_optional=False)
    conv_lon = {k: p.longitude_deg for k, p in conv.items()}
    rad_lon = {k: p.longitude_deg for k, p in rad.items()}
    matrix = full_directed_aspect_matrix(conv_lon, rad_lon, body_names=list(iter_benchmark_names()))
    out: list[tuple[str, float]] = []
    for row in matrix:
        if row["best_orb"] > orb_max + 1e-12:
            continue
        body = row["from_body"].removeprefix("conv:")
        if body not in SLOW_CONVERS_BODIES:
            continue
        sig = f"{radix_key}|{row['from_body']}|{row['to_body']}|{row['best_aspect']}"
        out.append((sig, float(row["best_orb"])))
    return out


def registry_snapshot() -> list[dict]:
    """Static inter-radix registry for activation matching."""
    blocks = build_cohort_registry()
    rows: list[dict] = []
    for block in blocks:
        for asp in block.longitude_aspects:
            if asp.orb_deg <= 2.0:
                rows.append(
                    {
                        "pair": f"{block.left}-{block.right}",
                        "kind": "longitude",
                        "body_a": asp.body_a,
                        "body_b": asp.body_b,
                        "aspect": asp.aspect,
                        "orb_deg": asp.orb_deg,
                    }
                )
    return rows
