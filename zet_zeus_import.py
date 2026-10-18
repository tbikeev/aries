# Copyright (C) 2026 Max Lange
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Import chart lines from Zet and Zeus semicolon-delimited export formats."""

from __future__ import annotations

import re
from typing import Any

from aaf_import import record_to_v1_dict

_ZET_LINE_RE = re.compile(
	r"^[^;]+;\s*\d{1,2}\.\d{1,2}\.\d{4};",
)
_ZEUS_LINE_RE = re.compile(
	r"^[^;]+;\d+;\s*\d{1,2}\.\d{1,2}\.\d{4};",
)


def parse_zet_text_best_effort(
	text: str,
	*,
	source_name: str = "<Zet paste>",
) -> dict[str, Any]:
	return _parse_lines(text, source_name=source_name, parser=_parse_zet_line)


def parse_zeus_text_best_effort(
	text: str,
	*,
	source_name: str = "<Zeus paste>",
) -> dict[str, Any]:
	return _parse_lines(text, source_name=source_name, parser=_parse_zeus_line)


def _parse_lines(
	text: str,
	*,
	source_name: str,
	parser,
) -> dict[str, Any]:
	records: list[dict[str, Any]] = []
	errors: list[dict[str, Any]] = []
	for lineno, raw_line in enumerate(str(text or "").splitlines(), start=1):
		line = raw_line.strip()
		if not line:
			continue
		try:
			records.append(parser(line, lineno))
		except ValueError as exc:
			errors.append(
				{
					"lineno": lineno,
					"source": source_name,
					"message": str(exc),
				}
			)
	return {"records": records, "errors": errors}


def records_to_v1_dicts(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
	return [record_to_v1_dict(record) for record in records]


def _parse_zet_line(line: str, lineno: int) -> dict[str, Any]:
	if not _ZET_LINE_RE.match(line):
		raise ValueError(f"line {lineno}: not a Zet chart line")
	parts = [part.strip() for part in line.split(";", 8)]
	if len(parts) < 8:
		raise ValueError(f"line {lineno}: Zet line needs at least 8 semicolon fields")
	name = parts[0]
	if not name:
		raise ValueError(f"line {lineno}: Zet line has no chart name")
	day, month, year, bc = _parse_dmY(parts[1], lineno)
	hour, minute, second, time_unknown = _parse_hms(parts[2], lineno)
	place = parts[4] if len(parts) > 4 else ""
	lat = _parse_zet_coord(parts[5], expected="lat", lineno=lineno)
	lon = _parse_zet_coord(parts[6], expected="lon", lineno=lineno)
	sex = parts[7].strip().upper()
	male = _parse_sex(sex)
	notes = parts[8].strip() if len(parts) > 8 else ""
	city, country = _split_place(place)
	tz_info = _timezone_from_zet_notes(notes)
	return {
		"name": name,
		"type": "radix",
		"male": male,
		"year": year,
		"month": month,
		"day": day,
		"bc": bc,
		"cal": "gregorian",
		"hour": hour,
		"minute": minute,
		"second": second,
		"time_unknown": time_unknown,
		"city": city,
		"country": country,
		"place": place,
		"lat": lat,
		"lon": lon,
		"tz": tz_info["tz"],
		"tz_name": tz_info["tz_name"],
		"zt": tz_info["zt"],
		"notes": notes,
	}


def _parse_zeus_line(line: str, lineno: int) -> dict[str, Any]:
	if not _ZEUS_LINE_RE.match(line):
		raise ValueError(f"line {lineno}: not a Zeus chart line")
	parts = [part.strip() for part in line.split(";", 11)]
	if len(parts) < 11:
		raise ValueError(f"line {lineno}: Zeus line needs at least 11 semicolon fields")
	name = parts[0]
	if not name:
		raise ValueError(f"line {lineno}: Zeus line has no chart name")
	day, month, year, bc = _parse_dmY(parts[2], lineno)
	hour, minute, second, time_unknown = _parse_hms(parts[3], lineno)
	place = parts[5]
	lat = _parse_zeus_coord(parts[6], expected="lat", lineno=lineno)
	lon = _parse_zeus_coord(parts[7], expected="lon", lineno=lineno)
	male = _parse_sex(parts[8])
	notes = parts[11].strip() if len(parts) > 11 else ""
	if not notes and len(parts) > 10:
		notes = parts[10].strip()
	city, country = _split_place(place)
	tz_info = _parse_zeus_timezone(parts[4], lineno)
	chart_type = "radix" if parts[1] == "0" else "radix"
	return {
		"name": name,
		"type": chart_type,
		"male": male,
		"year": year,
		"month": month,
		"day": day,
		"bc": bc,
		"cal": "gregorian",
		"hour": hour,
		"minute": minute,
		"second": second,
		"time_unknown": time_unknown,
		"city": city,
		"country": country,
		"place": place,
		"lat": lat,
		"lon": lon,
		"tz": tz_info["tz"],
		"tz_name": tz_info["tz_name"],
		"zt": tz_info["zt"],
		"notes": notes,
	}


def _parse_dmY(text: str, lineno: int) -> tuple[int, int, int, bool]:
	cleaned = str(text or "").strip()
	match = re.fullmatch(r"(\d{1,2})\.(\d{1,2})\.(\d{3,4})", cleaned)
	if not match:
		raise ValueError(f"line {lineno}: invalid date {text!r}")
	day = int(match.group(1))
	month = int(match.group(2))
	year = int(match.group(3))
	bc = year <= 0
	if bc:
		year = 1 - year
	if not 1 <= month <= 12 or not 1 <= day <= 31:
		raise ValueError(f"line {lineno}: invalid date {text!r}")
	return day, month, year, bc


def _parse_hms(text: str, lineno: int) -> tuple[int, int, int, bool]:
	cleaned = str(text or "").strip()
	if not cleaned or cleaned in {"*", "?"}:
		return 12, 0, 0, True
	match = re.fullmatch(r"(\d{1,2}):(\d{2})(?::(\d{2}))?", cleaned)
	if not match:
		raise ValueError(f"line {lineno}: invalid time {text!r}")
	hour = int(match.group(1))
	minute = int(match.group(2))
	second = int(match.group(3) or 0)
	if hour >= 24 or minute >= 60 or second >= 60:
		raise ValueError(f"line {lineno}: invalid time {text!r}")
	return hour, minute, second, False


def _parse_zet_coord(text: str, *, expected: str, lineno: int) -> float:
	cleaned = str(text or "").strip().lower()
	match = re.fullmatch(r"(\d+)([nsew])(\d+)", cleaned)
	if not match:
		raise ValueError(f"line {lineno}: invalid Zet {expected} {text!r}")
	degrees = int(match.group(1))
	hemisphere = match.group(2)
	minutes = int(match.group(3))
	value = degrees + (minutes / 60.0)
	if expected == "lat" and hemisphere not in {"n", "s"}:
		raise ValueError(f"line {lineno}: invalid Zet latitude {text!r}")
	if expected == "lon" and hemisphere not in {"e", "w"}:
		raise ValueError(f"line {lineno}: invalid Zet longitude {text!r}")
	if hemisphere in {"s", "w"}:
		value = -value
	return value


def _parse_zeus_coord(text: str, *, expected: str, lineno: int) -> float:
	cleaned = str(text or "").strip().upper()
	match = re.fullmatch(r"([NSEW])(\d+)\.(\d+)\.(\d+)", cleaned)
	if not match:
		raise ValueError(f"line {lineno}: invalid Zeus {expected} {text!r}")
	hemisphere = match.group(1)
	degrees = int(match.group(2))
	minutes = int(match.group(3))
	seconds = int(match.group(4))
	if expected == "lat" and hemisphere not in {"N", "S"}:
		raise ValueError(f"line {lineno}: invalid Zeus latitude {text!r}")
	if expected == "lon" and hemisphere not in {"E", "W"}:
		raise ValueError(f"line {lineno}: invalid Zeus longitude {text!r}")
	value = degrees + (minutes / 60.0) + (seconds / 3600.0)
	if hemisphere in {"S", "W"}:
		value = -value
	return value


def _parse_sex(text: str) -> bool | None:
	marker = str(text or "").strip().upper()
	if marker in {"M", "MALE"}:
		return True
	if marker in {"F", "FEMALE"}:
		return False
	if marker in {"", "-", "*", "?"}:
		return None
	raise ValueError(f"unsupported sex marker {text!r}")


def _split_place(place: str) -> tuple[str, str]:
	cleaned = str(place or "").strip()
	if not cleaned:
		return "", ""
	if "," in cleaned:
		head, tail = cleaned.rsplit(",", 1)
		return head.strip(), tail.strip()
	return cleaned, ""


def _timezone_from_zet_notes(notes: str) -> dict[str, str]:
	upper = str(notes or "").upper()
	if "TIMEZONE" in upper and "LMT" in upper:
		return {"tz": "Z", "tz_name": "LMT", "zt": "lmt"}
	return {"tz": "Z", "tz_name": "LMT", "zt": "lmt"}


def _parse_zeus_timezone(text: str, lineno: int) -> dict[str, str]:
	cleaned = str(text or "").strip()
	if not cleaned or cleaned == "-":
		return {"tz": "Z", "tz_name": "LMT", "zt": "lmt"}
	match = re.fullmatch(r"([+-])(\d{2}):(\d{2}):(\d{2})", cleaned)
	if not match:
		raise ValueError(f"line {lineno}: invalid Zeus timezone {text!r}")
	sign = 1 if match.group(1) == "+" else -1
	hours = int(match.group(2))
	minutes = int(match.group(3))
	seconds = int(match.group(4))
	if minutes >= 60 or seconds >= 60:
		raise ValueError(f"line {lineno}: invalid Zeus timezone {text!r}")
	total_minutes = sign * (hours * 60 + minutes + (1 if seconds >= 30 else 0))
	if total_minutes == 0:
		return {"tz": "Z", "tz_name": "", "zt": "zone"}
	sign_char = "+" if total_minutes >= 0 else "-"
	abs_minutes = abs(total_minutes)
	return {
		"tz": f"{sign_char}{abs_minutes // 60:02d}:{abs_minutes % 60:02d}",
		"tz_name": "",
		"zt": "zone",
	}
