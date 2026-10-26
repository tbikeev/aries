"""Phase A: static inter-radix cohort registry (FT–INC, FT–DK, INC–DK)."""

from __future__ import annotations

from dataclasses import dataclass

from aspects import DeclinationContact, LongitudeAspect, cross_aspects, declination_contacts
from ephemeris import iter_benchmark_names, positions_at_jd
from radix import RADIX_COHORT

COHORT_PAIRS = (("FT", "INC"), ("FT", "DK"), ("INC", "DK"))

# Researcher-supplied permanent registry (must be recovered by analysis).
EXPECTED_LONGITUDE = [
    ("FT", "Uranus", "DK", "Saturn", "conj", 0.10),  # 0°06'
    ("INC", "Jupiter", "DK", "Mercury", "conj", 0.85),  # 0°51'
    ("FT", "Venus", "DK", "Venus", "conj", 1.27),  # 1°16'
    ("FT", "Jupiter", "DK", "Pluto", "sq", 0.58),  # 0°35'
]

EXPECTED_DECLINATION = [
    ("INC", "Jupiter", "DK", "Sun", "par", 0.05),
    ("FT", "Mercury", "INC", "Moon", "par", 0.08),
    ("FT", "Saturn", "INC", "Jupiter", "cpar", 0.10),
    ("INC", "Node", "DK", "Pluto", "cpar", 0.17),
    # Manual screenshot read — unverified; do not fail pipeline if absent (see README).
    # ("INC", "Mercury", "DK", "Neptune", "par", 0.32),
    ("FT", "Venus", "DK", "Venus", "par", 0.48),
    ("FT", "Mars", "DK", "Mars", "cpar", 0.57),
]


@dataclass
class CohortPairResult:
    left: str
    right: str
    longitude_aspects: list[LongitudeAspect]
    declination: list[DeclinationContact]


def build_cohort_registry() -> list[CohortPairResult]:
    positions = {
        key: positions_at_jd(spec.birth_jd) for key, spec in RADIX_COHORT.items()
    }
    lons = {k: {n: p.longitude_deg for n, p in v.items()} for k, v in positions.items()}
    decls = {k: {n: p.declination_deg for n, p in v.items()} for k, v in positions.items()}
    bodies = list(iter_benchmark_names())
    out: list[CohortPairResult] = []
    for left, right in COHORT_PAIRS:
        la = cross_aspects(lons[left], lons[right], left_prefix=f"{left}:", right_prefix=f"{right}:", body_names=bodies)
        dc: list[DeclinationContact] = []
        for a in bodies:
            for b in bodies:
                d1, d2 = decls[left][a], decls[right][b]
                dc.append(DeclinationContact(f"{left}:{a}", f"{right}:{b}", "par", abs(d1 - d2)))
                dc.append(DeclinationContact(f"{left}:{a}", f"{right}:{b}", "cpar", abs(d1 + d2)))
        out.append(CohortPairResult(left, right, la, dc))
    return out


def verify_expected_registry(results: list[CohortPairResult]) -> list[dict]:
    """Return match rows for expected longitude / declination contacts."""
    lon_index: dict[tuple[str, str, str, str], list[LongitudeAspect]] = {}
    for block in results:
        for asp in block.longitude_aspects:
            key = (
                block.left,
                asp.body_a.split(":")[-1],
                block.right,
                asp.body_b.split(":")[-1],
            )
            lon_index.setdefault(key, []).append(asp)
    decl_index: list[DeclinationContact] = []
    for block in results:
        decl_index.extend(block.declination)

    report: list[dict] = []
    for left, a, right, b, aspect, max_orb in EXPECTED_LONGITUDE:
        hits = lon_index.get((left, a, right, b), [])
        hit = next((h for h in hits if h.aspect == aspect), None)
        report.append(
            {
                "kind": "longitude",
                "pair": f"{left}-{right}",
                "bodies": f"{a}-{b}",
                "aspect": aspect,
                "expected_max_orb_deg": max_orb,
                "found_orb_deg": hit.orb_deg if hit else None,
                "ok": hit is not None and hit.orb_deg <= max_orb + 0.02,
            }
        )
    for left, a, right, b, kind, max_delta in EXPECTED_DECLINATION:
        optional = False
        tag_a, tag_b = f"{left}:{a}", f"{right}:{b}"
        hit = next(
            (d for d in decl_index if d.body_a == tag_a and d.body_b == tag_b and d.kind == kind),
            None,
        )
        report.append(
            {
                "kind": "declination",
                "pair": f"{left}-{right}",
                "bodies": f"{a}-{b}",
                "contact": kind,
                "expected_max_delta_deg": max_delta,
                "found_delta_deg": hit.delta_deg if hit else None,
                "ok": hit is not None and hit.delta_deg <= max_delta + 0.03,
                "verified": not optional,
            }
        )
    return report
