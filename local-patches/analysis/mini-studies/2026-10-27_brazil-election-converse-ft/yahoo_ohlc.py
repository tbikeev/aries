"""Yahoo Finance chart API — daily OHLC (unadjusted) without requiring yfinance."""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone


@dataclass(frozen=True)
class DailyBar:
    session: date
    open: float
    high: float
    low: float
    close: float
    volume: float | None
    adj_close: float | None = None


def _utc_ts(d: date) -> int:
    return int(datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp())


def fetch_yahoo_daily_bars(
    symbol: str,
    start: date,
    end: date,
) -> list[DailyBar]:
    """Unadjusted daily bars from query1.finance.yahoo.com v8 chart API."""
    url = (
        "https://query1.finance.yahoo.com/v8/finance/chart/"
        + urllib.parse.quote(symbol, safe="")
        + f"?interval=1d&period1={_utc_ts(start)}&period2={_utc_ts(end + timedelta(days=1))}"
        + "&events=div,splits"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode())
    except OSError:
        return _fetch_yfinance_fallback(symbol, start, end)

    result = (data.get("chart") or {}).get("result") or []
    if not result:
        return _fetch_yfinance_fallback(symbol, start, end)
    r0 = result[0]
    ts = r0.get("timestamp") or []
    q = (r0.get("indicators") or {}).get("quote") or [{}]
    q0 = q[0] if q else {}
    opens = q0.get("open") or []
    highs = q0.get("high") or []
    lows = q0.get("low") or []
    closes = q0.get("close") or []
    vols = q0.get("volume") or []
    adj_blocks = (r0.get("indicators") or {}).get("adjclose") or [{}]
    adjcloses = adj_blocks[0].get("adjclose") if adj_blocks else []
    bars: list[DailyBar] = []
    for i, t in enumerate(ts):
        c = closes[i] if i < len(closes) else None
        if c is None:
            continue
        sess = datetime.fromtimestamp(t, tz=timezone.utc).date()
        adj = None
        if adjcloses and i < len(adjcloses) and adjcloses[i] is not None:
            adj = float(adjcloses[i])
        bars.append(
            DailyBar(
                session=sess,
                open=float(opens[i]) if i < len(opens) and opens[i] is not None else float(c),
                high=float(highs[i]) if i < len(highs) and highs[i] is not None else float(c),
                low=float(lows[i]) if i < len(lows) and lows[i] is not None else float(c),
                close=float(c),
                volume=float(vols[i]) if i < len(vols) and vols[i] is not None else None,
                adj_close=adj,
            )
        )
    bars.sort(key=lambda b: b.session)
    return bars


def _fetch_yfinance_fallback(symbol: str, start: date, end: date) -> list[DailyBar]:
    try:
        import yfinance as yf
    except ImportError:
        return []
    df = yf.download(
        symbol,
        start=start.isoformat(),
        end=(end + timedelta(days=1)).isoformat(),
        progress=False,
        auto_adjust=False,
    )
    if df is None or df.empty:
        return []
    if hasattr(df.columns, "nlevels") and df.columns.nlevels > 1:
        df = df.droplevel(1, axis=1)
    out: list[DailyBar] = []
    for idx, row in df.iterrows():
        sess = idx.date() if hasattr(idx, "date") else idx
        adj = None
        if "Adj Close" in row and row["Adj Close"] == row["Adj Close"]:
            adj = float(row["Adj Close"])
        out.append(
            DailyBar(
                session=sess,
                open=float(row["Open"]),
                high=float(row["High"]),
                low=float(row["Low"]),
                close=float(row["Close"]),
                volume=float(row["Volume"]) if "Volume" in row and row["Volume"] == row["Volume"] else None,
                adj_close=adj,
            )
        )
    return out


def _bars_to_return_series(bars: list[DailyBar], *, price: str) -> dict[date, float]:
    out: dict[date, float] = {}
    for i in range(1, len(bars)):
        prev, cur = bars[i - 1], bars[i]
        if price == "adj":
            p0, p1 = prev.adj_close, cur.adj_close
        else:
            p0, p1 = prev.close, cur.close
        if p0 is None or p1 is None or p0 <= 0:
            continue
        out[cur.session] = 100.0 * (p1 / p0 - 1.0)
    return out


def bars_to_return_series(bars: list[DailyBar]) -> dict[date, float]:
    """Unadjusted close-to-close % return keyed by session date."""
    return _bars_to_return_series(bars, price="close")


def bars_to_adj_return_series(bars: list[DailyBar]) -> dict[date, float]:
    """Adjusted close-to-close % return (splits + distributions)."""
    return _bars_to_return_series(bars, price="adj")
