"""Eligible ticker × event panel with returns and frozen features."""

from __future__ import annotations

from datetime import date

import pandas as pd

from brazil_historical import trading_session_jd
from brazil_paths import UNIVERSE_TICKERS, YAHOO_SYMBOL_OVERRIDE
from br2_features import frozen_feature_bundle
from ft_registry import approximate_ft_jd_noon, build_registry, ft_birth_jd, _parse_ft_date


def _company_return_map(ticker: str, sessions: list[date]) -> dict[date, float]:
    import yfinance as yf

    if not sessions:
        return {}
    ysym = YAHOO_SYMBOL_OVERRIDE.get(ticker, ticker)
    start = min(sessions).isoformat()
    end = (max(sessions).toordinal() + 5)
    end_d = date.fromordinal(end).isoformat()
    df = yf.download(ysym, start=start, end=end_d, progress=False, auto_adjust=False)
    if df.empty:
        return {}
    if isinstance(df.columns, pd.MultiIndex):
        df = df.droplevel(1, axis=1)
    df = df.reset_index()
    df["d"] = pd.to_datetime(df["Date"]).dt.date
    df = df.sort_values("d")
    df["ret"] = 100.0 * df["Close"].pct_change()
    return {r["d"]: float(r["ret"]) for _, r in df.iterrows() if pd.notna(r["ret"])}


def resolve_ft_jd(row: pd.Series) -> tuple[float | None, bool, str]:
    jd, strict = ft_birth_jd(row)
    if strict and jd is not None:
        return jd, True, "strict"
    ajd = approximate_ft_jd_noon(row)
    if ajd is not None:
        return ajd, False, "approx_noon"
    return None, False, "missing"


def build_eligible_panel(shocks: pd.DataFrame, *, use_cache: bool = True) -> pd.DataFrame:
    reg = build_registry()
    event_dates = [date.fromisoformat(str(d)) for d in shocks["event_date"].unique()]
    ret_cache: dict[str, dict[date, float]] = {}
    rows = []
    for _, srow in shocks.iterrows():
        ed = date.fromisoformat(str(srow["event_date"]))
        ewz_r = float(srow["ewz_return_cc_pct"])
        for _, trow in reg.iterrows():
            ticker = trow["ticker"]
            ft_d = _parse_ft_date(trow.get("ft_date"))
            if ft_d is None or ft_d >= ed:
                continue
            ft_jd, strict, conv = resolve_ft_jd(trow)
            if ft_jd is None:
                continue
            if ticker not in ret_cache:
                ret_cache[ticker] = _company_return_map(ticker, event_dates)
            cr = ret_cache[ticker].get(ed)
            if cr is None:
                continue
            ejd = trading_session_jd(ed)
            feats = frozen_feature_bundle(ft_jd, ejd, use_cache=use_cache)
            rows.append(
                {
                    "ticker": ticker,
                    "event_date": str(ed),
                    "episode_id": srow.get("episode_id"),
                    "discovery_only": bool(srow.get("discovery_only", False)),
                    "validation_eligible": bool(srow.get("validation_eligible", True)),
                    "strict_ft_timestamp": strict,
                    "ft_time_convention": conv,
                    "ewz_return_cc_pct": ewz_r,
                    "company_return_cc_pct": cr,
                    "return_abnormal_pp": cr - ewz_r,
                    **{
                        k: v
                        for k, v in feats.items()
                        if k.endswith("_count") or k.startswith("min_") or k.startswith("c2c_mars")
                    },
                }
            )
    return pd.DataFrame(rows)


STABLE_SUBUNIVERSE = ("ITUB", "BBD", "PBR", "VALE", "ABEV")
