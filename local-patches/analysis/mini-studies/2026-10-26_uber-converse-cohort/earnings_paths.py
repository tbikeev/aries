"""Default local data paths (discovered on Thomas's Mac)."""

from __future__ import annotations

from pathlib import Path

STUDY_ROOT = Path(__file__).resolve().parent
EARNINGS_OUTPUT = STUDY_ROOT / "earnings-study" / "output"

DEFAULT_EARNINGS_CSV = Path(
    "/Users/thomasbikeev/Projects/listok_fd/finance_data_downloader/data/eodhd_earnings/UBER.csv"
)
DEFAULT_OHLC_CSV = Path(
    "/Users/thomasbikeev/Projects/listok/finance-data-downloader/finance_data_downloader/data/eodhd_ohlc/UBER.csv"
)

# Alternate layout (listok vs listok_fd)
EARNINGS_CANDIDATES = [
    DEFAULT_EARNINGS_CSV,
    Path("/Users/thomasbikeev/Projects/listok/finance-data-downloader/finance_data_downloader/data/eodhd_earnings/UBER.csv"),
]


def resolve_earnings_csv(path: Path | None = None) -> Path:
    if path and path.exists():
        return path
    for candidate in EARNINGS_CANDIDATES:
        if candidate.exists():
            return candidate
    raise FileNotFoundError("UBER earnings CSV not found; pass --earnings-csv")


def resolve_ohlc_csv(path: Path | None = None) -> Path:
    p = path or DEFAULT_OHLC_CSV
    if not p.exists():
        raise FileNotFoundError(f"OHLC CSV not found: {p}")
    return p
