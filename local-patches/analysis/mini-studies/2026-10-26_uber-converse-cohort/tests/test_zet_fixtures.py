"""Compare computed positions to transcribed Zet Mirror RH screenshots."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

STUDY = Path(__file__).resolve().parents[1]
ROOT = STUDY.parents[3]
sys.path[:0] = [str(STUDY), str(ROOT), str(ROOT / "SWEP" / "src")]

from analysis import converse_jd_for  # noqa: E402
from ephemeris import positions_at_jd  # noqa: E402

FIXTURES = STUDY / "fixtures" / "zet_transcribed"


def _load(name: str) -> dict:
    path = FIXTURES / f"{name}.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _sign_lon(sign_index: int, d: float, m: float, s: float) -> float:
    return (sign_index * 30.0) + d + m / 60.0 + s / 3600.0


SIGNS = {
    "Aries": 0,
    "Taurus": 1,
    "Gemini": 2,
    "Cancer": 3,
    "Leo": 4,
    "Virgo": 5,
    "Libra": 6,
    "Scorpio": 7,
    "Sagittarius": 8,
    "Capricorn": 9,
    "Aquarius": 10,
    "Pisces": 11,
}


def test_ft_neg_spot_longitudes() -> None:
    data = _load("ft-neg")
    if not data:
        return
    cjd = converse_jd_for("FT", "NEG-01")
    pos = positions_at_jd(cjd)
    mir = data.get("mirror", {})
    for body, spec in mir.items():
        if body not in pos or "sign" not in spec:
            continue
        exp = _sign_lon(SIGNS[spec["sign"]], spec["d"], spec["m"], spec["s"])
        limit = 0.01 if body == "Node" else 0.002
        assert abs(pos[body].longitude_deg - exp) < limit, f"{body} lon delta {pos[body].longitude_deg - exp}"


def test_spot_checks_hardcoded() -> None:
    """Reference spot values from Thomas brief (converse / mirror column)."""
    spots = [
        ("FT", "NEG-01", "Sun", 140.3814),
        ("FT", "NEG-01", "Mars", 203.1288),
        ("FT", "POS-01", "Sun", 321.3003),
        ("FT", "POS-01", "Jupiter", 33.8936),
        ("INC", "NEG-01", "Saturn", 48.0003),
        ("INC", "POS-01", "Venus", 160.7392),
        ("DK", "NEG-01", "Jupiter", 248.685),
    ]
    for rk, ev, body, exp in spots:
        cjd = converse_jd_for(rk, ev)
        got = positions_at_jd(cjd)[body].longitude_deg
        assert abs(got - exp) < 0.002, f"{rk}/{ev}/{body}: {got} vs {exp}"
