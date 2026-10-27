"""Unit tests for synthetic equal-weight logic (no network)."""

from __future__ import annotations

from datetime import date

from yahoo_ohlc import DailyBar, bars_to_return_series


def test_bars_to_return_series():
    bars = [
        DailyBar(date(2020, 3, 11), 10, 10, 10, 100.0, None),
        DailyBar(date(2020, 3, 12), 10, 10, 10, 90.0, None),
        DailyBar(date(2020, 3, 13), 10, 10, 10, 99.0, None),
    ]
    rets = bars_to_return_series(bars)
    assert rets[date(2020, 3, 12)] == -10.0
    assert abs(rets[date(2020, 3, 13)] - 10.0) < 0.001
