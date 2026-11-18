"""Historical session sampling and Brazil shock dates (OHLC-defined)."""

from __future__ import annotations

from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from brazil_paths import EVENT_DATE, HISTORICAL_SAMPLE_N, HISTORICAL_SEED

ET = ZoneInfo("America/New_York")

# Large EWZ daily moves (close-to-close), documented independently of charts.
# Dates chosen from public Brazil macro/political headlines; verify in report.
BRAZIL_SHOCK_DATES: list[tuple[str, str, str]] = [
    ("2016-05-12", "negative", "Impeachment vote / political crisis"),
    ("2018-05-14", "negative", "Truckers strike begins"),
    ("2020-03-09", "negative", "COVID risk-off / oil"),
    ("2022-10-30", "mixed", "Presidential runoff (Lula win)"),
    ("2023-01-08", "negative", "Brasília riots aftermath"),
    ("2024-11-07", "positive", "Post-election fiscal relief rally"),
]


def trading_session_jd(session: date, hour: int = 9, minute: int = 30) -> float:
    import sys
    from brazil_paths import UBER_STUDY

    sys.path.insert(0, str(UBER_STUDY))
    from converse import utc_to_jd

    local = datetime.combine(session, time(hour, minute, 0), tzinfo=ET)
    utc = local.astimezone(timezone.utc)
    return utc_to_jd(utc.year, utc.month, utc.day, utc.hour, utc.minute, utc.second)


def sample_ordinary_sessions(
    yahoo_symbol: str,
    *,
    n: int = HISTORICAL_SAMPLE_N,
    end_before: date = EVENT_DATE,
    seed: int = HISTORICAL_SEED,
) -> list[date]:
    import yfinance as yf

    start = date(end_before.year - 6, 1, 1)
    df = yf.download(
        yahoo_symbol,
        start=start.isoformat(),
        end=end_before.isoformat(),
        progress=False,
        auto_adjust=False,
    )
    if df.empty:
        return []
    if isinstance(df.columns, pd.MultiIndex):
        df = df.droplevel(1, axis=1)
    df = df.reset_index()
    dates = pd.to_datetime(df["Date"]).dt.date.tolist()
    dates = [d for d in dates if d < end_before]
    if len(dates) <= n:
        return dates
    rng = np.random.default_rng(seed + hash(yahoo_symbol) % 10_000)
    idx = rng.choice(len(dates), size=n, replace=False)
    return sorted(dates[i] for i in idx)


def ewz_shock_sessions() -> pd.DataFrame:
    import yfinance as yf

    rows = []
    df = yf.download("EWZ", start="2015-01-01", end="2026-11-01", progress=False, auto_adjust=False)
    if isinstance(df.columns, pd.MultiIndex):
        df = df.droplevel(1, axis=1)
    df = df.reset_index()
    df["date"] = pd.to_datetime(df["Date"]).dt.date
    df["ret_cc"] = df["Close"].pct_change() * 100.0
    by_date = {r["date"]: r for _, r in df.iterrows()}
    for dstr, direction, reason in BRAZIL_SHOCK_DATES:
        d = date.fromisoformat(dstr)
        r = by_date.get(d)
        if r is None:
            rows.append({"shock_date": dstr, "direction_label": direction, "reason": reason, "ewz_return_cc_pct": None})
            continue
        rows.append(
            {
                "shock_date": dstr,
                "direction_label": direction,
                "reason": reason,
                "ewz_return_cc_pct": float(r["ret_cc"]) if pd.notna(r["ret_cc"]) else None,
            }
        )
    return pd.DataFrame(rows)
