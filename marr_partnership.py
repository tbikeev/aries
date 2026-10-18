# Copyright (C) 2026 Max Lange
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Marr partnership horoscope (time-distance offset).

When the younger partner was born later, the older partner's birth moment is
moved backward by the elapsed time between the two nativities:

    t_partnership = t_older - (t_younger - t_older) = 2 * t_older - t_younger

The chart is cast for the younger partner's birthplace and uses the younger
partner's sex flag for the radix record.
"""

from __future__ import annotations

import copy
from typing import Tuple

import astrology
import chart
import mtexts
from engine import calendar_policy


def partnership_jd(jd_older: float, jd_younger: float) -> float:
	"""Julian day of the Marr partnership epoch."""
	return (2.0 * float(jd_older)) - float(jd_younger)


def classify_older_younger(chrt_a, chrt_b):
	"""Return (older_chart, younger_chart) ordered by birth instant (UT jd)."""
	jd_a = float(getattr(chrt_a.time, "jd", 0.0))
	jd_b = float(getattr(chrt_b.time, "jd", 0.0))
	if jd_a <= jd_b:
		return chrt_a, chrt_b
	return chrt_b, chrt_a


def _chart_time_from_jd(jd: float, place, reference_time) -> chart.Time:
	cal = getattr(reference_time, "cal", chart.Time.GREGORIAN)
	if calendar_policy.calendar_for_jd(jd) == calendar_policy.CALENDAR_JULIAN:
		cal = chart.Time.JULIAN
	calflag = astrology.SE_JUL_CAL if cal == chart.Time.JULIAN else astrology.SE_GREG_CAL

	year, month, day, hour_float = astrology.swe_revjul(float(jd), calflag)
	hour = int(hour_float)
	minute_float = (hour_float - hour) * 60.0
	minute = int(minute_float)
	second = int(round((minute_float - minute) * 60.0))

	if second >= 60:
		second = 0
		minute += 1
	if minute >= 60:
		minute = 0
		hour += 1
	if hour >= 24:
		hour = 0
		import util

		year, month, day = util.incrDay(int(year), int(month), int(day))

	bc = int(year) <= 0
	if bc:
		year = 1 - int(year)

	plus = bool(getattr(reference_time, "plus", True))
	zh = int(getattr(reference_time, "zh", 0) or 0)
	zm = int(getattr(reference_time, "zm", 0) or 0)
	daylight = bool(getattr(reference_time, "daylightsaving", False))
	tzid = str(getattr(reference_time, "tzid", "") or "")
	tzauto = bool(getattr(reference_time, "tzauto", False))
	zt = getattr(reference_time, "zt", chart.Time.GREENWICH)

	return chart.Time(
		int(year),
		int(month),
		int(day),
		int(hour),
		int(minute),
		int(second),
		bc,
		cal,
		zt,
		plus,
		zh,
		zm,
		daylight,
		place,
		tzauto,
		tzid=tzid,
		tzauto=tzauto,
	)


def partnership_datetime_tuple(older_chrt, younger_chrt) -> Tuple[int, int, int, int, int, int]:
	"""Wall-clock components for the partnership epoch (older reference calendar)."""
	older, younger = older_chrt, younger_chrt
	jd = partnership_jd(older.time.jd, younger.time.jd)
	time_obj = _chart_time_from_jd(jd, younger.place, older.time)
	return (
		int(time_obj.year),
		int(time_obj.month),
		int(time_obj.day),
		int(time_obj.hour),
		int(time_obj.minute),
		int(time_obj.second),
	)


def build_marr_partnership_chart(chrt_a, chrt_b, opts, name=None):
	"""Build a radix-style Marr partnership chart for two nativities."""
	older, younger = classify_older_younger(chrt_a, chrt_b)
	jd = partnership_jd(older.time.jd, younger.time.jd)
	place = younger.place
	time = _chart_time_from_jd(jd, place, older.time)
	label = mtexts.txts.get("MarrPartnership", "Marr Partnership")
	default_name = "%s & %s %s" % (
		getattr(older, "name", "") or "Partner",
		getattr(younger, "name", "") or "Partner",
		label,
	)
	chart_name = name or default_name
	partnership = chart.Chart(
		chart_name,
		bool(getattr(younger, "male", True)),
		time,
		place,
		chart.Chart.RADIX,
		mtexts.txts.get("MarrPartnershipChart", "Marr partnership chart"),
		copy.deepcopy(opts),
		full=False,
	)
	partnership.full = True
	partnership.is_marr_partnership = True
	partnership.marr_partnership_source_pair = (older, younger)
	if partnership.full:
		from compositechart import _materialize_full_chart_state

		_materialize_full_chart_state(partnership)
	return partnership
