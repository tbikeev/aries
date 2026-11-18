"""Build earnings reactions for each ticker in the universe."""

from __future__ import annotations

from datetime import datetime

import pandas as pd

from cross_company_data import inventory_ticker, resolve_ticker_csv
from earnings_converse import event_jd_from_datetime
from earnings_loader import load_earnings_csv
from executive_radices import build_executive_radix
from market_reactions import build_reactions, load_ohlc_csv, reactions_to_dataframe, report_date_key


def dedupe_earnings_rows(rows: list, *, policy: str = "keep_first") -> tuple[list, int]:
    """Collapse duplicate report_date rows (same fiscal announcement)."""
    seen: set[tuple] = set()
    out = []
    dropped = 0
    for er in rows:
        key = (er.report_date, er.before_after_market)
        if key in seen:
            dropped += 1
            continue
        seen.add(key)
        out.append(er)
    return out, dropped


def pre_event_volatility(ohlc: pd.DataFrame, reaction_session, *, window: int = 20) -> float | None:
    if reaction_session is None:
        return None
    df = ohlc.sort_values("session")
    df = df[df["session"] < reaction_session].tail(window)
    if len(df) < 5:
        return None
    rets = df["px_close"].pct_change().dropna()
    if len(rets) < 3:
        return None
    return float(rets.std() * 100.0)


def build_company_events(
    *,
    ticker: str,
    universe_row: pd.Series,
    earnings_path=None,
    ohlc_path=None,
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Returns (event_panel, aspect_rows, meta)."""
    inv = inventory_ticker(ticker)
    ep = earnings_path or resolve_ticker_csv(ticker, kind="earnings")
    op = ohlc_path or resolve_ticker_csv(ticker, kind="ohlc")
    meta = {**inv, "duplicate_earnings_dropped": 0, "valid_events": 0}
    if not ep or not op:
        meta["skip_reason"] = "missing earnings or OHLC"
        return pd.DataFrame(), pd.DataFrame(), meta

    radix = build_executive_radix(
        ticker=ticker,
        executive=str(universe_row.get("executive", "")),
        dob_str=str(universe_row["dob"]),
        verification_status=str(universe_row.get("verification_status", "")),
    )
    earnings = load_earnings_csv(ep)
    earnings, dup = dedupe_earnings_rows(earnings)
    meta["duplicate_earnings_dropped"] = dup
    ohlc = load_ohlc_csv(op)
    first_trade = ohlc["session"].min()
    reactions = build_reactions(earnings, ohlc, first_trade_session=first_trade)
    react_df = reactions_to_dataframe(reactions)

    from cross_company_features import extract_event_features

    event_rows: list[dict] = []
    aspect_parts: list[pd.DataFrame] = []
    for r in reactions:
        if r.excluded or r.event_datetime_utc is None:
            continue
        ejd = event_jd_from_datetime(r.event_datetime_utc)
        feats, asp_df = extract_event_features(
            birth_jd=radix.birth_jd,
            event_jd=ejd,
            ticker=ticker,
            universe_row=universe_row,
            radix=radix,
            reaction=r,
        )
        feats["pre_event_volatility"] = pre_event_volatility(ohlc, r.reaction_session)
        if feats.get("pre_event_volatility") and feats["pre_event_volatility"] > 0:
            if feats.get("return_cc") is not None:
                feats["volatility_normalised_return"] = (
                    feats["return_cc"] / feats["pre_event_volatility"]
                )
        event_rows.append(feats)
        if not asp_df.empty:
            aspect_parts.append(asp_df)

    events = pd.DataFrame(event_rows)
    aspects = pd.concat(aspect_parts, ignore_index=True) if aspect_parts else pd.DataFrame()
    meta["valid_events"] = len(events)
    meta["executive"] = radix.executive
    meta["birth_jd"] = radix.birth_jd
    meta["time_convention"] = radix.time_convention
    meta["dob_quality"] = radix.dob_quality
    return events, aspects, meta
