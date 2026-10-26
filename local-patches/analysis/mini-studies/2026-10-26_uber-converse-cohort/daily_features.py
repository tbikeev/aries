"""Frozen converse feature columns for each trading session."""

from __future__ import annotations

from datetime import date, datetime, timezone

import pandas as pd

from earnings_converse import converse_count_features, event_jd_from_datetime, slow_body_active_signatures
from earnings_paths import FROZEN_ORB_THRESHOLDS_DEG

COHORTS = ("FT", "INC", "DK")


def _parse_session(s: str) -> date:
    return date.fromisoformat(str(s)[:10])


def _event_jd_for_session(session: date) -> float:
    from daily_market import session_open_utc_fixed

    dt = session_open_utc_fixed(session)
    return event_jd_from_datetime(dt)


def compute_daily_features(
    panel: pd.DataFrame,
    *,
    progress_every: int = 250,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Returns:
      feature_panel: one row per session with frozen count columns
      slow_active_long: long format (session, signature, orb) for episode builder
    """
    rows: list[dict] = []
    slow_rows: list[dict] = []
    n = len(panel)
    for _, rec in panel.iterrows():
        sess = _parse_session(rec["session"])
        ejd = _event_jd_for_session(sess)
        row: dict = {"session": rec["session"]}
        for orb in FROZEN_ORB_THRESHOLDS_DEG:
            tag = "orb" + str(orb).replace(".", "")
            total_tight = 0
            for rk in COHORTS:
                counts = converse_count_features(rk, ejd, orb_max=orb)
                row[f"{rk}_sq_count_{tag}"] = counts["sq_count"]
                row[f"{rk}_tight_count_{tag}"] = counts["tight_aspect_count"]
                total_tight += counts["tight_aspect_count"]
            row[f"tight_aspect_count_{tag}"] = total_tight
            if orb == 1.0:
                for rk in COHORTS:
                    for sig, orb_val in slow_body_active_signatures(rk, ejd, orb_max=orb):
                        slow_rows.append(
                            {
                                "session": rec["session"],
                                "radix_key": rk,
                                "signature": sig,
                                "best_orb": orb_val,
                            }
                        )
        rows.append(row)
        if progress_every and len(rows) % progress_every == 0:
            print(f"daily features: {len(rows)}/{n}", flush=True)
    return pd.DataFrame(rows), pd.DataFrame(slow_rows)
