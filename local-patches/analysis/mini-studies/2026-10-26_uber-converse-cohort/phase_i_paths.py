"""Phase I output paths."""

from __future__ import annotations

from pathlib import Path

STUDY_ROOT = Path(__file__).resolve().parent
DECLINATION_OUTPUT = STUDY_ROOT / "declination-study" / "output"
PHASE_H_FREEZE = STUDY_ROOT / "uber-final-diagnostics" / "output" / "hypothesis_freeze.json"

DECL_ORB_PRIMARY = 0.5
DECL_ORB_SECONDARY = 1.0
DECL_ORB_EXACT = 0.25
LON_ORB_PRIMARY = 1.0
LON_ORB_TIGHT = 0.5
DUAL_DECL_ORB = 0.5

PLACEBO_SURROGATES_DEFAULT = 1000
PLACEBO_SEED_DEFAULT = 20261027
