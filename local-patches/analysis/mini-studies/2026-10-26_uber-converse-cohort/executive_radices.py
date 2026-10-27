"""CEO radix charts from universe CSV (fixed noon conventions)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

from converse import utc_to_jd
from radix import ChartSpec

# Documented birthplaces for 12:00 local civil time where we have a defensible zone.
# Others use noon UTC fallback (explicitly flagged).
BIRTHPLACE_TZ: dict[str, tuple[str, str]] = {
    # ticker -> (Iana TZ, note)
    "MSFT": ("Asia/Kolkata", "Satya Nadella — Hyderabad area; India no DST"),
    "AAPL": ("America/Chicago", "Tim Cook — Alabama"),
    "NVDA": ("Asia/Taipei", "Jensen Huang — Taiwan"),
    "GOOGL": ("Asia/Kolkata", "Sundar Pichai — Chennai area"),
    "META": ("America/New_York", "Mark Zuckerberg — New York"),
    "AMZN": ("America/New_York", "Andy Jassy — New York"),
    "CRM": ("America/Los_Angeles", "Marc Benioff — California"),
    "AMD": ("America/New_York", "Lisa Su — Taiwan-born; US career — NYC proxy weak"),
    "ADBE": ("Asia/Kolkata", "Shantanu Narayen — Hyderabad"),
    "DELL": ("America/Chicago", "Michael Dell — Texas"),
    "UBER": ("Asia/Tehran", "Dara Khosrowshahi — matches existing UBER DK study"),
    "ABNB": ("America/New_York", "Brian Chesky — New York"),
    "TSLA": ("Africa/Johannesburg", "Elon Musk — Pretoria"),
    "DIS": ("America/New_York", "Bob Iger — New York"),
    "WMT": ("America/Chicago", "Doug McMillon — Arkansas"),
    "NFLX": ("America/Los_Angeles", "Reed Hastings — Boston → CA career"),
    "SPOT": ("Europe/Stockholm", "Daniel Ek — Sweden"),
    "CMCSA": ("America/New_York", "Brian Roberts — Pennsylvania"),
    "MCD": ("America/Chicago", "Chris Kempczinski — Chicago area"),
    "SBUX": ("America/New_York", "Howard Schultz — New York"),
    "RBLX": ("America/Los_Angeles", "David Baszucki — California"),
    "F": ("America/Detroit", "Jim Farley — Michigan"),
    "GM": ("America/Detroit", "Mary Barra — Michigan"),
    "DAL": ("America/New_York", "Ed Bastian — Georgia"),
    "FDX": ("America/New_York", "Fred Smith — Mississippi"),
    "BA": ("America/New_York", "Dave Calhoun — Pennsylvania"),
    "LMT": ("America/New_York", "Marillyn Hewson — Alabama"),
    "TM": ("Asia/Tokyo", "Akio Toyoda — Japan"),
    "STLA": ("Europe/Lisbon", "Carlos Tavares — Portugal"),
    "UAL": ("America/Chicago", "Oscar Munoz — California"),
    "LUV": ("America/Chicago", "Gary Kelly — Texas"),
    "JPM": ("America/New_York", "Jamie Dimon — New York"),
    "BAC": ("America/New_York", "Brian Moynihan — Ohio"),
    "BLK": ("America/New_York", "Larry Fink — California"),
    "COIN": ("America/Los_Angeles", "Brian Armstrong — California"),
    "HOOD": ("America/New_York", "Vlad Tenev — Bulgaria → US; weak"),
    "PFE": ("Europe/Athens", "Albert Bourla — Greece"),
    "BNTX": ("Europe/Berlin", "Uğur Şahin — Germany"),
    "MRNA": ("Europe/Paris", "Stéphane Bancel — France"),
    "MS": ("America/New_York", "James Gorman — England → US; NYC proxy"),
    "UNH": ("Europe/London", "Andrew Witty — UK"),
}


@dataclass(frozen=True)
class ExecutiveRadix:
    ticker: str
    executive: str
    dob: date
    birth_jd: float
    time_convention: str
    timezone_used: str
    birth_time_uncertain: bool = True
    dob_quality: str = ""
    notes: str = ""

    def chart_spec(self) -> ChartSpec:
        dt = datetime.fromtimestamp(0, tz=timezone.utc)  # placeholder
        # Reconstruct UTC components from birth_jd via inverse is heavy; store UTC in build.
        raise NotImplementedError("use build_executive_radix")


def _dob_from_str(text: str) -> date:
    y, m, d = text.strip().split("-")
    return date(int(y), int(m), int(d))


def birth_jd_for_dob(
    dob: date,
    *,
    ticker: str,
    use_local_noon: bool = True,
) -> tuple[float, str, str]:
    """Return (birth_jd_ut, time_convention, timezone_label)."""
    if use_local_noon and ticker.upper() in BIRTHPLACE_TZ:
        tz_name, _note = BIRTHPLACE_TZ[ticker.upper()]
        tz = ZoneInfo(tz_name)
        local = datetime.combine(dob, time(12, 0, 0), tzinfo=tz)
        utc = local.astimezone(timezone.utc)
        jd = utc_to_jd(
            utc.year, utc.month, utc.day, utc.hour, utc.minute, utc.second
        )
        return jd, "noon_local_birthplace", tz_name
    utc = datetime.combine(dob, time(12, 0, 0), tzinfo=timezone.utc)
    jd = utc_to_jd(utc.year, utc.month, utc.day, utc.hour, utc.minute, utc.second)
    return jd, "noon_utc_fallback", "UTC"


def build_executive_radix(
    *,
    ticker: str,
    executive: str,
    dob_str: str,
    verification_status: str,
) -> ExecutiveRadix:
    dob = _dob_from_str(dob_str)
    jd, convention, tz = birth_jd_for_dob(dob, ticker=ticker)
    quality = (verification_status or "").strip() or "unknown"
    uncertain = True  # all CEO times treated as uncertain unless sourced
    note = f"{convention}; {tz}; angles/houses excluded from features"
    return ExecutiveRadix(
        ticker=ticker.upper(),
        executive=executive,
        dob=dob,
        birth_jd=jd,
        time_convention=convention,
        timezone_used=tz,
        birth_time_uncertain=uncertain,
        dob_quality=quality,
        notes=note,
    )


def sensitivity_birth_jd_perturbations(birth_jd: float, *, hours: tuple[float, ...] = (-6.0, 6.0)) -> list[tuple[str, float]]:
    """Fixed ±6h JD perturbations (not optimised from outcomes)."""
    day = 1.0 / 24.0
    out: list[tuple[str, float]] = [("nominal", birth_jd)]
    for h in hours:
        label = f"jd_shift_{h:+g}h"
        out.append((label, birth_jd + h * day))
    return out
