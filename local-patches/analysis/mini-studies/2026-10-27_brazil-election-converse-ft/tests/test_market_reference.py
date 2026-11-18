"""Unit tests for synthetic equal-weight logic (no network)."""

from __future__ import annotations

from datetime import date

from yahoo_ohlc import DailyBar, bars_to_adj_return_series, bars_to_return_series


def test_bars_to_return_series():
    bars = [
        DailyBar(date(2020, 3, 11), 10, 10, 10, 100.0, None),
        DailyBar(date(2020, 3, 12), 10, 10, 10, 90.0, None),
        DailyBar(date(2020, 3, 13), 10, 10, 10, 99.0, None),
    ]
    rets = bars_to_return_series(bars)
    assert rets[date(2020, 3, 12)] == -10.0
    assert abs(rets[date(2020, 3, 13)] - 10.0) < 0.001


def test_adj_return_unchanged_when_adj_tracks_close():
    bars = [
        DailyBar(date(2022, 12, 14), 10, 10, 10, 100.0, None, adj_close=100.0),
        DailyBar(date(2022, 12, 15), 10, 10, 10, 98.0, None, adj_close=98.0),
    ]
    assert bars_to_adj_return_series(bars)[date(2022, 12, 15)] == -2.0
    assert bars_to_return_series(bars)[date(2022, 12, 15)] == -2.0


def test_adj_return_smooths_ex_dividend_price_gap():
    # Price drops on ex-date; adjusted series back-fills so total return is ~0.
    bars = [
        DailyBar(date(2022, 12, 14), 10, 10, 10, 100.0, None, adj_close=100.0),
        DailyBar(date(2022, 12, 15), 10, 10, 10, 98.0, None, adj_close=100.0),
    ]
    assert bars_to_return_series(bars)[date(2022, 12, 15)] == -2.0
    assert bars_to_adj_return_series(bars)[date(2022, 12, 15)] == 0.0
