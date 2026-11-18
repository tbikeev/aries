"""Resolve local EODHD CSV paths per ticker."""

from __future__ import annotations

from pathlib import Path

from cross_company_paths import EARNINGS_ROOTS, OHLC_ROOTS


def resolve_ticker_csv(ticker: str, *, kind: str) -> Path | None:
    """Return first existing ``TICKER.csv`` under known data roots."""
    roots = EARNINGS_ROOTS if kind == "earnings" else OHLC_ROOTS
    name = f"{ticker.upper()}.csv"
    for root in roots:
        if not root.is_dir():
            continue
        candidate = root / name
        if candidate.is_file():
            return candidate
    return None


def inventory_ticker(ticker: str) -> dict:
    ep = resolve_ticker_csv(ticker, kind="earnings")
    op = resolve_ticker_csv(ticker, kind="ohlc")
    return {
        "ticker": ticker.upper(),
        "earnings_csv": str(ep) if ep else None,
        "ohlc_csv": str(op) if op else None,
        "has_earnings": ep is not None,
        "has_ohlc": op is not None,
        "eligible_files": ep is not None and op is not None,
    }
