"""Load EODHD earnings CSV (read-only)."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path


@dataclass(frozen=True)
class EarningsRow:
    code: str
    report_date: date
    fiscal_period_end: date
    before_after_market: str
    currency: str
    actual: float | None
    estimate: float | None
    difference: float | None
    surprise_pct: float | None


def _parse_float(value: str) -> float | None:
    text = (value or "").strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _parse_date(value: str) -> date:
    y, m, d = value.strip().split("-")
    return date(int(y), int(m), int(d))


def load_earnings_csv(path: Path) -> list[EarningsRow]:
    rows: list[EarningsRow] = []
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for raw in reader:
            rows.append(
                EarningsRow(
                    code=raw["code"],
                    report_date=_parse_date(raw["report_date"]),
                    fiscal_period_end=_parse_date(raw["date"]),
                    before_after_market=(raw.get("before_after_market") or "").strip(),
                    currency=raw.get("currency", ""),
                    actual=_parse_float(raw.get("actual", "")),
                    estimate=_parse_float(raw.get("estimate", "")),
                    difference=_parse_float(raw.get("difference", "")),
                    surprise_pct=_parse_float(raw.get("percent", "")),
                )
            )
    rows.sort(key=lambda r: (r.report_date, r.before_after_market))
    return rows
