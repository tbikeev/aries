"""Daily panel smoke tests."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

STUDY = Path(__file__).resolve().parents[1]
ROOT = STUDY.parents[3]
sys.path[:0] = [str(STUDY), str(ROOT), str(ROOT / "SWEP" / "src")]

from daily_market import build_daily_panel, session_open_utc_fixed  # noqa: E402
from earnings_converse import converse_count_features, event_jd_from_datetime  # noqa: E402
from earnings_paths import resolve_ohlc_csv  # noqa: E402
from market_reactions import load_ohlc_csv  # noqa: E402


def test_daily_panel_has_returns() -> None:
    ohlc = load_ohlc_csv(resolve_ohlc_csv())
    panel = build_daily_panel(ohlc)
    assert len(panel) > 1000
    assert panel["r_cc_pct"].notna().all()


def test_converse_counts_deterministic() -> None:
    dt = session_open_utc_fixed(date(2022, 8, 2))
    ejd = event_jd_from_datetime(dt)
    a = converse_count_features("DK", ejd, orb_max=1.0)
    b = converse_count_features("DK", ejd, orb_max=1.0)
    assert a == b
    assert "sq_count" in a
