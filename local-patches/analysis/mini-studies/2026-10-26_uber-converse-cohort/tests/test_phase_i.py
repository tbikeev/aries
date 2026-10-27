"""Phase I declination tests."""

from __future__ import annotations

import sys
from pathlib import Path

STUDY = Path(__file__).resolve().parents[1]
ROOT = STUDY.parents[3]
sys.path[:0] = [str(STUDY), str(ROOT), str(ROOT / "SWEP" / "src")]

from declination_geometry import classify_declination_pair  # noqa: E402


def test_parallel_same_sign() -> None:
    kinds = classify_declination_pair(10.0, 10.5)
    assert len(kinds) == 1
    assert kinds[0][0] == "par"
    assert abs(kinds[0][1] - 0.5) < 1e-9


def test_contrapar_opposite_sign() -> None:
    kinds = classify_declination_pair(10.0, -10.2)
    assert len(kinds) == 1
    assert kinds[0][0] == "cpar"
    assert abs(kinds[0][1] - 0.2) < 1e-9


def test_equator_not_both() -> None:
    kinds = classify_declination_pair(0.005, -0.004)
    assert len(kinds) == 1


def test_double_activation_requires_same_pair() -> None:
    from phase_i_dual import build_dual_contacts
    import pandas as pd

    asp = pd.DataFrame(
        [
            {
                "report_date": "2020-01-01",
                "radix_key": "DK",
                "from_body": "conv:Mars",
                "to_body": "radix:Saturn",
                "best_aspect": "sq",
                "best_orb": 0.5,
            }
        ]
    )
    decl = pd.DataFrame(
        [
            {
                "report_date": "2020-01-01",
                "radix_key": "DK",
                "conv_body": "Mars",
                "radix_body": "Saturn",
                "decl_aspect": "par",
                "decl_orb_deg": 0.2,
            }
        ]
    )
    dual = build_dual_contacts(asp, decl)
    assert len(dual) == 1
    wrong = pd.DataFrame(
        [
            {
                "report_date": "2020-01-01",
                "radix_key": "DK",
                "conv_body": "Venus",
                "radix_body": "Saturn",
                "decl_aspect": "par",
                "decl_orb_deg": 0.2,
            }
        ]
    )
    assert len(build_dual_contacts(asp, wrong)) == 0
