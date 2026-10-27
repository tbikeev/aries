"""Event-day OHLC returns (Yahoo primary for 2026-10-26; local EODHD for history)."""

from __future__ import annotations

from datetime import date

import pandas as pd

from brazil_paths import EVENT_DATE, PREV_CLOSE_DATE, YAHOO_SYMBOL_OVERRIDE


def fetch_event_returns(tickers: list[str], *, include_benchmarks: bool = True) -> pd.DataFrame:
    import yfinance as yf

    rows = []
    for t in tickers:
        ysym = YAHOO_SYMBOL_OVERRIDE.get(t, t)
        try:
            df = yf.download(
                ysym,
                start="2026-10-15",
                end="2026-11-05",
                progress=False,
                auto_adjust=False,
            )
        except Exception:
            df = pd.DataFrame()
        if df.empty:
            rows.append(
                {
                    "ticker": t,
                    "yahoo_symbol": ysym,
                    "return_cc_pct": None,
                    "data_flag": "no_yahoo_data",
                }
            )
            continue
        if isinstance(df.columns, pd.MultiIndex):
            df = df.droplevel(1, axis=1)
        df = df.reset_index()
        df["date"] = pd.to_datetime(df["Date"]).dt.date
        prev = df[df["date"] == PREV_CLOSE_DATE]
        ev = df[df["date"] == EVENT_DATE]
        if prev.empty or ev.empty:
            rows.append({"ticker": t, "yahoo_symbol": ysym, "return_cc_pct": None, "data_flag": "missing_session"})
            continue
        c0 = float(prev["Close"].iloc[0])
        o1 = float(ev["Open"].iloc[0])
        c1 = float(ev["Close"].iloc[0])
        rows.append(
            {
                "ticker": t,
                "yahoo_symbol": ysym,
                "prev_close_date": str(PREV_CLOSE_DATE),
                "event_date": str(EVENT_DATE),
                "prev_close_unadj": c0,
                "event_open_unadj": o1,
                "event_close_unadj": c1,
                "event_high_unadj": float(ev["High"].iloc[0]),
                "event_low_unadj": float(ev["Low"].iloc[0]),
                "return_cc_pct": 100.0 * (c1 / c0 - 1.0),
                "return_gap_pct": 100.0 * (o1 / c0 - 1.0),
                "return_intra_pct": 100.0 * (c1 / o1 - 1.0) if o1 else None,
                "abs_return_cc_pct": abs(100.0 * (c1 / c0 - 1.0)),
                "price_basis": "unadjusted_close",
                "data_source": "yfinance",
                "data_flag": "ok",
            }
        )
    out = pd.DataFrame(rows)
    if include_benchmarks:
        for bench in ("EWZ", "SPY"):
            if bench not in out["ticker"].values:
                bench_rows = fetch_event_returns([bench], include_benchmarks=False)
                out = pd.concat([out, bench_rows], ignore_index=True)
    if "return_cc_pct" in out.columns:
        ewz = out.loc[out["ticker"] == "EWZ", "return_cc_pct"]
        spy = out.loc[out["ticker"] == "SPY", "return_cc_pct"]
        ewz_r = float(ewz.iloc[0]) if len(ewz) and pd.notna(ewz.iloc[0]) else None
        spy_r = float(spy.iloc[0]) if len(spy) and pd.notna(spy.iloc[0]) else None
        for i, row in out.iterrows():
            if row["ticker"] in ("EWZ", "SPY"):
                continue
            if ewz_r is not None and pd.notna(row.get("return_cc_pct")):
                out.at[i, "return_vs_ewz_pp"] = float(row["return_cc_pct"]) - ewz_r
            if spy_r is not None and pd.notna(row.get("return_cc_pct")):
                out.at[i, "return_vs_spy_pp"] = float(row["return_cc_pct"]) - spy_r
    return out
