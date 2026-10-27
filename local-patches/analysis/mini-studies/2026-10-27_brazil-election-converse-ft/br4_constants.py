"""BR-4 constants and paths."""

from __future__ import annotations

from pathlib import Path

from brazil_paths import STUDY_ROOT

CONTROLLED_DIR = STUDY_ROOT / "output" / "br3_5_controlled"
OUTPUT_BR4 = STUDY_ROOT / "output" / "br4"

# Minimum eligible observations per tail for pooled ranking eligibility.
MIN_POOLED_N_PER_TAIL = 15
# Minimum per-ticker N in each tail for ticker to count toward consistency stats.
MIN_TICKER_N_PER_TAIL = 3

BOOTSTRAP_DRAWS = 250
PERMUTATION_DRAWS = 250
RNG_SEED = 20261027
