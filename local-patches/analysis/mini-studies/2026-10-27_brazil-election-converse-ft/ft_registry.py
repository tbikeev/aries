"""Build universe_ft_registry.csv from Munkasey + documented overrides."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

import pandas as pd

from brazil_paths import (
    MUNKASEY_SYMBOL_OVERRIDE,
    MUNKASEY_XLSX,
    UNIVERSE_TICKERS,
    YAHOO_SYMBOL_OVERRIDE,
)

ET = ZoneInfo("America/New_York")
NYSE_LAT, NYSE_LON = 40.7128, -74.0060


def _parse_ft_date(dstr: object) -> date | None:
    if dstr is None or (isinstance(dstr, float) and pd.isna(dstr)):
        return None
    if isinstance(dstr, date) and not isinstance(dstr, datetime):
        return dstr
    text = str(dstr).strip()[:10]
    if not text or text.lower() in ("nan", "none"):
        return None
    y, m, d = text.split("-")
    return date(int(y), int(m), int(d))

# Manual FT rows when Munkasey missing (document sources in notes).
MANUAL_FT: dict[str, dict] = {
    "EBR": {
        "company": "Centrais Eletricas Brasileiras S.A. – Eletrobras (ADR)",
        "instrument_type": "ADR",
        "exchange": "NYSE",
        "ft_date": None,
        "ft_time_hhmm": None,
        "ft_timezone": "America/New_York",
        "ft_place": "NYSE, New York",
        "ft_source": "Munkasey not indexed; FT timestamp required before strict analysis",
        "ft_confidence": "missing",
        "notes": "Include in universe; exclude from strict-timestamp cohort until sourced.",
    },
}


@dataclass
class FtRadix:
    ticker: str
    birth_jd: float
    ft_datetime_utc: str
    strict_timestamp: bool


def build_registry() -> pd.DataFrame:
    from brazil_paths import STUDY_ROOT
    import sys

    sys.path.insert(0, str(STUDY_ROOT.parent / "2026-10-26_uber-converse-cohort"))
    from munkasey_import import extract_corporate_fields, load_munkasey_index

    index = load_munkasey_index(MUNKASEY_XLSX) if MUNKASEY_XLSX.exists() else {}

    rows = []
    for ticker in UNIVERSE_TICKERS:
        mkey = MUNKASEY_SYMBOL_OVERRIDE.get(ticker, ticker)
        m = extract_corporate_fields(mkey, xlsx=MUNKASEY_XLSX)
        manual = MANUAL_FT.get(ticker, {})
        ft_date = m.get("ft_date") or manual.get("ft_date")
        ft_time = m.get("ft_time_hhmm") or manual.get("ft_time_hhmm")
        strict = bool(ft_date and ft_time)
        if ft_date and not ft_time:
            strict = False
        company = manual.get("company") or ""
        if not company and mkey in index:
            row = index[mkey]
            if len(row) > 2 and pd.notna(row.iloc[2]):
                company = str(row.iloc[2]).strip()
        rows.append(
            {
                "ticker": ticker,
                "yahoo_symbol": YAHOO_SYMBOL_OVERRIDE.get(ticker, ticker),
                "munkasey_symbol": mkey,
                "company": company,
                "instrument_type": manual.get("instrument_type", "ADR"),
                "exchange": m.get("ft_exchange") or manual.get("exchange", ""),
                "ft_date": ft_date,
                "ft_time_hhmm": ft_time,
                "ft_timezone": "America/New_York",
                "ft_place": manual.get("ft_place", "US listing venue"),
                "ft_source": "Munkasey Companies2 col9/col10"
                if m.get("munkasey_found")
                else manual.get("ft_source", ""),
                "ft_confidence": "munkasey_hhmm" if ft_time else ("missing_time" if ft_date else "missing"),
                "strict_timestamp_eligible": strict,
                "munkasey_found": m.get("munkasey_found", False),
                "data_quality_flags": ";".join(
                    f
                    for f in [
                        "no_munkasey" if not m.get("munkasey_found") and ticker not in MANUAL_FT else "",
                        "no_ft_time" if ft_date and not ft_time else "",
                        "no_ft_date" if not ft_date else "",
                        "yahoo_alias" if ticker in YAHOO_SYMBOL_OVERRIDE else "",
                    ]
                    if f
                ),
            }
        )
    return pd.DataFrame(rows)


def ft_birth_jd(row: pd.Series) -> tuple[float | None, bool]:
    """Return (jd_ut, strict_ok). Uses exact Munkasey time when present; never 09:30 default."""
    import sys

    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent / "2026-10-26_uber-converse-cohort"))
    from converse import utc_to_jd

    d0 = _parse_ft_date(row.get("ft_date"))
    tstr = row.get("ft_time_hhmm")
    if d0 is None:
        return None, False
    if not tstr or str(tstr) in ("", "nan", "None"):
        return None, False
    hh, mm = str(tstr).split(":")
    local = datetime.combine(d0, time(int(hh), int(mm), 0), tzinfo=ET)
    utc = local.astimezone(timezone.utc)
    jd = utc_to_jd(utc.year, utc.month, utc.day, utc.hour, utc.minute, utc.second)
    return jd, True


def approximate_ft_jd_noon(row: pd.Series) -> float | None:
    """Sensitivity only: noon ET on FT date when time missing."""
    import sys

    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent / "2026-10-26_uber-converse-cohort"))
    from converse import utc_to_jd

    d0 = _parse_ft_date(row.get("ft_date"))
    if d0 is None:
        return None
    local = datetime.combine(d0, time(12, 0), tzinfo=ET)
    utc = local.astimezone(timezone.utc)
    return utc_to_jd(utc.year, utc.month, utc.day, utc.hour, utc.minute, utc.second)
