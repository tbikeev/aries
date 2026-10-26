"""Converse transit clock (Zet coefficient -1 / Aries Converse Transit).

Formula (continuous UT Julian day):

    T_conv = 2 * T_radix - T_event

Aries canonical implementation: ``engine.converse_transits.mirrored_jd`` (same formula).
This module is headless (no wx) and mirrors ``jd_to_utc_tuple`` rounding rules.
"""

from __future__ import annotations

import astrology
import util

GREGORIAN = 0


def mirrored_jd(birth_jd: float, event_jd: float) -> float:
    return (2.0 * float(birth_jd)) - float(event_jd)


def utc_to_jd(year: int, month: int, day: int, hour: int, minute: int = 0, second: int = 0) -> float:
    ut = hour + (minute / 60.0) + (second / 3600.0)
    return float(astrology.swe_julday(int(year), int(month), int(day), ut, astrology.SE_GREG_CAL))


def jd_to_utc_tuple(jd_value: float) -> tuple[int, int, int, int, int, int]:
    year, month, day, hour = astrology.swe_revjul(float(jd_value), astrology.SE_GREG_CAL)
    total_seconds = int(round(float(hour) * 3600.0))
    if total_seconds >= 24 * 3600:
        total_seconds -= 24 * 3600
        year, month, day = util.incrDay(int(year), int(month), int(day))
    elif total_seconds < 0:
        total_seconds += 24 * 3600
        year, month, day = util.decrDay(int(year), int(month), int(day))
    hour, remainder = divmod(total_seconds, 3600)
    minute, second = divmod(remainder, 60)
    return (int(year), int(month), int(day), int(hour), int(minute), int(second))


def converse_utc(
    birth_jd: float,
    event_jd: float,
) -> tuple[int, int, int, int, int, int]:
    return jd_to_utc_tuple(mirrored_jd(birth_jd, event_jd))
