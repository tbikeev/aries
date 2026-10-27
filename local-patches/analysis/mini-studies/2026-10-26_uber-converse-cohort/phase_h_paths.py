"""Phase H output paths (does not overwrite earnings/daily reports)."""

from __future__ import annotations

from pathlib import Path

STUDY_ROOT = Path(__file__).resolve().parent
PHASE_H_OUTPUT = STUDY_ROOT / "uber-final-diagnostics" / "output"

FROZEN_ORBS_DEG = (0.5, 1.0)
SHIFT_OFFSETS_DAYS = (30, 90, 180, 365)
PLACEBO_SURROGATE_COUNT = 1000
PLACEBO_SEED = 20261027
