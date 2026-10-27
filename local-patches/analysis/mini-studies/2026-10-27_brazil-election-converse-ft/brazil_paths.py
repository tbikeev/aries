"""Paths and constants — Brazil election converse FT study."""

from __future__ import annotations

from datetime import date, datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

STUDY_ROOT = Path(__file__).resolve().parent
UBER_STUDY = STUDY_ROOT.parent / "2026-10-26_uber-converse-cohort"
OUTPUT = STUDY_ROOT / "output"
CACHE = STUDY_ROOT / "cache"
FIXTURES = STUDY_ROOT / "fixtures"

UNIVERSE_TICKERS = (
    "PAGS",
    "XP",
    "STNE",
    "NU",
    "ITUB",
    "BBD",
    "PBR",
    "ABEV",
    "EBR",
    "VALE",
    "ERJ",
)

EVENT_DATE = date(2026, 10, 26)
EVENT_TZ = ZoneInfo("America/New_York")
EVENT_LOCAL = datetime(2026, 10, 26, 9, 30, 0, tzinfo=EVENT_TZ)
PREV_CLOSE_DATE = date(2026, 10, 23)  # Friday before Monday event

ORB_PRIMARY = 1.0
ORB_SECONDARY = 0.5
HISTORICAL_SAMPLE_N = 100
HISTORICAL_SEED = 20261027
PLACEBO_SEED = 20261027

MUNKASEY_XLSX = Path(
    "/Users/thomasbikeev/Library/Mobile Documents/com~apple~CloudDocs/Documents/Munkasey/Companies2 a.xlsx"
)

# Yahoo symbols when US ticker differs (documented in registry).
YAHOO_SYMBOL_OVERRIDE = {
    "ERJ": "EMBJ",  # Embraer ADR; ERJ not on Yahoo at run time
}

# Munkasey symbol aliases for FT lookup.
MUNKASEY_SYMBOL_OVERRIDE = {
    "ERJ": "EMBJ",
}
