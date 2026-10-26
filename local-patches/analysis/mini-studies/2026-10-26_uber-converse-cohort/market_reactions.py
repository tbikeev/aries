"""Map earnings announcements to NYSE reaction sessions and compute returns."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

import exchange_calendars as xcals
import pandas as pd

NYSE = xcals.get_calendar("XNYS")
NY_TZ = ZoneInfo("America/New_York")

# Converse event time: market open on reaction session (documented assumption).
REACTION_EVENT_TIME = time(9, 30, 0)
REACTION_TIME_PROVENANCE = "NYSE regular session open on mapped reaction day (not press-release time)"


def report_date_key(value: date | str | pd.Timestamp) -> str:
    """Normalize earnings report_date for merges (date objects vs CSV strings)."""
    if isinstance(value, date) and not isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, pd.Timestamp):
        return value.date().isoformat()
    return str(value)[:10]


@dataclass
class OhlcBar:
    session: date
    open: float
    high: float
    low: float
    close: float
    adjusted_close: float
    volume: float | None


@dataclass
class EarningsReaction:
    report_date: date
    fiscal_period_end: date
    timing: str
    reaction_session: date | None
    event_datetime_utc: datetime | None
    excluded: bool
    exclusion_reason: str
    mapping_uncertain: bool
    mapping_note: str
    actual_eps: float | None
    estimate_eps: float | None
    eps_surprise_pct: float | None
    prev_session: date | None = None
    r_gap_pct: float | None = None
    r_cc_pct: float | None = None
    r_intra_pct: float | None = None
    r_2d_pct: float | None = None
    r_5d_pct: float | None = None
    abs_r_cc_pct: float | None = None
    return_sign: int | None = None
    high_vs_prev_pct: float | None = None
    low_vs_prev_pct: float | None = None
    intraday_range_pct: float | None = None
    volume: float | None = None
    volume_ratio_20d: float | None = None
    price_basis: str = "adjusted_close"


def load_ohlc_csv(path: Path, *, price_basis: str = "adjusted_close") -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["date"])
    df = df.sort_values("date").reset_index(drop=True)
    df["session"] = df["date"].dt.date
    if price_basis == "adjusted_close":
        df["px_close"] = df["adjusted_close"].astype(float)
    else:
        df["px_close"] = df["close"].astype(float)
    df["px_open"] = df["open"].astype(float)
    df["px_high"] = df["high"].astype(float)
    df["px_low"] = df["low"].astype(float)
    # Consistency check
    mismatch = (df["close"].astype(float) - df["adjusted_close"].astype(float)).abs().max()
    df.attrs["close_adj_max_diff"] = float(mismatch)
    return df


def _sessions_index(sessions: pd.DatetimeIndex) -> list[date]:
    return [ts.date() for ts in sessions]


def is_trading_session(day: date) -> bool:
    return bool(NYSE.is_session(day))


def next_trading_session(on_or_after: date) -> date | None:
    if NYSE.is_session(on_or_after):
        return on_or_after
    try:
        return NYSE.next_session(on_or_after).date()
    except Exception:
        return None


def next_session_strictly_after(day: date) -> date | None:
    try:
        return NYSE.next_session(day).date()
    except Exception:
        return None


def previous_trading_session(before: date) -> date | None:
    try:
        return NYSE.previous_session(before).date()
    except Exception:
        return None


def map_reaction_session(report_date: date, timing: str) -> tuple[date | None, bool, str]:
    timing_norm = (timing or "").strip().lower()
    uncertain = False
    note = ""
    if timing_norm in ("beforemarket", "before market", "before_market"):
        if is_trading_session(report_date):
            return report_date, uncertain, note
        session = next_trading_session(report_date)
        note = "report_date not a session; used next session"
        return session, uncertain, note
    if timing_norm in ("aftermarket", "after market", "after_market"):
        session = next_session_strictly_after(report_date)
        return session, uncertain, note
    if timing_norm in ("", "unknown", "duringmarket", "during market"):
        uncertain = True
        note = f"timing '{timing}' — defaulting to AfterMarket rule"
        session = map_reaction_session(report_date, "AfterMarket")[0]
        return session, uncertain, note
    uncertain = True
    note = f"unrecognized timing '{timing}' — AfterMarket fallback"
    return map_reaction_session(report_date, "AfterMarket")[0], uncertain, note


def event_utc_from_reaction_session(reaction_session: date) -> datetime:
    local = datetime.combine(reaction_session, REACTION_EVENT_TIME, tzinfo=NY_TZ)
    return local.astimezone(ZoneInfo("UTC"))


def build_reactions(
    earnings_rows: list,
    ohlc: pd.DataFrame,
    *,
    first_trade_session: date | None = None,
) -> list[EarningsReaction]:
    if first_trade_session is None:
        first_trade_session = ohlc["session"].min()
    by_session = {row.session: row for row in _ohlc_rows(ohlc)}
    vol_ma20 = (
        ohlc.set_index("session")["volume"]
        .astype(float)
        .rolling(20, min_periods=5)
        .mean()
    )

    out: list[EarningsReaction] = []
    for er in earnings_rows:
        reaction_session, uncertain, note = map_reaction_session(
            er.report_date, er.before_after_market
        )
        excluded = False
        reason = ""
        if reaction_session is None:
            excluded = True
            reason = "no reaction session on calendar"
        elif reaction_session < first_trade_session:
            excluded = True
            reason = f"reaction session {reaction_session} before first OHLC session {first_trade_session}"
        elif reaction_session not in by_session:
            excluded = True
            reason = f"no OHLC bar for reaction session {reaction_session}"

        event_utc = None
        if reaction_session and not excluded:
            event_utc = event_utc_from_reaction_session(reaction_session)

        rec = EarningsReaction(
            report_date=er.report_date,
            fiscal_period_end=er.fiscal_period_end,
            timing=er.before_after_market,
            reaction_session=reaction_session,
            event_datetime_utc=event_utc,
            excluded=excluded,
            exclusion_reason=reason,
            mapping_uncertain=uncertain,
            mapping_note=note,
            actual_eps=er.actual,
            estimate_eps=er.estimate,
            eps_surprise_pct=er.surprise_pct,
        )
        if not excluded and reaction_session:
            _fill_returns(rec, by_session, vol_ma20)
        out.append(rec)
    return out


def _ohlc_rows(df: pd.DataFrame) -> list[OhlcBar]:
    rows: list[OhlcBar] = []
    for _, r in df.iterrows():
        vol = r.get("volume")
        rows.append(
            OhlcBar(
                session=r["session"],
                open=float(r["px_open"]),
                high=float(r["px_high"]),
                low=float(r["px_low"]),
                close=float(r["px_close"]),
                adjusted_close=float(r["adjusted_close"]),
                volume=float(vol) if pd.notna(vol) else None,
            )
        )
    return rows


def _session_offset(reaction: date, offset: int, sessions: list[date]) -> date | None:
    try:
        idx = sessions.index(reaction)
    except ValueError:
        return None
    j = idx + offset
    if j < 0 or j >= len(sessions):
        return None
    return sessions[j]


def _fill_returns(rec: EarningsReaction, by_session: dict[date, OhlcBar], vol_ma20) -> None:
    sessions = sorted(by_session.keys())
    react = rec.reaction_session
    assert react is not None
    prev = previous_trading_session(react)
    rec.prev_session = prev
    if prev is None or prev not in by_session or react not in by_session:
        return
    b_prev = by_session[prev]
    b_react = by_session[react]
    c0 = b_prev.close
    if c0 == 0:
        return
    rec.r_gap_pct = 100.0 * (b_react.open - c0) / c0
    rec.r_cc_pct = 100.0 * (b_react.close - c0) / c0
    rec.r_intra_pct = 100.0 * (b_react.close - b_react.open) / b_react.open if b_react.open else None
    rec.abs_r_cc_pct = abs(rec.r_cc_pct) if rec.r_cc_pct is not None else None
    rec.return_sign = (1 if rec.r_cc_pct > 0 else (-1 if rec.r_cc_pct < 0 else 0)) if rec.r_cc_pct is not None else None
    rec.high_vs_prev_pct = 100.0 * (b_react.high - c0) / c0
    rec.low_vs_prev_pct = 100.0 * (b_react.low - c0) / c0
    rec.intraday_range_pct = 100.0 * (b_react.high - b_react.low) / c0
    rec.volume = b_react.volume
    ma = float(vol_ma20.loc[react]) if react in vol_ma20.index and pd.notna(vol_ma20.loc[react]) else None
    if ma and ma > 0 and rec.volume is not None:
        rec.volume_ratio_20d = rec.volume / ma

    s1 = _session_offset(react, 1, sessions)
    s4 = _session_offset(react, 4, sessions)
    if s1 and s1 in by_session:
        rec.r_2d_pct = 100.0 * (by_session[s1].close - c0) / c0
    if s4 and s4 in by_session:
        rec.r_5d_pct = 100.0 * (by_session[s4].close - c0) / c0


def reactions_to_dataframe(reactions: list[EarningsReaction]) -> pd.DataFrame:
    df = pd.DataFrame([r.__dict__ for r in reactions])
    if "report_date" in df.columns:
        df["report_date"] = df["report_date"].map(report_date_key)
    if "reaction_session" in df.columns:
        df["reaction_session"] = df["reaction_session"].map(
            lambda v: report_date_key(v) if v is not None and v == v else None
        )
    if "fiscal_period_end" in df.columns:
        df["fiscal_period_end"] = df["fiscal_period_end"].map(report_date_key)
    if "prev_session" in df.columns:
        df["prev_session"] = df["prev_session"].map(
            lambda v: report_date_key(v) if v is not None and v == v else None
        )
    return df
