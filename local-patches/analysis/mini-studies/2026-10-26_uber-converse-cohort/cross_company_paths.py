"""Paths and frozen cross-company study configuration."""

from __future__ import annotations

import os
from pathlib import Path

STUDY_ROOT = Path(__file__).resolve().parent
CROSS_OUTPUT = STUDY_ROOT / "cross-company-study" / "output"
CROSS_INPUT = STUDY_ROOT / "cross-company-study" / "input"
CROSS_CACHE = STUDY_ROOT / "cross-company-study" / "cache"

DEFAULT_UNIVERSE_CSV = CROSS_INPUT / "universe_cohort_all.csv"

# Frozen hypothesis (transferred from UBER Phase H / I).
FROZEN_SQ_ORB_DEG = 1.0
FROZEN_SQ_ORB_HALF_DEG = 0.5
PRIMARY_FEATURE = "square_count_1deg"
SECONDARY_FEATURES = ("square_count_0p5deg", "tight_count_1deg")

PARTITION_SEED = 20261027
PLACEBO_SEED_DEFAULT = 20261027
PLACEBO_SURROGATES_DEFAULT = 1000

DISCOVERY_TICKER = "UBER"

EARNINGS_ROOTS = [
    Path("/Users/thomasbikeev/Projects/listok_fd/finance_data_downloader/data/eodhd_earnings"),
    Path(
        "/Users/thomasbikeev/Projects/listok/finance-data-downloader/"
        "finance_data_downloader/data/eodhd_earnings"
    ),
]
OHLC_ROOTS = [
    Path(
        "/Users/thomasbikeev/Projects/listok/finance-data-downloader/"
        "finance_data_downloader/data/eodhd_ohlc"
    ),
]

# Override via environment for other machines.
if os.environ.get("EODHD_EARNINGS_DIR"):
    EARNINGS_ROOTS.insert(0, Path(os.environ["EODHD_EARNINGS_DIR"]))
if os.environ.get("EODHD_OHLC_DIR"):
    OHLC_ROOTS.insert(0, Path(os.environ["EODHD_OHLC_DIR"]))
