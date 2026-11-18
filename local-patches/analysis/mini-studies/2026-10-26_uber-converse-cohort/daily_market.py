"""Daily UBER session panel (returns at 09:30 ET converse anchor)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from market_reactions import (
    NY_TZ,
    REACTION_EVENT_TIME,
    REACTION_TIME_PROVENANCE,
    load_ohlc_csv,
    previous_trading_session,
)

FORWARD_EMBARGO_SESSIONS = 5


@dataclass
class DailySession:
    session: date
    event_datetime_utc: datetime
    prev_session: date | None
    r_cc_pct: float | None
    r_gap_pct: float | None
    r_intra_pct: float | None
    r_2d_pct: float | None
    r_5d_pct: float | None
    abs_r_cc_pct: float | None
    return_sign: int | None
    volume_ratio_20d: float | None


def session_open_utc_fixed(session: date) -> datetime:
    from datetime import timezone

    local = datetime.combine(session, REACTION_EVENT_TIME, tzinfo=NY_TZ)
    return local.astimezone(timezone.utc)


def build_daily_panel(ohlc: pd.DataFrame) -> pd.DataFrame:
    """One row per OHLC session with CC/gap/intra and forward returns."""
    by = {r["session"]: r for _, r in ohlc.iterrows()}
    sessions = sorted(by.keys())
    vol = ohlc.set_index("session")["volume"].astype(float)
    vol_ma20 = vol.rolling(20, min_periods=10).mean()

    rows: list[dict] = []
    for i, sess in enumerate(sessions):
        prev = previous_trading_session(sess)
        if prev is None or prev not in by:
            continue
        b_prev = by[prev]
        b = by[sess]
        c0 = float(b_prev["px_close"])
        if c0 == 0:
            continue
        o = float(b["px_open"])
        c = float(b["px_close"])
        r_gap = 100.0 * (o - c0) / c0
        r_cc = 100.0 * (c - c0) / c0
        r_intra = 100.0 * (c - o) / o if o else None
        r2 = r5 = None
        if i + 1 < len(sessions):
            s1 = sessions[i + 1]
            if s1 in by:
                r2 = 100.0 * (float(by[s1]["px_close"]) - c0) / c0
        if i + 4 < len(sessions):
            s4 = sessions[i + 4]
            if s4 in by:
                r5 = 100.0 * (float(by[s4]["px_close"]) - c0) / c0
        vr = None
        v = b.get("volume")
        if v is not None and pd.notna(v) and sess in vol_ma20.index:
            ma = float(vol_ma20.loc[sess])
            if ma > 0:
                vr = float(v) / ma
        rows.append(
            {
                "session": sess.isoformat(),
                "event_datetime_utc": session_open_utc_fixed(sess).isoformat(),
                "prev_session": prev.isoformat(),
                "r_cc_pct": r_cc,
                "r_gap_pct": r_gap,
                "r_intra_pct": r_intra,
                "r_2d_pct": r2,
                "r_5d_pct": r5,
                "abs_r_cc_pct": abs(r_cc),
                "return_sign": 1 if r_cc > 0 else (-1 if r_cc < 0 else 0),
                "volume_ratio_20d": vr,
                "converse_time_provenance": REACTION_TIME_PROVENANCE,
            }
        )
    return pd.DataFrame(rows)


def load_earnings_reaction_sessions(path: Path) -> set[str]:
    if not path.exists():
        return set()
    df = pd.read_csv(path)
    if "excluded" in df.columns:
        df = df[~df["excluded"].astype(bool)]
    col = "reaction_session"
    return set(df[col].astype(str).str[:10])
