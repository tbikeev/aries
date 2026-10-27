"""Historical C2C/C2R percentile ranks (prior sessions only, midrank)."""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from brazil_historical import trading_session_jd
from brazil_paths import BR2_HISTORICAL_MIN_SESSIONS, YAHOO_SYMBOL_OVERRIDE
from br2_features import frozen_feature_bundle
from ft_registry import build_registry
from br2_panel import resolve_ft_jd


def _midrank_percentile(value: float, history: list[float]) -> float:
    if not history:
        return float("nan")
    arr = np.asarray(history, dtype=float)
    below = np.sum(arr < value - 1e-12)
    equal = np.sum(np.abs(arr - value) <= 1e-12)
    return float((below + 0.5 * equal + 1) / (len(arr) + 1))


def _load_trading_dates(yahoo_symbol: str, before: date) -> list[date]:
    import yfinance as yf

    start = date(before.year - 10, 1, 1)
    df = yf.download(
        yahoo_symbol,
        start=start.isoformat(),
        end=before.isoformat(),
        progress=False,
        auto_adjust=False,
    )
    if df.empty:
        return []
    if isinstance(df.columns, pd.MultiIndex):
        df = df.droplevel(1, axis=1)
    df = df.reset_index()
    return [d for d in pd.to_datetime(df["Date"]).dt.date.tolist() if d < before]


def build_historical_percentiles(panel: pd.DataFrame, *, use_cache: bool = True) -> pd.DataFrame:
    reg = build_registry().set_index("ticker")
    rows = []
    for ticker, tgrp in panel.groupby("ticker"):
        trow = reg.loc[ticker]
        ft_jd, strict, _ = resolve_ft_jd(trow)
        if ft_jd is None:
            continue
        ysym = YAHOO_SYMBOL_OVERRIDE.get(ticker, ticker)
        events = sorted(tgrp["event_date"].unique())
        if not events:
            continue
        last_ed = date.fromisoformat(events[-1])
        all_dates = _load_trading_dates(ysym, last_ed)
        if not all_dates:
            continue
        # Incremental history: only sessions strictly before each event.
        hist_counts: dict[str, list[float]] = {
            "c2c_sq": [],
            "c2c_sq_opp": [],
            "c2c_hard": [],
            "c2r_hard": [],
        }
        date_ptr = 0
        for ed_str in events:
            ed = date.fromisoformat(ed_str)
            while date_ptr < len(all_dates) and all_dates[date_ptr] < ed:
                d = all_dates[date_ptr]
                f = frozen_feature_bundle(ft_jd, trading_session_jd(d), use_cache=use_cache)
                hist_counts["c2c_sq"].append(float(f["c2c_sq_count"]))
                hist_counts["c2c_sq_opp"].append(float(f["c2c_sq_opp_count"]))
                hist_counts["c2c_hard"].append(float(f["c2c_hard_count"]))
                hist_counts["c2r_hard"].append(float(f["c2r_hard_count"]))
                date_ptr += 1
            # Use trailing window for reference (prior only, capped at min_sessions).
            n_use = min(BR2_HISTORICAL_MIN_SESSIONS, len(hist_counts["c2c_hard"]))
            ref = {k: v[-n_use:] if n_use else [] for k, v in hist_counts.items()}
            obs = frozen_feature_bundle(ft_jd, trading_session_jd(ed), use_cache=use_cache)
            rows.append(
                {
                    "ticker": ticker,
                    "event_date": ed_str,
                    "strict_ft_timestamp": strict,
                    "historical_n_sessions": n_use,
                    "pct_c2c_sq": _midrank_percentile(obs["c2c_sq_count"], ref["c2c_sq"]),
                    "pct_c2c_sq_opp": _midrank_percentile(obs["c2c_sq_opp_count"], ref["c2c_sq_opp"]),
                    "pct_c2c_hard": _midrank_percentile(obs["c2c_hard_count"], ref["c2c_hard"]),
                    "pct_c2r_hard": _midrank_percentile(obs["c2r_hard_count"], ref["c2r_hard"]),
                }
            )
    return pd.DataFrame(rows)
