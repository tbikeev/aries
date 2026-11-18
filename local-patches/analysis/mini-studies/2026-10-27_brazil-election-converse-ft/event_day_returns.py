"""Fetch unadjusted close-to-close returns for event dates (yfinance)."""

from __future__ import annotations

import csv
from datetime import date, timedelta
from pathlib import Path

from astrolog_study_config import StudyConfig, yahoo_for_ticker


def _prev_trading_day(d: date) -> date:
    p = d - timedelta(days=1)
    while p.weekday() >= 5:
        p -= timedelta(days=1)
    return p


def _fetch_yahoo_chart_closes(symbol: str, start: date, end: date) -> dict[date, float]:
    import json
    import urllib.parse
    import urllib.request

    from datetime import datetime, timezone

    def _ts(d: date) -> int:
        return int(datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp())

    url = (
        "https://query1.finance.yahoo.com/v8/finance/chart/"
        + urllib.parse.quote(symbol, safe="")
        + f"?interval=1d&period1={_ts(start)}&period2={_ts(end + timedelta(days=1))}"
        + "&events=div,splits"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
    except OSError:
        return {}
    result = data.get("chart", {}).get("result") or []
    if not result:
        return {}
    r0 = result[0]
    ts = r0.get("timestamp") or []
    closes = (r0.get("indicators", {}).get("quote") or [{}])[0].get("close") or []
    out: dict[date, float] = {}
    for t, c in zip(ts, closes):
        if c is None:
            continue
        out[datetime.fromtimestamp(t, tz=timezone.utc).date()] = float(c)
    return out


def fetch_return_cc_pct(symbol: str, event: date) -> tuple[float | None, str]:
    prev = _prev_trading_day(event)
    start = prev - timedelta(days=14)
    end = event + timedelta(days=5)
    closes = _fetch_yahoo_chart_closes(symbol, start, end)
    if not closes:
        try:
            import yfinance as yf
        except ImportError:
            return None, "no_history"
        hist = yf.Ticker(symbol).history(
            start=start.isoformat(), end=end.isoformat(), auto_adjust=False
        )
        if hist is None or hist.empty:
            return None, "no_history"
        closes = {x.date(): float(row["Close"]) for x, row in hist.iterrows()}
    if event not in closes:
        return None, "no_event_bar"
    dates = sorted(closes.keys())
    ei = dates.index(event)
    if ei == 0:
        return None, "no_prev_bar"
    prev_close = closes[dates[ei - 1]]
    event_close = closes[event]
    if prev_close <= 0:
        return None, "bad_prev_close"
    ret = 100.0 * (event_close / prev_close - 1.0)
    return ret, "yahoo_chart_unadj_close"


def write_event_returns(study: StudyConfig, path: Path) -> list[dict]:
    rows: list[dict] = []
    event_dates = {d for d, _ in study.events}
    for ed in sorted(event_dates):
        if study.ibovespa_reference and ed in study.ibovespa_reference:
            rows.append(
                {
                    "ticker": "IBOVESPA",
                    "yahoo_symbol": "^BVSP",
                    "event_date": ed,
                    "return_cc_pct": study.ibovespa_reference[ed],
                    "data_source": "documented_ibovespa",
                    "data_flag": "reference",
                }
            )
        ret, flag = fetch_return_cc_pct("^BVSP", date.fromisoformat(ed))
        if ret is not None:
            rows.append(
                {
                    "ticker": "IBOVESPA_YF",
                    "yahoo_symbol": "^BVSP",
                    "event_date": ed,
                    "return_cc_pct": round(ret, 2),
                    "data_source": "yfinance_unadj_close",
                    "data_flag": flag,
                }
            )
    for ticker in study.tickers:
        sym = yahoo_for_ticker(ticker)
        for ed in sorted(event_dates):
            ret, flag = fetch_return_cc_pct(sym, date.fromisoformat(ed))
            if ret is None and ticker == "ERJ":
                ret, flag = fetch_return_cc_pct("ERJ", date.fromisoformat(ed))
            if ret is None and ticker == "NU":
                pass  # listed Dec 2021
            rows.append(
                {
                    "ticker": ticker,
                    "yahoo_symbol": sym,
                    "event_date": ed,
                    "return_cc_pct": round(ret, 2) if ret is not None else "",
                    "data_source": flag if ret is not None else "",
                    "data_flag": flag if ret is None else "ok",
                }
            )
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["ticker", "yahoo_symbol", "event_date", "return_cc_pct", "data_source", "data_flag"]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    return rows


def load_returns_csv(path: Path) -> dict[tuple[str, str], float]:
    out: dict[tuple[str, str], float] = {}
    if not path.is_file():
        return out
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            t = row.get("ticker", "")
            ed = row.get("event_date", "")
            raw = row.get("return_cc_pct", "")
            if raw in ("", None):
                continue
            try:
                out[(t, ed)] = float(raw)
            except ValueError:
                continue
    return out
