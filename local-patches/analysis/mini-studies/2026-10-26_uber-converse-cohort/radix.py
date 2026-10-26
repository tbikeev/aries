"""Fixed UBER cohort radix charts (researcher-supplied metadata)."""

from __future__ import annotations

from dataclasses import dataclass

from converse import utc_to_jd


@dataclass(frozen=True)
class ChartSpec:
    key: str
    label: str
    year: int
    month: int
    day: int
    hour: int
    minute: int
    second: int
    latitude_deg: float
    longitude_deg: float
    notes: str = ""

    @property
    def birth_jd(self) -> float:
        return utc_to_jd(
            self.year,
            self.month,
            self.day,
            self.hour,
            self.minute,
            self.second,
        )


NYSE_LAT = 40.7128
NYSE_LON = -74.0060

RADIX_COHORT: dict[str, ChartSpec] = {
    "FT": ChartSpec(
        key="FT",
        label="UBER first trade (NYSE)",
        year=2019,
        month=5,
        day=10,
        hour=15,
        minute=50,
        second=0,
        latitude_deg=NYSE_LAT,
        longitude_deg=NYSE_LON,
        notes="2019-05-10 11:50 -04:00 → 15:50 UTC; matches Stocks/UBER.zbs",
    ),
    "INC": ChartSpec(
        key="INC",
        label="Uber Technologies Inc. (Delaware incorporation)",
        year=2013,
        month=3,
        day=14,
        hour=16,
        minute=0,
        second=0,
        latitude_deg=39.0 + 2 / 60.0 + 45 / 3600.0,
        longitude_deg=-(75.0 + 29 / 60.0 + 32 / 3600.0),
        notes="2013-03-14 12:00 -04:00 → 16:00 UTC",
    ),
    "DK": ChartSpec(
        key="DK",
        label="Dara Khosrowshahi",
        year=1969,
        month=5,
        day=28,
        hour=9,
        minute=0,
        second=0,
        latitude_deg=35.0 + 41 / 60.0,
        longitude_deg=51.0 + 25 / 60.0,
        notes="1969-05-28 12:00 +03:00 → 09:00 UTC; noon may be conventional — see README",
    ),
}


@dataclass(frozen=True)
class EventSpec:
    key: str
    label: str
    year: int
    month: int
    day: int
    hour: int
    minute: int
    second: int
    latitude_deg: float
    longitude_deg: float

    @property
    def event_jd(self) -> float:
        return utc_to_jd(
            self.year,
            self.month,
            self.day,
            self.hour,
            self.minute,
            self.second,
        )


EVENTS: dict[str, EventSpec] = {
    "NEG-01": EventSpec(
        key="NEG-01",
        label="NEG-01",
        year=2026,
        month=2,
        day=4,
        hour=14,
        minute=30,
        second=0,
        latitude_deg=NYSE_LAT,
        longitude_deg=NYSE_LON,
    ),
    "POS-01": EventSpec(
        key="POS-01",
        label="POS-01",
        year=2026,
        month=8,
        day=7,
        hour=16,
        minute=0,
        second=0,
        latitude_deg=NYSE_LAT,
        longitude_deg=NYSE_LON,
    ),
}

ZET_COLLECTION_KEY = "UBER.zdb"
