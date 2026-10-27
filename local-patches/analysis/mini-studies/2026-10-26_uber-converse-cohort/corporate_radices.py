"""FT and INC radix JD from v2 universe + Munkasey fields."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

from converse import utc_to_jd

ET = ZoneInfo("America/New_York")
UTC = timezone.utc

# Delaware incorporation proxy (same as UBER INC study).
DE_LAT = 39.0 + 2 / 60.0 + 45 / 3600.0
DE_LON = -(75.0 + 29 / 60.0 + 32 / 3600.0)
NYSE_LAT = 40.7128
NYSE_LON = -74.0060

STATE_TZ: dict[str, str] = {
    "DE": "America/New_York",
    "CA": "America/Los_Angeles",
    "WA": "America/Los_Angeles",
    "TX": "America/Chicago",
    "NY": "America/New_York",
}


@dataclass(frozen=True)
class CompanyRadix:
    ticker: str
    radix_kind: str  # CEO | FT | INC
    label: str
    birth_jd: float
    time_convention: str
    timezone_used: str
    birth_time_uncertain: bool
    quality_note: str
    source_date: str | None = None


def _parse_iso(d: str | None) -> date | None:
    if not d or str(d).strip() in ("", "nan"):
        return None
    y, m, day = str(d).strip()[:10].split("-")
    return date(int(y), int(m), int(day))


def _parse_hhmm(text: str | None) -> tuple[int, int] | None:
    if not text or str(text).strip() in ("", "nan"):
        return None
    parts = str(text).strip().split(":")
    if len(parts) != 2:
        return None
    return int(parts[0]), int(parts[1])


def _jd_from_local(d: date, hh: int, mm: int, tz_name: str) -> tuple[float, str]:
    tz = ZoneInfo(tz_name)
    local = datetime.combine(d, time(hh, mm, 0), tzinfo=tz)
    utc = local.astimezone(UTC)
    jd = utc_to_jd(utc.year, utc.month, utc.day, utc.hour, utc.minute, utc.second)
    return jd, tz_name


def build_ft_radix(row) -> CompanyRadix | None:
    d = _parse_iso(row.get("ft_date"))
    if d is None:
        return None
    hhmm = _parse_hhmm(row.get("ft_time_hhmm"))
    exch = str(row.get("ft_exchange") or "").strip().upper()
    if hhmm:
        hh, mm = hhmm
        convention = f"first_trade_time_munkasey_{row.get('ft_time_source') or 'hhmm'}"
        uncertain = False
    else:
        hh, mm = 9, 30
        convention = "first_trade_exchange_open_default_0930_et"
        uncertain = True
    jd, tz = _jd_from_local(d, hh, mm, "America/New_York")
    note = f"Exchange code {exch or '?'}; FT date from Munkasey col9; angles/houses excluded."
    if uncertain:
        note += " FT clock unknown — 09:30 ET placeholder."
    return CompanyRadix(
        ticker=str(row["ticker"]).upper(),
        radix_kind="FT",
        label=f"{row['ticker']} first trade",
        birth_jd=jd,
        time_convention=convention,
        timezone_used=tz,
        birth_time_uncertain=uncertain,
        quality_note=note,
        source_date=row.get("ft_date"),
    )


def build_inc_radix(row) -> CompanyRadix | None:
    d = _parse_iso(row.get("inc_date"))
    if d is None:
        return None
    state = str(row.get("inc_state") or "").strip().upper()
    if state in STATE_TZ:
        tz_name = STATE_TZ[state]
        jd, tz_used = _jd_from_local(d, 12, 0, tz_name)
        convention = f"incorporation_noon_local_{state}"
    else:
        utc = datetime.combine(d, time(12, 0, 0), tzinfo=UTC)
        jd = utc_to_jd(utc.year, utc.month, utc.day, utc.hour, utc.minute, utc.second)
        tz_used = "UTC"
        convention = "incorporation_noon_utc_fallback"
    note = (
        f"Incorporation date Munkasey col6; state={state or '?'}. "
        "Birth time unknown — noon civil convention; angles/houses excluded."
    )
    return CompanyRadix(
        ticker=str(row["ticker"]).upper(),
        radix_kind="INC",
        label=f"{row['ticker']} incorporation",
        birth_jd=jd,
        time_convention=convention,
        timezone_used=tz_used,
        birth_time_uncertain=True,
        quality_note=note,
        source_date=row.get("inc_date"),
    )
