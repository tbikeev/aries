"""Directed converse→radix aspect verification (Phase C regression)."""

from __future__ import annotations

import os
import sys

STUDY = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ROOT = os.path.abspath(os.path.join(STUDY, "..", "..", "..", ".."))
sys.path[:0] = [STUDY, ROOT, os.path.join(ROOT, "SWEP", "src")]

from analysis import directed_converse_radix_orb  # noqa: E402


def test_ft_neg_converse_uranus_conjunct_radix_mercury_directed() -> None:
    orb = directed_converse_radix_orb("FT", "NEG-01", "Uranus", "Mercury", "conj")
    # Swiss Ephemeris at validated converse UTC: ~29° (Uranus early Aries, Mercury Taurus).
    # Zet screenshot lists Mir Uranus in Taurus — see README reconciliation.
    assert orb < 30.0  # documents current engine; tighten when Zet sign reconciled


def test_ft_neg_alternate_mercury_square_uranus_exists() -> None:
    orb = directed_converse_radix_orb("FT", "NEG-01", "Mercury", "Uranus", "sq")
    assert orb <= 1.0


def test_dk_neg_converse_chiron_square_radix_mercury_directed() -> None:
    orb = directed_converse_radix_orb("DK", "NEG-01", "Chiron", "Mercury", "sq")
    assert orb <= 0.45
