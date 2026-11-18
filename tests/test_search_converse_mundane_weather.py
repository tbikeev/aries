# Copyright (C) 2026 Max Lange
# SPDX-License-Identifier: AGPL-3.0-or-later

import chart
import searchbackend
import searchquery
from engine import converse_transits


class _FakeTime:
    def __init__(self, jd):
        self.jd = jd
        self.cal = chart.Time.GREGORIAN


class _FakeChart:
    def __init__(self, birth_jd):
        self.time = _FakeTime(birth_jd)


def _mundane_row(converse_jd):
    row = searchquery.SearchResult(
        searchquery.SearchQuery.TECHNIQUE_MUNDANE_WEATHER,
        searchquery.SearchQuery.ASPECT_CONJUNCTION,
        "planet:mars",
        "planet:saturn",
    )
    row.event_jd = converse_jd
    return row


def test_converse_mundane_weather_remaps_to_display_window(monkeypatch):
    birth_jd = 2451545.0
    display_jd = birth_jd + 15.0
    converse_jd = converse_transits.mirrored_jd(birth_jd, display_jd)
    chrt = _FakeChart(birth_jd)

    def fake_mundane(catalog, chart_obj, query, start_jd, end_jd, runtime=None, compiled=None):
        assert start_jd <= converse_jd < end_jd
        return [_mundane_row(converse_jd)]

    monkeypatch.setattr(searchbackend, "_search_mundane_weather", fake_mundane)
    monkeypatch.setattr(
        searchbackend,
        "_fill_row_from_jd",
        lambda row, catalog, event_jd, calflag: setattr(row, "event_jd", event_jd),
    )

    rows = searchbackend._search_converse_mundane_weather(
        catalog=None,
        chrt=chrt,
        query=None,
        display_start_jd=birth_jd + 10.0,
        display_end_jd=birth_jd + 20.0,
    )

    assert len(rows) == 1
    row = rows[0]
    assert row.technique == searchquery.SearchQuery.TECHNIQUE_CONVERSE_MUNDANE_WEATHER
    assert abs(float(row.event_jd) - display_jd) < 1e-6
    assert abs(float(row.metadata["converse_mundane_weather_jd"]) - converse_jd) < 1e-6


def test_converse_mundane_weather_drops_out_of_range_events(monkeypatch):
    birth_jd = 2451545.0
    chrt = _FakeChart(birth_jd)
    far_converse_jd = birth_jd - 100.0

    monkeypatch.setattr(
        searchbackend,
        "_search_mundane_weather",
        lambda *args, **kwargs: [_mundane_row(far_converse_jd)],
    )

    rows = searchbackend._search_converse_mundane_weather(
        catalog=None,
        chrt=chrt,
        query=None,
        display_start_jd=birth_jd + 10.0,
        display_end_jd=birth_jd + 20.0,
    )

    assert rows == []
