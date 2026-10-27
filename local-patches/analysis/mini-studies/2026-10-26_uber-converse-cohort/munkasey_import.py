"""Extract FT / INC fields from Munkasey Companies2 workbook (read-only)."""

from __future__ import annotations

import re
from datetime import date, datetime, time, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

# Munkasey main-row layout (Sheet1, verified against UBER / MSFT / AAPL).
COL_SYMBOL = 0
COL_EXCHANGE = 1
COL_FT_DATE = 9
COL_INC_DATE = 6
COL_INC_STATE = 8
COL_FT_TIME = 10
COL_FT_TIME_ALT = 7

DEFAULT_MUNKASEY_XLSX = Path(
    "/Users/thomasbikeev/Library/Mobile Documents/com~apple~CloudDocs/Documents/Munkasey/Companies2 a.xlsx"
)

ET = ZoneInfo("America/New_York")

STATE_TZ: dict[str, str] = {
    "DE": "America/New_York",
    "CA": "America/Los_Angeles",
    "WA": "America/Los_Angeles",
    "TX": "America/Chicago",
}


def _is_main_row(symbol: object) -> bool:
    if not isinstance(symbol, str):
        return False
    s = symbol.strip()
    return bool(s) and s != "- -" and not s.startswith("- -")


def _parse_mdy(value: object) -> date | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, datetime):
        return value.date()
    text = str(value).strip()
    if not text or text in ("- -", "-", "nan"):
        return None
    for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _parse_hhmm(value: object) -> tuple[int, int] | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, str):
        text = value.strip()
        if not text or text in ("- -", "-"):
            return None
        if re.fullmatch(r"\d{3,4}", text):
            n = int(text)
            return n // 100, n % 100
        return None
    try:
        n = int(value)
    except (TypeError, ValueError):
        return None
    if n < 0 or n > 2359:
        return None
    return n // 100, n % 100


def load_munkasey_index(xlsx: Path | None = None) -> dict[str, pd.Series]:
    path = xlsx or DEFAULT_MUNKASEY_XLSX
    if not path.exists():
        raise FileNotFoundError(f"Munkasey workbook not found: {path}")
    df = pd.read_excel(path, sheet_name=0, header=None)
    index: dict[str, pd.Series] = {}
    for _, row in df.iterrows():
        sym = row.iloc[COL_SYMBOL]
        if not _is_main_row(sym):
            continue
        index[str(sym).strip().upper()] = row
    return index


def extract_corporate_fields(ticker: str, *, xlsx: Path | None = None) -> dict:
    """Return FT/INC dates and metadata for one ticker."""
    index = load_munkasey_index(xlsx)
    t = ticker.upper()
    if t not in index:
        return {
            "ticker": t,
            "munkasey_found": False,
            "ft_date": None,
            "inc_date": None,
            "ft_exchange": None,
            "inc_state": None,
            "ft_time_hhmm": None,
            "ft_time_source": None,
        }
    row = index[t]
    ft_date = _parse_mdy(row.iloc[COL_FT_DATE])
    inc_date = _parse_mdy(row.iloc[COL_INC_DATE])
    exch = str(row.iloc[COL_EXCHANGE]).strip() if pd.notna(row.iloc[COL_EXCHANGE]) else ""
    inc_state = str(row.iloc[COL_INC_STATE]).strip() if pd.notna(row.iloc[COL_INC_STATE]) else ""
    hhmm = _parse_hhmm(row.iloc[COL_FT_TIME])
    source = "col10_hhmm"
    if hhmm is None:
        hhmm = _parse_hhmm(row.iloc[COL_FT_TIME_ALT])
        source = "col7_hhmm" if hhmm else None
    return {
        "ticker": t,
        "munkasey_found": True,
        "ft_date": ft_date.isoformat() if ft_date else None,
        "inc_date": inc_date.isoformat() if inc_date else None,
        "ft_exchange": exch,
        "inc_state": inc_state,
        "ft_time_hhmm": f"{hhmm[0]:02d}:{hhmm[1]:02d}" if hhmm else None,
        "ft_time_source": source,
    }


def build_universe_v2(
    ceo_csv: Path,
    *,
    xlsx: Path | None = None,
    out_csv: Path,
) -> pd.DataFrame:
    """Merge CEO universe with Munkasey FT/INC columns."""
    base = pd.read_csv(ceo_csv)
    base["ticker"] = base["ticker"].astype(str).str.upper().str.strip()
    corp_rows = []
    for t in base["ticker"]:
        corp_rows.append(extract_corporate_fields(t, xlsx=xlsx))
    corp = pd.DataFrame(corp_rows)
    merged = base.merge(corp, on="ticker", how="left")
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(out_csv, index=False)
    return merged
