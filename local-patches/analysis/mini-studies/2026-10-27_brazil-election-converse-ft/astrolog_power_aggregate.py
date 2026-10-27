#!/usr/bin/env python3
"""Aggregate qualifying planetary aspect power (Oct 5 vs Oct 26) from astrolog_debug outputs.

Filters: both endpoints must be Sun, Mercury, Venus, Mars, Jupiter, Saturn, Uranus,
Neptune, or Pluto (same rule as the archive AWK one-liner).

Writes CSV summaries under output/astrolog_debug/ and prints validation vs expected totals.
"""

from __future__ import annotations

import argparse
import csv
import html
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from astrolog_paths import STUDY_ROOT

QUALIFYING = frozenset(
    {
        "Sun",
        "Mercury",
        "Venus",
        "Mars",
        "Jupiter",
        "Saturn",
        "Uranus",
        "Neptune",
        "Pluto",
    }
)

TICKERS = ("ABEV", "BBD", "ERJ", "ITUB", "NU", "PAGS", "PBR", "STNE", "VALE", "XP")
RUN_DATE = "2026-10-05"
CRASH_DATE = "2026-10-26"
MODES = ("c2c", "c2r")
DATE_LABEL = {RUN_DATE: "run", CRASH_DATE: "crash"}

_ASPECT_RE = re.compile(
    r"(?:\)|\])\s+(Con|Opp|Squ|Tri|Sex|Inc)\s+(?:with\s+)?[(\[]",
    re.I,
)
_POWER_LINE = re.compile(r" - power:\s+([0-9.]+)\s*$")

# Reference totals from independent archive verification (two decimal places on sums).
EXPECTED_OVERALL = {
    ("c2c", RUN_DATE): (113, 502.36, 4.446),
    ("c2c", CRASH_DATE): (128, 492.19, 3.845),
    ("c2r", RUN_DATE): (288, 1089.67, 3.784),
    ("c2r", CRASH_DATE): (294, 1225.92, 4.170),
}

EXPECTED_C2C_ASPECT = {
    "con": (114.92, 75.34),
    "sex": (138.06, 117.52),
    "tri": (102.41, 90.36),
    "squ": (112.61, 130.85),
    "opp": (16.20, 59.71),
    "inc": (18.16, 18.42),
}

EXPECTED_C2R_ASPECT = {
    "con": (182.59, 252.00),
    "sex": (227.77, 265.01),
    "tri": (194.87, 249.42),
    "squ": (314.19, 303.99),
    "opp": (116.16, 112.70),
    "inc": (54.10, 42.80),
}


@dataclass(frozen=True)
class QualifyingAspect:
    left: str
    right: str
    aspect: str
    power: float


def _right_body_from_line(line: str) -> str | None:
    """Match archive AWK: split on ) or ] + whitespace; right = split field a[3] (1-based)."""
    parts = re.split(r"[)\]][ \t]+", line)
    if len(parts) < 3:
        return None
    right = parts[2]
    right = re.sub(r"[ \t]+- orb:.*", "", right)
    return right.strip()


def _left_body_from_line(line: str) -> str | None:
    m = re.match(r"^\s*\d+:\s+(\S+)", line)
    return m.group(1) if m else None


def parse_qualifying_aspects(text: str) -> list[QualifyingAspect]:
    out: list[QualifyingAspect] = []
    for line in text.splitlines():
        if " - power:" not in line:
            continue
        mp = _POWER_LINE.search(line)
        if not mp:
            continue
        left = _left_body_from_line(line)
        right = _right_body_from_line(line)
        if not left or not right or left not in QUALIFYING or right not in QUALIFYING:
            continue
        ma = _ASPECT_RE.search(line)
        if not ma:
            continue
        aspect = ma.group(1).lower()[:3]
        out.append(
            QualifyingAspect(
                left=left,
                right=right,
                aspect=aspect,
                power=float(mp.group(1)),
            )
        )
    return out


def _load_raw(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _html_pre_block(raw: str) -> str:
    """Extract aspect lines embedded in brazil_mirror_debug.html (<pre> sections)."""
    return html.unescape(raw)


def verify_html_matches_raw(html_path: Path, debug_dir: Path) -> list[str]:
    """Ensure HTML embeds the same qualifying aspect lines as on-disk raw files."""
    errors: list[str] = []
    if not html_path.is_file():
        return [f"Missing HTML report: {html_path}"]
    page = html.unescape(html_path.read_text(encoding="utf-8", errors="replace"))
    for ticker in TICKERS:
        for date in (RUN_DATE, CRASH_DATE):
            for mode in MODES:
                raw_path = debug_dir / f"{ticker}_{date}_{mode}.txt"
                if not raw_path.is_file():
                    errors.append(f"Missing raw file: {raw_path.name}")
                    continue
                aspects = parse_qualifying_aspects(_load_raw(raw_path))
                if not aspects:
                    errors.append(f"No qualifying aspects parsed from {raw_path.name}")
                    continue
                for a in aspects[:3]:
                    if f"{a.power:.4f}" not in page:
                        errors.append(
                            f"HTML missing sample aspect power for {raw_path.name} "
                            f"({a.left} {a.aspect} {a.right} power={a.power:.4f})"
                        )
                        break
    return errors


def discover_files(debug_dir: Path) -> dict[tuple[str, str, str], Path]:
    found: dict[tuple[str, str, str], Path] = {}
    for ticker in TICKERS:
        for date in (RUN_DATE, CRASH_DATE):
            for mode in MODES:
                p = debug_dir / f"{ticker}_{date}_{mode}.txt"
                if p.is_file():
                    found[(ticker, date, mode)] = p
    return found


def aggregate(debug_dir: Path) -> tuple[dict, dict, dict]:
    """Returns (overall, by_aspect, by_ticker) nested dicts."""
    overall: dict[tuple[str, str], dict] = {}
    by_aspect: dict[tuple[str, str, str], float] = {}
    by_ticker: dict[tuple[str, str, str], float] = {}

    files = discover_files(debug_dir)
    for (ticker, date, mode), path in sorted(files.items()):
        aspects = parse_qualifying_aspects(_load_raw(path))
        key = (mode, date)
        bucket = overall.setdefault(key, {"count": 0, "sum": 0.0})
        bucket["count"] += len(aspects)
        bucket["sum"] += sum(a.power for a in aspects)
        tk = (ticker, mode, date)
        by_ticker[tk] = sum(a.power for a in aspects)
        for a in aspects:
            by_aspect[(mode, date, a.aspect)] = (
                by_aspect.get((mode, date, a.aspect), 0.0) + a.power
            )

    return overall, by_aspect, by_ticker


def _pct_change(run: float, crash: float) -> float | None:
    if run == 0:
        return None
    return (crash - run) / run * 100.0


def _try_write_excel(
    out_dir: Path,
    overall_rows: list[dict],
    aspect_rows: list[dict],
    ticker_rows: list[dict],
) -> None:
    try:
        from openpyxl import Workbook
    except ImportError:
        return
    wb = Workbook()
    ws = wb.active
    ws.title = "overall"
    for i, row in enumerate(overall_rows, start=1):
        if i == 1:
            ws.append(list(row.keys()))
        ws.append(list(row.values()))
    ws2 = wb.create_sheet("by_aspect")
    for i, row in enumerate(aspect_rows, start=1):
        if i == 1:
            ws2.append(list(row.keys()))
        ws2.append(list(row.values()))
    ws3 = wb.create_sheet("by_ticker")
    for i, row in enumerate(ticker_rows, start=1):
        if i == 1:
            ws3.append(list(row.keys()))
        ws3.append(list(row.values()))
    xlsx = out_dir / "power_comparison.xlsx"
    wb.save(xlsx)
    print(f"Wrote {xlsx}")


def _write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def _close(a: float, b: float, *, tol_sum: float = 0.02, tol_avg: float = 0.002) -> bool:
    return abs(a - b) <= tol_sum if abs(a) > 1 else abs(a - b) <= tol_avg


def validate(
    overall: dict[tuple[str, str], dict],
    by_aspect: dict[tuple[str, str, str], float],
) -> list[str]:
    issues: list[str] = []
    for key, (exp_n, exp_sum, exp_avg) in EXPECTED_OVERALL.items():
        got = overall.get(key, {"count": 0, "sum": 0.0})
        n, s = got["count"], got["sum"]
        avg = s / n if n else 0.0
        if n != exp_n:
            issues.append(f"{key}: count {n} != expected {exp_n}")
        if not _close(s, exp_sum, tol_sum=0.02):
            issues.append(f"{key}: sum {s:.4f} != expected {exp_sum}")
        if not _close(avg, exp_avg, tol_avg=0.002):
            issues.append(f"{key}: avg {avg:.4f} != expected {exp_avg}")

    for aspect, (run_e, crash_e) in EXPECTED_C2C_ASPECT.items():
        run_g = by_aspect.get(("c2c", RUN_DATE, aspect), 0.0)
        crash_g = by_aspect.get(("c2c", CRASH_DATE, aspect), 0.0)
        if not _close(run_g, run_e):
            issues.append(f"c2c {aspect} run {run_g:.2f} != {run_e}")
        if not _close(crash_g, crash_e):
            issues.append(f"c2c {aspect} crash {crash_g:.2f} != {crash_e}")

    for aspect, (run_e, crash_e) in EXPECTED_C2R_ASPECT.items():
        run_g = by_aspect.get(("c2r", RUN_DATE, aspect), 0.0)
        crash_g = by_aspect.get(("c2r", CRASH_DATE, aspect), 0.0)
        if not _close(run_g, run_e):
            issues.append(f"c2r {aspect} run {run_g:.2f} != {run_e}")
        if not _close(crash_g, crash_e):
            issues.append(f"c2r {aspect} crash {crash_g:.2f} != {crash_e}")

    return issues


def build_report(
    debug_dir: Path,
    *,
    strict: bool,
) -> int:
    html_path = debug_dir / "brazil_mirror_debug.html"
    html_errors = verify_html_matches_raw(html_path, debug_dir)
    files = discover_files(debug_dir)
    expected_files = len(TICKERS) * len(MODES) * 2
    if len(files) != expected_files:
        html_errors.append(f"File count {len(files)} != expected {expected_files}")

    overall, by_aspect, by_ticker = aggregate(debug_dir)
    val_errors = validate(overall, by_aspect)
    all_errors = html_errors + val_errors

    out_dir = debug_dir
    overall_rows: list[dict] = []
    for mode in MODES:
        for date in (RUN_DATE, CRASH_DATE):
            b = overall.get((mode, date), {"count": 0, "sum": 0.0})
            n, s = b["count"], b["sum"]
            overall_rows.append(
                {
                    "mode": mode,
                    "date": date,
                    "date_label": DATE_LABEL[date],
                    "aspect_count": n,
                    "total_power": round(s, 4),
                    "avg_power": round(s / n, 4) if n else 0.0,
                }
            )
    for date in (RUN_DATE, CRASH_DATE):
        n = sum(overall.get((m, date), {"count": 0})["count"] for m in MODES)
        s = sum(overall.get((m, date), {"sum": 0.0})["sum"] for m in MODES)
        overall_rows.append(
            {
                "mode": "combined",
                "date": date,
                "date_label": DATE_LABEL[date],
                "aspect_count": n,
                "total_power": round(s, 4),
                "avg_power": round(s / n, 4) if n else 0.0,
            }
        )

    aspect_rows: list[dict] = []
    for mode, expected in (("c2c", EXPECTED_C2C_ASPECT), ("c2r", EXPECTED_C2R_ASPECT)):
        for aspect in ("con", "sex", "tri", "squ", "opp", "inc"):
            run_s = by_aspect.get((mode, RUN_DATE, aspect), 0.0)
            crash_s = by_aspect.get((mode, CRASH_DATE, aspect), 0.0)
            ch = _pct_change(run_s, crash_s)
            aspect_rows.append(
                {
                    "mode": mode,
                    "aspect": aspect,
                    "run_sum": round(run_s, 2),
                    "crash_sum": round(crash_s, 2),
                    "pct_change_crash_vs_run": round(ch, 1) if ch is not None else "",
                }
            )

    ticker_rows: list[dict] = []
    for ticker in TICKERS:
        for mode in MODES:
            run_p = by_ticker.get((ticker, mode, RUN_DATE), 0.0)
            crash_p = by_ticker.get((ticker, mode, CRASH_DATE), 0.0)
            ticker_rows.append(
                {
                    "ticker": ticker,
                    "mode": mode,
                    "run_total_power": round(run_p, 4),
                    "crash_total_power": round(crash_p, 4),
                    "crash_higher": crash_p > run_p,
                }
            )

    _write_csv(
        out_dir / "power_overall_summary.csv",
        overall_rows,
        ["mode", "date", "date_label", "aspect_count", "total_power", "avg_power"],
    )
    _write_csv(
        out_dir / "power_by_aspect_type.csv",
        aspect_rows,
        ["mode", "aspect", "run_sum", "crash_sum", "pct_change_crash_vs_run"],
    )
    _write_csv(
        out_dir / "power_by_ticker.csv",
        ticker_rows,
        ["ticker", "mode", "run_total_power", "crash_total_power", "crash_higher"],
    )

    _try_write_excel(out_dir, overall_rows, aspect_rows, ticker_rows)

    md_lines = [
        "# Astrolog qualifying power — Oct 5 (run) vs Oct 26 (crash)",
        "",
        f"Source: `{debug_dir}` · Planets: Sun–Pluto only (both endpoints).",
        "",
        "## Cross-check",
        f"- Raw files found: **{len(files)}/40**",
        f"- HTML raw match: **{'OK' if not html_errors else 'FAIL'}**",
        "",
        "## Overall",
        "",
        "| Mode | Date | Aspects | Total power | Avg power |",
        "|------|------|---------|-------------|-----------|",
    ]
    for row in overall_rows:
        md_lines.append(
            f"| {row['mode']} | {row['date_label']} | {row['aspect_count']} | "
            f"{row['total_power']:.2f} | {row['avg_power']:.3f} |"
        )

    c2c_higher = sum(
        1
        for t in TICKERS
        if by_ticker.get((t, "c2c", CRASH_DATE), 0) > by_ticker.get((t, "c2c", RUN_DATE), 0)
    )
    c2r_higher = sum(
        1
        for t in TICKERS
        if by_ticker.get((t, "c2r", CRASH_DATE), 0) > by_ticker.get((t, "c2r", RUN_DATE), 0)
    )
    md_lines.extend(
        [
            "",
            "## Per-ticker (crash higher total?)",
            f"- c2c: **{c2c_higher}/10** tickers higher on crash date",
            f"- c2r: **{c2r_higher}/10** tickers higher on crash date",
            "",
            "## Validation",
        ]
    )
    if all_errors:
        md_lines.append("**FAILED** — differences:")
        for e in all_errors:
            md_lines.append(f"- {e}")
    else:
        md_lines.append("**PASSED** — totals match archive reference tables.")

    report_path = out_dir / "POWER_AGGREGATE_REPORT.md"
    report_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    print(f"Wrote {out_dir / 'power_overall_summary.csv'}")
    print(f"Wrote {out_dir / 'power_by_aspect_type.csv'}")
    print(f"Wrote {out_dir / 'power_by_ticker.csv'}")
    print(f"Wrote {report_path}")
    if all_errors:
        print("\nValidation issues:", file=sys.stderr)
        for e in all_errors:
            print(f"  - {e}", file=sys.stderr)
        return 1 if strict else 0
    print("\nValidation PASSED (matches archive reference totals).")
    return 0


def main() -> None:
    p = argparse.ArgumentParser(description="Aggregate qualifying astrolog aspect power")
    p.add_argument(
        "--debug-dir",
        type=Path,
        default=STUDY_ROOT / "output" / "astrolog_debug",
        help="Directory with *_c2c.txt / *_c2r.txt outputs",
    )
    p.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 if validation fails (default: warn only)",
    )
    args = p.parse_args()
    raise SystemExit(build_report(args.debug_dir.resolve(), strict=args.strict))


if __name__ == "__main__":
    main()
