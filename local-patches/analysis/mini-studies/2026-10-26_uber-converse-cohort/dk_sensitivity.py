"""DK birth-time sensitivity scaffold (not used for classification tuning)."""

from __future__ import annotations

from converse import utc_to_jd
from ephemeris import positions_at_jd
from radix import RADIX_COHORT

# Reference noon Tehran with documented +03:00; sweep ±2h without changing corporate charts.
DK_UT_HOURS = (7.0, 7.5, 8.0, 8.5, 9.0, 9.5, 10.0, 11.0)


def dk_birth_jd_variants() -> list[tuple[str, float]]:
    spec = RADIX_COHORT["DK"]
    out: list[tuple[str, float]] = []
    for hour in DK_UT_HOURS:
        jd = utc_to_jd(spec.year, spec.month, spec.day, int(hour), int((hour % 1) * 60), 0)
        label = f"UT_{hour:.1f}h"
        out.append((label, jd))
    return out


def slow_body_longitudes(jd_ut: float) -> dict[str, float]:
    pos = positions_at_jd(jd_ut)
    keep = ("Sun", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto")
    return {k: pos[k].longitude_deg for k in keep if k in pos}
