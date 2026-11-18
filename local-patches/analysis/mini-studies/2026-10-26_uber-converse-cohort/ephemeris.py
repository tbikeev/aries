"""Swiss Ephemeris adapter (Aries ``astrology`` module, headless)."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import Iterable

# Repo root: .../aries
_ARIES_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
if _ARIES_ROOT not in sys.path:
    sys.path.insert(0, _ARIES_ROOT)
_swep = os.path.join(_ARIES_ROOT, "SWEP", "src")
if _swep not in sys.path:
    sys.path.insert(0, _swep)

import astrology  # noqa: E402

_EPHE_DIR = os.path.join(_ARIES_ROOT, "SWEP", "Ephem")
if os.path.isdir(_EPHE_DIR):
    astrology.swe_set_ephe_path(_EPHE_DIR)

CALC_FLAG = astrology.SEFLG_SWIEPH | astrology.SEFLG_SPEED
EQU_FLAG = (CALC_FLAG & ~astrology.SEFLG_SIDEREAL) | astrology.SEFLG_EQUATORIAL

BENCHMARK_IDS: tuple[tuple[str, int], ...] = (
    ("Sun", astrology.SE_SUN),
    ("Moon", astrology.SE_MOON),
    ("Mercury", astrology.SE_MERCURY),
    ("Venus", astrology.SE_VENUS),
    ("Mars", astrology.SE_MARS),
    ("Jupiter", astrology.SE_JUPITER),
    ("Saturn", astrology.SE_SATURN),
    ("Uranus", astrology.SE_URANUS),
    ("Neptune", astrology.SE_NEPTUNE),
    ("Pluto", astrology.SE_PLUTO),
    ("Node", astrology.SE_TRUE_NODE),
)

OPTIONAL_IDS: tuple[tuple[str, int], ...] = (
    ("Chiron", astrology.SE_CHIRON),
    ("Lilith", astrology.SE_MEAN_APOG),
)


@dataclass(frozen=True)
class BodyPosition:
    name: str
    longitude_deg: float
    declination_deg: float
    speed_lon: float
    retrograde: bool


def position_at_jd(jd_ut: float, swe_id: int, name: str) -> BodyPosition:
    _err, ecl = astrology.swe_calc_ut(jd_ut, swe_id, CALC_FLAG)
    _err, equ = astrology.swe_calc_ut(jd_ut, swe_id, EQU_FLAG)
    speed = float(ecl[3])
    return BodyPosition(
        name=name,
        longitude_deg=float(ecl[0]) % 360.0,
        declination_deg=float(equ[1]),
        speed_lon=speed,
        retrograde=speed < 0.0,
    )


def positions_at_jd(
    jd_ut: float,
    *,
    include_optional: bool = False,
) -> dict[str, BodyPosition]:
    out: dict[str, BodyPosition] = {}
    for name, swe_id in BENCHMARK_IDS:
        out[name] = position_at_jd(jd_ut, swe_id, name)
    if include_optional:
        for name, swe_id in OPTIONAL_IDS:
            try:
                out[name] = position_at_jd(jd_ut, swe_id, name)
            except Exception:
                continue
    return out


def houses_at_jd(jd_ut: float, lat_deg: float, lon_deg: float) -> dict[str, BodyPosition]:
    """Placidus Asc/MC at geographic location (optional Zet comparison)."""
    import houses  # noqa: WPS433

    cusps, ascmc = houses.Houses(
        jd_ut,
        lat_deg,
        lon_deg,
        b"=P",  # Placidus
    ).houses()
    asc_lon = float(ascmc[0])
    mc_lon = float(ascmc[1])
    return {
        "Asc": BodyPosition("Asc", asc_lon % 360.0, 0.0, 0.0, False),
        "MC": BodyPosition("MC", mc_lon % 360.0, 0.0, 0.0, False),
    }


def iter_benchmark_names() -> Iterable[str]:
    for name, _ in BENCHMARK_IDS:
        yield name
