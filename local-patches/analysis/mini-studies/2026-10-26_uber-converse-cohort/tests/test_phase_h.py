"""Phase H smoke tests."""

from __future__ import annotations

import sys
from pathlib import Path

STUDY = Path(__file__).resolve().parents[1]
ROOT = STUDY.parents[3]
sys.path[:0] = [str(STUDY), str(ROOT), str(ROOT / "SWEP" / "src")]

from converse import mirrored_jd  # noqa: E402
from phase_h_data import load_earnings_panel  # noqa: E402


def test_cc_gap_intra_identity() -> None:
    df = load_earnings_panel()
    assert df["cc_identity_err_bps"].max() < 0.05


def test_converse_shift_doubles() -> None:
    b, e = 2450000.0, 2451000.0
    delta = 30.0
    assert mirrored_jd(b + delta, e) == mirrored_jd(b, e) + 2 * delta
