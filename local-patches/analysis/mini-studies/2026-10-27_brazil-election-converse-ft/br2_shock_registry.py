"""Historical Brazil shock registries (identified + systematic EWZ extremes)."""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from brazil_paths import (
    BR2_EPISODE_GAP_TRADING_DAYS,
    BR2_SYSTEMATIC_TOP_N,
    DISCOVERY_EVENT_DATE,
)

IDENTIFIED_SHOCKS: list[dict] = [
    {"event_date": "2017-05-18", "direction_hint": "crash", "reason": "Brazilian political crisis (Temer tape)", "source": "identified"},
    {"event_date": "2018-10-02", "direction_hint": "rally", "reason": "Election-related rally", "source": "identified"},
    {"event_date": "2020-03-09", "direction_hint": "crash", "reason": "COVID/oil shock", "source": "identified", "episode_group": "covid-2020-03"},
    {"event_date": "2020-03-12", "direction_hint": "crash", "reason": "COVID crash", "source": "identified", "episode_group": "covid-2020-03"},
    {"event_date": "2020-03-16", "direction_hint": "crash", "reason": "COVID crash", "source": "identified", "episode_group": "covid-2020-03"},
    {"event_date": "2020-03-24", "direction_hint": "rally", "reason": "COVID rebound", "source": "identified", "episode_group": "covid-2020-03-rebound"},
    {"event_date": "2022-10-03", "direction_hint": "rally", "reason": "First-round election rally", "source": "identified", "episode_group": "brazil-election-2022"},
    {"event_date": "2026-10-05", "direction_hint": "rally", "reason": "First-round election rally", "source": "identified", "episode_group": "brazil-election-2026"},
    {
        "event_date": "2026-10-26",
        "direction_hint": "crash",
        "reason": "Second-round election crash (discovery)",
        "source": "identified",
        "episode_group": "brazil-election-2026",
        "discovery_only": True,
    },
]


def load_ewz_daily(*, end: str = "2026-11-05") -> pd.DataFrame:
    import yfinance as yf

    df = yf.download("EWZ", start="2000-01-01", end=end, progress=False, auto_adjust=False)
    if isinstance(df.columns, pd.MultiIndex):
        df = df.droplevel(1, axis=1)
    df = df.reset_index()
    df["event_date"] = pd.to_datetime(df["Date"]).dt.date
    df = df.sort_values("event_date")
    df["ewz_prev_close"] = df["Close"].shift(1)
    df["ewz_return_cc_pct"] = 100.0 * (df["Close"] / df["ewz_prev_close"] - 1.0)
    df["ewz_abs_return_cc_pct"] = df["ewz_return_cc_pct"].abs()
    vol = df["ewz_return_cc_pct"].rolling(60, min_periods=20).std()
    df["ewz_vol_std_60d"] = vol
    df["ewz_return_zscore"] = df["ewz_return_cc_pct"] / vol
    return df


def _direction_from_return(r: float) -> str:
    if r > 0.05:
        return "rally"
    if r < -0.05:
        return "crash"
    return "mixed"


def build_identified_registry(ewz: pd.DataFrame) -> pd.DataFrame:
    by = {r["event_date"]: r for _, r in ewz.iterrows()}
    rows = []
    for spec in IDENTIFIED_SHOCKS:
        d = date.fromisoformat(spec["event_date"])
        r = by.get(d)
        if r is None or pd.isna(r.get("ewz_return_cc_pct")):
            rows.append({**spec, "verified": False, "ewz_return_cc_pct": None, "direction_verified": None})
            continue
        ret = float(r["ewz_return_cc_pct"])
        rows.append(
            {
                **spec,
                "verified": True,
                "ewz_return_cc_pct": ret,
                "direction_verified": _direction_from_return(ret),
                "ewz_data_source": "yfinance_unadj_close",
            }
        )
    return pd.DataFrame(rows)


def _systematic_picks(ewz: pd.DataFrame, *, top_n: int) -> pd.DataFrame:
    valid = ewz.dropna(subset=["ewz_return_cc_pct"]).copy()
    crashes_raw = valid.nsmallest(top_n, "ewz_return_cc_pct")
    rallies_raw = valid.nlargest(top_n, "ewz_return_cc_pct")
    crashes_z = valid.dropna(subset=["ewz_return_zscore"]).nsmallest(top_n, "ewz_return_zscore")
    rallies_z = valid.dropna(subset=["ewz_return_zscore"]).nlargest(top_n, "ewz_return_zscore")

    def tag(df, method, direction):
        out = df[["event_date", "ewz_return_cc_pct", "ewz_return_zscore"]].copy()
        out["selection_method"] = method
        out["direction_hint"] = direction
        out["source"] = "systematic"
        out["reason"] = f"EWZ {direction} ({method})"
        return out

    parts = [
        tag(crashes_raw, "raw_return_top30_crash", "crash"),
        tag(rallies_raw, "raw_return_top30_rally", "rally"),
        tag(crashes_z, "vol_standardized_top30_crash", "crash"),
        tag(rallies_z, "vol_standardized_top30_rally", "rally"),
    ]
    merged = pd.concat(parts, ignore_index=True)
    merged["event_date"] = merged["event_date"].astype(str)
    merged = merged.drop_duplicates(subset=["event_date"], keep="first")
    merged["verified"] = True
    merged["direction_verified"] = merged["ewz_return_cc_pct"].apply(_direction_from_return)
    merged["ewz_data_source"] = "yfinance_unadj_close"
    return merged


def assign_episode_ids(shocks: pd.DataFrame, ewz: pd.DataFrame) -> pd.DataFrame:
    """Cluster adjacent trading days with same sign into episodes."""
    df = shocks.copy()
    df["episode_group"] = df.get("episode_group", pd.Series([None] * len(df)))
    df["event_date_parsed"] = pd.to_datetime(df["event_date"]).dt.date
    trading = ewz["event_date"].tolist()
    idx = {d: i for i, d in enumerate(trading)}

    episode_ids = []
    prev_d = None
    prev_sign = None
    current_ep = None
    ep_counter = 0
    for _, row in df.sort_values("event_date_parsed").iterrows():
        if pd.notna(row["episode_group"]) and str(row["episode_group"]).strip():
            episode_ids.append(str(row["episode_group"]))
            prev_d = row["event_date_parsed"]
            prev_sign = np.sign(row.get("ewz_return_cc_pct") or 0)
            current_ep = str(row["episode_group"])
            continue
        d = row["event_date_parsed"]
        sign = np.sign(row.get("ewz_return_cc_pct") or 0)
        gap = 999
        if prev_d is not None and d in idx and prev_d in idx:
            gap = abs(idx[d] - idx[prev_d])
        if current_ep is None or sign != prev_sign or gap > BR2_EPISODE_GAP_TRADING_DAYS:
            ep_counter += 1
            current_ep = f"auto_ep_{row['event_date']}_{ep_counter}"
        episode_ids.append(current_ep)
        prev_d, prev_sign = d, sign
    df = df.sort_values("event_date_parsed")
    df["episode_id"] = episode_ids
    if "discovery_only" not in df.columns:
        df["discovery_only"] = False
    df["discovery_only"] = df["discovery_only"].fillna(False).astype(bool)
    df["validation_eligible"] = (df["event_date"].astype(str) != str(DISCOVERY_EVENT_DATE)) & df["verified"]
    return df.drop(columns=["event_date_parsed"], errors="ignore")


def build_historical_shock_registry() -> tuple[pd.DataFrame, pd.DataFrame]:
    ewz = load_ewz_daily()
    idf = build_identified_registry(ewz)
    sysdf = _systematic_picks(ewz, top_n=BR2_SYSTEMATIC_TOP_N)
    # Union: identified verified + systematic not already in identified dates
    id_dates = set(idf[idf["verified"]]["event_date"].astype(str))
    sys_extra = sysdf[~sysdf["event_date"].isin(id_dates)]
    combined = pd.concat([idf, sys_extra], ignore_index=True)
    combined = combined[combined["verified"] == True].copy()  # noqa: E712
    combined = combined.sort_values("event_date").drop_duplicates(subset=["event_date"], keep="first")
    combined = assign_episode_ids(combined, ewz)

    episodes = (
        combined.groupby("episode_id", as_index=False)
        .agg(
            episode_start=("event_date", "min"),
            episode_end=("event_date", "max"),
            n_days=("event_date", "count"),
            min_ewz_return=("ewz_return_cc_pct", "min"),
            max_ewz_return=("ewz_return_cc_pct", "max"),
            discovery_only=("discovery_only", "max"),
            validation_eligible=("validation_eligible", "min"),
        )
    )
    return combined, episodes
