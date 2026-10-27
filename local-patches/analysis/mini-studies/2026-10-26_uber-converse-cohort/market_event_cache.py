"""Per-ticker earnings reaction cache (radix-independent)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from cross_company_data import resolve_ticker_csv
from earnings_converse import event_jd_from_datetime
from earnings_loader import load_earnings_csv
from market_reactions import build_reactions, load_ohlc_csv
from multi_company_earnings import dedupe_earnings_rows, pre_event_volatility


def cache_path(cache_dir: Path, ticker: str) -> Path:
    return cache_dir / "market_events" / f"{ticker.upper()}.csv"


def build_market_event_table(
    ticker: str,
    *,
    earnings_path=None,
    ohlc_path=None,
) -> tuple[pd.DataFrame, dict]:
    ep = earnings_path or resolve_ticker_csv(ticker, kind="earnings")
    op = ohlc_path or resolve_ticker_csv(ticker, kind="ohlc")
    meta: dict = {"ticker": ticker.upper()}
    if not ep or not op:
        meta["skip_reason"] = "missing earnings or OHLC"
        return pd.DataFrame(), meta
    earnings = load_earnings_csv(ep)
    earnings, dup = dedupe_earnings_rows(earnings)
    meta["duplicate_earnings_dropped"] = dup
    ohlc = load_ohlc_csv(op)
    first_trade = ohlc["session"].min()
    reactions = build_reactions(earnings, ohlc, first_trade_session=first_trade)
    rows = []
    for r in reactions:
        if r.excluded or r.event_datetime_utc is None:
            continue
        ejd = event_jd_from_datetime(r.event_datetime_utc)
        vol = pre_event_volatility(ohlc, r.reaction_session)
        rows.append(
            {
                "ticker": ticker.upper(),
                "report_date": str(r.report_date),
                "reaction_date": str(r.reaction_session),
                "event_jd_ut": ejd,
                "return_cc": r.r_cc_pct,
                "return_gap": r.r_gap_pct,
                "return_intraday": r.r_intra_pct,
                "abs_return_cc": r.abs_r_cc_pct,
                "return_2d": r.r_2d_pct,
                "return_5d": r.r_5d_pct,
                "pre_event_volatility": vol,
                "event_quality": "ambiguous_timing" if r.mapping_uncertain else "ok",
                "timing": r.timing,
                "eps_surprise_pct": r.eps_surprise_pct,
            }
        )
    df = pd.DataFrame(rows)
    meta["valid_events"] = len(df)
    return df, meta


def load_or_build_market_events(
    ticker: str,
    cache_dir: Path,
    *,
    reuse: bool = True,
) -> tuple[pd.DataFrame, dict]:
    path = cache_path(cache_dir, ticker)
    if reuse and path.exists():
        df = pd.read_csv(path)
        return df, {"ticker": ticker.upper(), "from_cache": True, "valid_events": len(df)}
    df, meta = build_market_event_table(ticker)
    if not df.empty:
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(path, index=False)
    meta["from_cache"] = False
    return df, meta
