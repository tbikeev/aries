# Copyright (C) 2026 Max Lange
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Marr partnership horoscope — Juan & Evita Perón reference case."""

from __future__ import annotations

import datetime

import astrology

from marr_partnership import classify_older_younger, partnership_datetime_tuple, partnership_jd


class _FakeTime:
	def __init__(self, dt: datetime.datetime, jd: float):
		self.year = dt.year
		self.month = dt.month
		self.day = dt.day
		self.hour = dt.hour
		self.minute = dt.minute
		self.second = dt.second
		self.jd = jd
		self.cal = 0  # GREGORIAN
		self.plus = True
		self.zh = 0
		self.zm = 0
		self.daylightsaving = False
		self.zt = 0
		self.tzid = ""
		self.tzauto = False


class _FakePlace:
	pass


class _FakeChart:
	def __init__(self, name: str, male: bool, dt: datetime.datetime, jd: float):
		self.name = name
		self.male = male
		self.time = _FakeTime(dt, jd)
		self.place = _FakePlace()


def _dt(y, m, d, h, mi, s):
	return datetime.datetime(y, m, d, h, mi, s)


def test_partnership_jd_symmetry():
	juan_dt = _dt(1895, 10, 8, 12, 4, 22)
	evita_dt = _dt(1919, 5, 7, 8, 56, 51)
	# Use synthetic JDs with the same ordering as real ephemeris would preserve.
	juan_jd = 2414338.003009
	evita_jd = 2422948.872812
	assert partnership_jd(juan_jd, evita_jd) == (2.0 * juan_jd - evita_jd)


def test_peron_partnership_datetime_civil():
	"""Morinus/Aries export: partnership 11.03.1872 15:11:53 for Juan/Evita."""
	juan_dt = _dt(1895, 10, 8, 12, 4, 22)
	evita_dt = _dt(1919, 5, 7, 8, 56, 51)
	delta = evita_dt - juan_dt
	expected = juan_dt - delta
	assert expected == _dt(1872, 3, 11, 15, 11, 53)

	def _jd(dt: datetime.datetime) -> float:
		return astrology.swe_julday(
			dt.year,
			dt.month,
			dt.day,
			dt.hour + dt.minute / 60.0 + dt.second / 3600.0,
			astrology.SE_GREG_CAL,
		)

	juan = _FakeChart("Peron, Juan", True, juan_dt, _jd(juan_dt))
	evita = _FakeChart("Peron, Evita", False, evita_dt, _jd(evita_dt))
	older, younger = classify_older_younger(juan, evita)
	assert older is juan
	assert younger is evita
	tuple_ = partnership_datetime_tuple(older, younger)
	assert tuple_ == (
		expected.year,
		expected.month,
		expected.day,
		expected.hour,
		expected.minute,
		expected.second,
	)
