"""Mandatory converse UTC timestamp tests (Zet coefficient -1)."""

from __future__ import annotations

import os
import sys

STUDY = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ROOT = os.path.abspath(os.path.join(STUDY, "..", "..", "..", ".."))
sys.path[:0] = [STUDY, ROOT, os.path.join(ROOT, "SWEP", "src")]

from converse import converse_utc, utc_to_jd  # noqa: E402
from radix import EVENTS, RADIX_COHORT  # noqa: E402


def _check(radix_key: str, event_key: str, expected: tuple[int, int, int, int, int, int]) -> None:
    r = RADIX_COHORT[radix_key]
    e = EVENTS[event_key]
    got = converse_utc(r.birth_jd, e.event_jd)
    assert got == expected, f"{radix_key}/{event_key}: {got} != {expected}"


def test_ft_neg_pos_converse_utc() -> None:
    _check("FT", "NEG-01", (2012, 8, 12, 17, 10, 0))
    _check("FT", "POS-01", (2012, 2, 10, 15, 40, 0))


def test_inc_neg_pos_converse_utc() -> None:
    _check("INC", "NEG-01", (2000, 4, 21, 17, 30, 0))
    _check("INC", "POS-01", (1999, 10, 20, 16, 0, 0))


def test_dk_neg_pos_converse_utc() -> None:
    _check("DK", "NEG-01", (1912, 9, 18, 3, 30, 0))
    _check("DK", "POS-01", (1912, 3, 18, 2, 0, 0))
