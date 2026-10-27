"""Headless astrolog mirror (-pd -1) via sa_app/listok ast77 scripts (no sa_app Python imports)."""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import date, datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

from astrolog_paths import resolve_ast77_binary, resolve_ast77_root

MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
ET = ZoneInfo("America/New_York")
EVENT_ZONE = "4:00"  # EDT, hours west of UTC (ast77 convention)


@dataclass(frozen=True)
class ChartSpec:
    name: str
    place: str
    year: int
    month: int
    day: int
    hour: int
    minute: int
    second: int = 0
    lon: str = "74w00"
    lat: str = "40n45"
    zone: str = EVENT_ZONE


def format_qcl(c: ChartSpec) -> str:
    mon = MONTHS[c.month - 1]
    label = c.name.replace('"', "'")[:72]
    place = c.place.replace('"', "'")[:72]
    return (
        f"-qcl {mon} {c.day} {c.year}  "
        f"{c.hour:02d}:{c.minute:02d}:{c.second:02d} ST {c.zone} "
        f"{c.lon} {c.lat} "
        f'"{label}" "{place}"'
    )


def write_chart_list(path: Path, radix: ChartSpec, event: ChartSpec) -> None:
    path.write_text(
        "@AL770  ; Brazil FT mirror debug\n"
        f"{format_qcl(radix)}\n"
        f"{format_qcl(event)}\n",
        encoding="utf-8",
    )


def _run(cmd: list[str], *, cwd: Path, env: dict | None = None) -> str:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(f"astrolog failed ({proc.returncode}): {' '.join(cmd)}\n{detail}")
    return proc.stdout or ""


# Patched ast77 binary aborts (SIGABRT) when invoked by absolute path from Python subprocess;
# run as ./astrolog with cwd=ast77 root (same as reverse_chart.sh when ASTROLOG=./astrolog).
_ASTrolog_BIN = "./astrolog"


def run_mirror_bundle(
    radix: ChartSpec,
    event: ChartSpec,
    *,
    pd_key: str = "-1.0",
    event_st_zone: str | None = None,
) -> tuple[str, str]:
    """Returns (internal_mirror_aspects, radix_cross_aspects) text."""
    root = resolve_ast77_root()
    binary = resolve_ast77_binary(root)
    base = "astrolog-custom-tropical.as"
    symbolic = "astrolog-progression-symbolic.as"
    real = "astrolog-progression-real.as"
    for p in (binary, root / base, root / symbolic, root / real, root / "scripts" / "reverse_chart.sh"):
        if not p.is_file():
            raise FileNotFoundError(p)

    env = os.environ.copy()
    env["ASTROLOG"] = _ASTrolog_BIN

    with tempfile.TemporaryDirectory(prefix="br_mirror_") as tmp:
        tmp_path = Path(tmp)
        chart_list = tmp_path / "chart_list.txt"
        outdir = tmp_path / "out"
        write_chart_list(chart_list, radix, event)
        _run(
            [
                "bash",
                "./scripts/reverse_chart.sh",
                "--key",
                pd_key,
                str(chart_list),
                "0",
                "1",
                str(outdir),
            ],
            cwd=root,
            env=env,
        )

        rev_dump = outdir / "reverse" / "reverse_positions_dump.txt"
        if not rev_dump.is_file():
            raise FileNotFoundError(rev_dump)

        internal = _run(
            [
                _ASTrolog_BIN,
                "-i",
                base,
                "-i",
                symbolic,
                "-i",
                real,
                "-i",
                str(rev_dump),
                "-a",
            ],
            cwd=root,
            env=env,
        )

        cross = _run(
            [
                _ASTrolog_BIN,
                "-i",
                base,
                "-i",
                symbolic,
                "-i",
                real,
                "-pC",
                "1",
                "-i",
                str(chart_list),
                "-rp0",
                str(chart_list),
                str(chart_list),
                "-z",
                event_st_zone or event.zone or EVENT_ZONE,
                "-qL",
                "0",
                "-qL2",
                "1",
                "-pt",
                "~Mon2",
                "~Day2",
                "~Yea2",
                "~Tim2",
                "-pd",
                pd_key,
                "-a",
            ],
            cwd=root,
            env=env,
        )
        return _strip_dbg(internal), _strip_dbg(cross)


def _strip_dbg(text: str) -> str:
    lines = [ln for ln in text.splitlines() if not ln.startswith("DBG:")]
    return "\n".join(lines).strip() + "\n"


def _parse_ft_date(dstr: object) -> date | None:
    if dstr is None:
        return None
    text = str(dstr).strip()[:10]
    if not text or text.lower() in ("nan", "none"):
        return None
    y, m, d = text.split("-")
    return date(int(y), int(m), int(d))


def chart_from_ft(ticker: str, row) -> ChartSpec:
    d = _parse_ft_date(row.get("ft_date") if hasattr(row, "get") else row["ft_date"])
    if d is None:
        raise ValueError(f"{ticker}: missing FT date")
    tstr = row.get("ft_time_hhmm")
    if tstr and str(tstr) not in ("", "nan", "None"):
        hh, mm = str(tstr).split(":")[:2]
        hour, minute = int(hh), int(mm)
    else:
        hour, minute = 12, 0
    company = (row.get("company") or ticker)[:60]
    return ChartSpec(
        name=f"{ticker} FT",
        place="New York NY",
        year=d.year,
        month=d.month,
        day=d.day,
        hour=hour,
        minute=minute,
    )


def ny_standard_time_zone_hours_west(session: date) -> str:
    """Astrolog ST zone string (hours west of UTC) for America/New_York on session date."""
    local_noon = datetime.combine(session, time(12, 0), tzinfo=ET)
    hours_west = int(-local_noon.utcoffset().total_seconds() // 3600)
    return f"{hours_west}:00"


def event_chart(ticker: str, event: date, label: str, *, st_zone: str | None = None) -> ChartSpec:
    return ChartSpec(
        name=f"{ticker} event {event.isoformat()}",
        place="New York NY",
        year=event.year,
        month=event.month,
        day=event.day,
        hour=9,
        minute=30,
        zone=st_zone or ny_standard_time_zone_hours_west(event),
    )
