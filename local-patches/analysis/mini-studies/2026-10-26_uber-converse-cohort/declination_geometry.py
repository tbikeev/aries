"""Signed declination Par / Cpar classification (mutually exclusive per pair)."""

from __future__ import annotations

EQUATOR_EPS_DEG = 0.01
DECL_ORBS = (0.25, 0.5, 1.0)  # 15', 30', 1°


def classify_declination_pair(d_conv: float, d_radix: float) -> list[tuple[str, float]]:
    """
    Return at most one of ('par', orb) or ('cpar', orb) per directed pair.
    Par: same hemisphere (product > eps²). Cpar: opposite hemispheres.
    """
    d1, d2 = float(d_conv), float(d_radix)
    par_orb = abs(d1 - d2)
    cpar_orb = abs(abs(d1) - abs(d2))
    if abs(d1) < EQUATOR_EPS_DEG and abs(d2) < EQUATOR_EPS_DEG:
        return [("par", par_orb)]
    prod = d1 * d2
    if prod > EQUATOR_EPS_DEG**2:
        return [("par", par_orb)]
    if prod < -(EQUATOR_EPS_DEG**2):
        return [("cpar", cpar_orb)]
    # Straddling equator: assign tighter orb only (avoid double count).
    if par_orb <= cpar_orb:
        return [("par", par_orb)]
    return [("cpar", cpar_orb)]


def orb_within(orb: float, threshold: float) -> bool:
    return orb <= threshold + 1e-12
