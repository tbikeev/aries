"""Presets for mirror debug + power aggregate comparisons."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from astrolog_paths import STUDY_ROOT
from brazil_paths import UNIVERSE_TICKERS, YAHOO_SYMBOL_OVERRIDE

DEBUG_TICKERS = tuple(t for t in UNIVERSE_TICKERS if t != "EBR")


@dataclass(frozen=True)
class StudyConfig:
    slug: str
    title: str
    html_title: str
    events: tuple[tuple[str, str], ...]  # (iso date, label)
    rebound_date: str  # "run" / positive leg in comparison tables
    panic_date: str  # "crash" / stress leg
    rebound_label: str = "rebound"
    panic_label: str = "panic"
    output_dir: Path = field(default_factory=lambda: STUDY_ROOT / "output" / "astrolog_debug")
    tickers: tuple[str, ...] = DEBUG_TICKERS
    expected_overall: dict[tuple[str, str], tuple[int, float, float]] | None = None
    ibovespa_reference: dict[str, float] | None = None  # date -> documented IBOV C2C %


ELECTION_2026 = StudyConfig(
    slug="election_2026",
    title="Brazil FT — 5 Oct vs 26 Oct 2026 @ 09:30 NY (EDT)",
    html_title="Brazil FT mirror — Oct 2026 election (Astrolog −pd 1.0 converse)",
    events=(
        ("2026-10-05", "First-round rally"),
        ("2026-10-26", "Second-round crash (discovery)"),
    ),
    rebound_date="2026-10-05",
    panic_date="2026-10-26",
    rebound_label="run",
    panic_label="crash",
    output_dir=STUDY_ROOT / "output" / "astrolog_debug",
    expected_overall={
        ("c2c", "2026-10-05"): (113, 502.36, 4.446),
        ("c2c", "2026-10-26"): (128, 492.19, 3.845),
        ("c2r", "2026-10-05"): (288, 1089.67, 3.784),
        ("c2r", "2026-10-26"): (294, 1225.92, 4.170),
    },
)

COVID_2020 = StudyConfig(
    slug="covid_2020",
    title="Brazil ADR FT — 12 Mar vs 24 Mar 2020 @ 09:30 NY (EDT)",
    html_title="Brazil FT mirror — COVID Mar 2020 (Astrolog −pd 1.0 converse)",
    events=(
        ("2020-03-12", "COVID panic crash (Ibovespa −14.78% C2C)"),
        ("2020-03-24", "COVID stimulus rebound (Ibovespa +9.69% C2C)"),
    ),
    rebound_date="2020-03-24",
    panic_date="2020-03-12",
    rebound_label="rebound",
    panic_label="panic",
    output_dir=STUDY_ROOT / "output" / "astrolog_debug_covid_2020",
    ibovespa_reference={
        "2020-03-12": -14.78,
        "2020-03-24": 9.69,
    },
)


def yahoo_for_ticker(ticker: str) -> str:
    return YAHOO_SYMBOL_OVERRIDE.get(ticker, ticker)
