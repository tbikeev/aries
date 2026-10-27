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
from astrolog_study_config import ELECTION_2026, StudyConfig
from event_day_returns import load_returns_csv

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

MODES = ("c2c", "c2r")

_ASPECT_RE = re.compile(
    r"(?:\)|\])\s+(Con|Opp|Squ|Tri|Sex|Inc)\s+(?:with\s+)?[(\[]",
    re.I,
)
_POWER_LINE = re.compile(r" - power:\s+([0-9.]+)\s*$")

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


def _study_dates(study: StudyConfig) -> tuple[str, str]:
    return study.rebound_date, study.panic_date


def verify_html_matches_raw(html_path: Path, debug_dir: Path, *, study: StudyConfig) -> list[str]:
    """Ensure HTML embeds the same qualifying aspect lines as on-disk raw files."""
    errors: list[str] = []
    if not html_path.is_file():
        return [f"Missing HTML report: {html_path}"]
    page = html.unescape(html_path.read_text(encoding="utf-8", errors="replace"))
    rebound, panic = _study_dates(study)
    for ticker in study.tickers:
        for date in (rebound, panic):
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


def discover_files(debug_dir: Path, *, study: StudyConfig) -> dict[tuple[str, str, str], Path]:
    found: dict[tuple[str, str, str], Path] = {}
    rebound, panic = _study_dates(study)
    for ticker in study.tickers:
        for date in (rebound, panic):
            for mode in MODES:
                p = debug_dir / f"{ticker}_{date}_{mode}.txt"
                if p.is_file():
                    found[(ticker, date, mode)] = p
    return found


@dataclass
class TickerAgg:
    overall: dict[tuple[str, str], dict]
    by_aspect: dict[tuple[str, str, str], float]
    by_ticker_power: dict[tuple[str, str, str], float]
    by_ticker_count: dict[tuple[str, str, str], int]
    by_ticker_aspect_power: dict[tuple[str, str, str, str], float]
    by_ticker_aspect_count: dict[tuple[str, str, str, str], int]


def aggregate(debug_dir: Path, *, study: StudyConfig) -> TickerAgg:
    overall: dict[tuple[str, str], dict] = {}
    by_aspect: dict[tuple[str, str, str], float] = {}
    by_ticker_power: dict[tuple[str, str, str], float] = {}
    by_ticker_count: dict[tuple[str, str, str], int] = {}
    by_ticker_aspect_power: dict[tuple[str, str, str, str], float] = {}
    by_ticker_aspect_count: dict[tuple[str, str, str, str], int] = {}

    files = discover_files(debug_dir, study=study)
    for (ticker, date, mode), path in sorted(files.items()):
        aspects = parse_qualifying_aspects(_load_raw(path))
        key = (mode, date)
        bucket = overall.setdefault(key, {"count": 0, "sum": 0.0})
        bucket["count"] += len(aspects)
        bucket["sum"] += sum(a.power for a in aspects)
        tk = (ticker, mode, date)
        by_ticker_power[tk] = sum(a.power for a in aspects)
        by_ticker_count[tk] = len(aspects)
        for a in aspects:
            by_aspect[(mode, date, a.aspect)] = (
                by_aspect.get((mode, date, a.aspect), 0.0) + a.power
            )
            tak = (ticker, mode, date, a.aspect)
            by_ticker_aspect_power[tak] = by_ticker_aspect_power.get(tak, 0.0) + a.power
            by_ticker_aspect_count[tak] = by_ticker_aspect_count.get(tak, 0) + 1

    return TickerAgg(
        overall=overall,
        by_aspect=by_aspect,
        by_ticker_power=by_ticker_power,
        by_ticker_count=by_ticker_count,
        by_ticker_aspect_power=by_ticker_aspect_power,
        by_ticker_aspect_count=by_ticker_aspect_count,
    )


def load_event_returns(study: StudyConfig) -> dict[tuple[str, str], float]:
    """ticker, event_date -> return_cc_pct (event_day_returns.csv, else BR-2 panel)."""
    rebound, panic = _study_dates(study)
    csv_path = study.output_dir / "event_day_returns.csv"
    out = load_returns_csv(csv_path)
    if out:
        return out
    panel = STUDY_ROOT / "output" / "br2" / "eligible_ticker_event_panel.csv"
    if not panel.is_file():
        return out
    with panel.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("event_date") not in (rebound, panic):
                continue
            ticker = row.get("ticker", "")
            if ticker not in study.tickers:
                continue
            try:
                ret = float(row["company_return_cc_pct"])
            except (KeyError, ValueError):
                continue
            out[(ticker, row["event_date"])] = ret
    return out


ASPECT_ORDER = ("con", "sex", "tri", "squ", "opp", "inc")


def build_ticker_breakdown(
    agg: TickerAgg,
    returns: dict[tuple[str, str], float],
    *,
    study: StudyConfig,
) -> tuple[list[dict], list[dict]]:
    """Summary rows (one per ticker) and detail rows (ticker × mode × aspect)."""
    rebound, panic = _study_dates(study)
    summary: list[dict] = []
    detail: list[dict] = []
    for ticker in study.tickers:
        ret_rebound = returns.get((ticker, rebound))
        ret_panic = returns.get((ticker, panic))
        ret_diff = (
            (ret_panic - ret_rebound)
            if ret_rebound is not None and ret_panic is not None
            else None
        )
        row: dict = {
            "ticker": ticker,
            f"return_{study.rebound_label}_pct": round(ret_rebound, 2)
            if ret_rebound is not None
            else "",
            f"return_{study.panic_label}_pct": round(ret_panic, 2) if ret_panic is not None else "",
            f"return_diff_{study.panic_label}_minus_{study.rebound_label}_pp": round(ret_diff, 2)
            if ret_diff is not None
            else "",
        }
        for mode in MODES:
            n_run = agg.by_ticker_count.get((ticker, mode, rebound), 0)
            n_crash = agg.by_ticker_count.get((ticker, mode, panic), 0)
            p_run = agg.by_ticker_power.get((ticker, mode, rebound), 0.0)
            p_crash = agg.by_ticker_power.get((ticker, mode, panic), 0.0)
            row[f"{mode}_aspect_count_{study.rebound_label}"] = n_run
            row[f"{mode}_aspect_count_{study.panic_label}"] = n_crash
            row[f"{mode}_aspect_count_diff"] = n_crash - n_run
            row[f"{mode}_power_sum_{study.rebound_label}"] = round(p_run, 2)
            row[f"{mode}_power_sum_{study.panic_label}"] = round(p_crash, 2)
            row[f"{mode}_power_sum_diff"] = round(p_crash - p_run, 2)
            ret_reb_key = f"return_{study.rebound_label}_pct"
            ret_pan_key = f"return_{study.panic_label}_pct"
            ret_diff_key = f"return_diff_{study.panic_label}_minus_{study.rebound_label}_pp"
            for asp in ASPECT_ORDER:
                cn_r = agg.by_ticker_aspect_count.get((ticker, mode, rebound, asp), 0)
                cn_c = agg.by_ticker_aspect_count.get((ticker, mode, panic, asp), 0)
                pw_r = agg.by_ticker_aspect_power.get((ticker, mode, rebound, asp), 0.0)
                pw_c = agg.by_ticker_aspect_power.get((ticker, mode, panic, asp), 0.0)
                detail.append(
                    {
                        "ticker": ticker,
                        "mode": mode,
                        "aspect": asp,
                        f"count_{study.rebound_label}": cn_r,
                        f"count_{study.panic_label}": cn_c,
                        "count_diff": cn_c - cn_r,
                        f"power_{study.rebound_label}": round(pw_r, 2),
                        f"power_{study.panic_label}": round(pw_c, 2),
                        "power_diff": round(pw_c - pw_r, 2),
                        ret_reb_key: row[ret_reb_key],
                        ret_pan_key: row[ret_pan_key],
                        ret_diff_key: row[ret_diff_key],
                    }
                )
        summary.append(row)
    return summary, detail


def write_ticker_breakdown_html(
    path: Path,
    summary: list[dict],
    detail: list[dict],
    *,
    study: StudyConfig = ELECTION_2026,
) -> None:
    asp_label = {
        "con": "Conjunction",
        "sex": "Sextile",
        "tri": "Trine",
        "squ": "Square",
        "opp": "Opposition",
        "inc": "Inconjunct",
    }
    rl, pl = study.rebound_label, study.panic_label
    ret_reb = f"return_{rl}_pct"
    ret_pan = f"return_{pl}_pct"
    ret_diff = f"return_diff_{pl}_minus_{rl}_pp"
    parts = [
        "<!DOCTYPE html><html><head><meta charset='utf-8'>",
        f"<title>{html.escape(study.title)} — ticker power breakdown</title>",
        "<style>",
        "body{font-family:system-ui,sans-serif;margin:1rem;font-size:0.9rem;}",
        "table{border-collapse:collapse;width:100%;margin-bottom:1.5rem;}",
        "th,td{border:1px solid #ccc;padding:0.35rem 0.5rem;text-align:right;}",
        "th:first-child,td:first-child{text-align:left;}",
        "thead th{background:#eee;}",
        "h2{margin-top:2rem;border-bottom:1px solid #ccc;}",
        ".neg{color:#b00;}.pos{color:#060;}",
        "</style></head><body>",
        f"<h1>{html.escape(study.title)}</h1>",
        "<p>Qualifying aspects: Sun–Pluto both ends. Event time 09:30 NY (EDT). "
        f"Price diff = {pl} − {rl} (pp). See <code>event_day_returns.csv</code>.</p>",
        "<h2>All tickers — totals</h2>",
        "<table><thead><tr>",
        f"<th>Ticker</th><th>Ret {rl} %</th><th>Ret {pl} %</th><th>Δ pp</th>",
        f"<th>c2c # {rl}</th><th>c2c # {pl}</th><th>c2c Σ {rl}</th><th>c2c Σ {pl}</th>",
        f"<th>c2r # {rl}</th><th>c2r # {pl}</th><th>c2r Σ {rl}</th><th>c2r Σ {pl}</th>",
        "</tr></thead><tbody>",
    ]
    for r in summary:
        diff = r.get(ret_diff, "")
        diff_cls = ""
        if diff != "":
            diff_cls = "neg" if float(diff) < 0 else "pos" if float(diff) > 0 else ""
        parts.append(
            f"<tr><td>{r['ticker']}</td>"
            f"<td>{r.get(ret_reb, '')}</td><td>{r.get(ret_pan, '')}</td>"
            f"<td class='{diff_cls}'>{diff}</td>"
            f"<td>{r.get(f'c2c_aspect_count_{rl}', '')}</td><td>{r.get(f'c2c_aspect_count_{pl}', '')}</td>"
            f"<td>{r.get(f'c2c_power_sum_{rl}', '')}</td><td>{r.get(f'c2c_power_sum_{pl}', '')}</td>"
            f"<td>{r.get(f'c2r_aspect_count_{rl}', '')}</td><td>{r.get(f'c2r_aspect_count_{pl}', '')}</td>"
            f"<td>{r.get(f'c2r_power_sum_{rl}', '')}</td><td>{r.get(f'c2r_power_sum_{pl}', '')}</td></tr>"
        )
    parts.append("</tbody></table>")

    tickers = [r["ticker"] for r in summary]
    by_ticker: dict[str, list[dict]] = {t: [] for t in tickers}
    for d in detail:
        by_ticker[d["ticker"]].append(d)

    for ticker in tickers:
        parts.append(f"<h2>{ticker}</h2>")
        head = next(x for x in summary if x["ticker"] == ticker)
        parts.append(
            f"<p>Price: {rl} <strong>{head.get(ret_reb, '')}%</strong>, {pl} "
            f"<strong>{head.get(ret_pan, '')}%</strong>, Δ "
            f"<strong>{head.get(ret_diff, '')}</strong> pp</p>"
        )
        for mode in MODES:
            parts.append(f"<h3>{mode}</h3>")
            parts.append(
                f"<table><thead><tr><th>Aspect</th><th># {rl}</th><th># {pl}</th>"
                f"<th>Δ #</th><th>Σ {rl}</th><th>Σ {pl}</th><th>Δ power</th>"
                "</tr></thead><tbody>"
            )
            for asp in ASPECT_ORDER:
                d = next(
                    x for x in by_ticker[ticker] if x["mode"] == mode and x["aspect"] == asp
                )
                parts.append(
                    f"<tr><td>{asp_label[asp]}</td>"
                    f"<td>{d.get(f'count_{rl}', '')}</td><td>{d.get(f'count_{pl}', '')}</td>"
                    f"<td>{d.get('count_diff', '')}</td>"
                    f"<td>{d.get(f'power_{rl}', '')}</td><td>{d.get(f'power_{pl}', '')}</td>"
                    f"<td>{d.get('power_diff', '')}</td></tr>"
                )
            parts.append("</tbody></table>")
    parts.append("</body></html>")
    path.write_text("\n".join(parts), encoding="utf-8")


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
    *,
    study: StudyConfig,
) -> list[str]:
    issues: list[str] = []
    rebound, panic = _study_dates(study)
    if study.expected_overall:
        for key, (exp_n, exp_sum, exp_avg) in study.expected_overall.items():
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
            run_g = by_aspect.get(("c2c", rebound, aspect), 0.0)
            crash_g = by_aspect.get(("c2c", panic, aspect), 0.0)
            if not _close(run_g, run_e):
                issues.append(f"c2c {aspect} rebound {run_g:.2f} != {run_e}")
            if not _close(crash_g, crash_e):
                issues.append(f"c2c {aspect} panic {crash_g:.2f} != {crash_e}")

        for aspect, (run_e, crash_e) in EXPECTED_C2R_ASPECT.items():
            run_g = by_aspect.get(("c2r", rebound, aspect), 0.0)
            crash_g = by_aspect.get(("c2r", panic, aspect), 0.0)
            if not _close(run_g, run_e):
                issues.append(f"c2r {aspect} rebound {run_g:.2f} != {run_e}")
            if not _close(crash_g, crash_e):
                issues.append(f"c2r {aspect} panic {crash_g:.2f} != {crash_e}")

    return issues


def _date_label(study: StudyConfig, iso: str) -> str:
    if iso == study.rebound_date:
        return study.rebound_label
    if iso == study.panic_date:
        return study.panic_label
    return iso


def build_report(
    debug_dir: Path | None = None,
    *,
    study: StudyConfig = ELECTION_2026,
    strict: bool = False,
) -> int:
    out_dir = debug_dir or study.output_dir
    rebound, panic = _study_dates(study)
    html_path = out_dir / "brazil_mirror_debug.html"
    html_errors = verify_html_matches_raw(html_path, out_dir, study=study)
    files = discover_files(out_dir, study=study)
    expected_files = len(study.tickers) * len(MODES) * 2
    if len(files) != expected_files:
        html_errors.append(f"File count {len(files)} != expected {expected_files}")

    agg = aggregate(out_dir, study=study)
    overall, by_aspect = agg.overall, agg.by_aspect
    val_errors = validate(overall, by_aspect, study=study)
    all_errors = html_errors + val_errors

    returns = load_event_returns(study)
    summary_rows, detail_rows = build_ticker_breakdown(agg, returns, study=study)

    overall_rows: list[dict] = []
    for mode in MODES:
        for date in (rebound, panic):
            b = overall.get((mode, date), {"count": 0, "sum": 0.0})
            n, s = b["count"], b["sum"]
            overall_rows.append(
                {
                    "mode": mode,
                    "date": date,
                    "date_label": _date_label(study, date),
                    "aspect_count": n,
                    "total_power": round(s, 4),
                    "avg_power": round(s / n, 4) if n else 0.0,
                }
            )
    for date in (rebound, panic):
        n = sum(overall.get((m, date), {"count": 0})["count"] for m in MODES)
        s = sum(overall.get((m, date), {"sum": 0.0})["sum"] for m in MODES)
        overall_rows.append(
            {
                "mode": "combined",
                "date": date,
                "date_label": _date_label(study, date),
                "aspect_count": n,
                "total_power": round(s, 4),
                "avg_power": round(s / n, 4) if n else 0.0,
            }
        )

    aspect_rows: list[dict] = []
    for mode in MODES:
        for aspect in ASPECT_ORDER:
            reb_s = by_aspect.get((mode, rebound, aspect), 0.0)
            pan_s = by_aspect.get((mode, panic, aspect), 0.0)
            ch = _pct_change(reb_s, pan_s)
            aspect_rows.append(
                {
                    "mode": mode,
                    "aspect": aspect,
                    f"{study.rebound_label}_sum": round(reb_s, 2),
                    f"{study.panic_label}_sum": round(pan_s, 2),
                    f"pct_change_{study.panic_label}_vs_{study.rebound_label}": round(ch, 1)
                    if ch is not None
                    else "",
                }
            )

    ticker_rows: list[dict] = []
    for ticker in study.tickers:
        for mode in MODES:
            reb_p = agg.by_ticker_power.get((ticker, mode, rebound), 0.0)
            pan_p = agg.by_ticker_power.get((ticker, mode, panic), 0.0)
            ticker_rows.append(
                {
                    "ticker": ticker,
                    "mode": mode,
                    f"{study.rebound_label}_total_power": round(reb_p, 4),
                    f"{study.panic_label}_total_power": round(pan_p, 4),
                    f"{study.panic_label}_higher": pan_p > reb_p,
                }
            )

    summary_fields = list(summary_rows[0].keys()) if summary_rows else []
    detail_fields = list(detail_rows[0].keys()) if detail_rows else []
    _write_csv(out_dir / "power_ticker_breakdown_summary.csv", summary_rows, summary_fields)
    _write_csv(out_dir / "power_ticker_breakdown_by_aspect.csv", detail_rows, detail_fields)
    write_ticker_breakdown_html(
        out_dir / "power_ticker_breakdown.html", summary_rows, detail_rows, study=study
    )

    _write_csv(
        out_dir / "power_overall_summary.csv",
        overall_rows,
        ["mode", "date", "date_label", "aspect_count", "total_power", "avg_power"],
    )
    aspect_fields = list(aspect_rows[0].keys()) if aspect_rows else []
    ticker_fields = list(ticker_rows[0].keys()) if ticker_rows else []
    _write_csv(out_dir / "power_by_aspect_type.csv", aspect_rows, aspect_fields)
    _write_csv(out_dir / "power_by_ticker.csv", ticker_rows, ticker_fields)

    _try_write_excel(out_dir, overall_rows, aspect_rows, ticker_rows)

    md_lines = [
        f"# Astrolog qualifying power — {study.title}",
        "",
        f"Source: `{out_dir}` · Planets: Sun–Pluto only (both endpoints).",
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

    n_t = len(study.tickers)
    c2c_higher = sum(
        1
        for t in study.tickers
        if agg.by_ticker_power.get((t, "c2c", panic), 0)
        > agg.by_ticker_power.get((t, "c2c", rebound), 0)
    )
    c2r_higher = sum(
        1
        for t in study.tickers
        if agg.by_ticker_power.get((t, "c2r", panic), 0)
        > agg.by_ticker_power.get((t, "c2r", rebound), 0)
    )
    md_lines.extend(
        [
            "",
            f"## Per-ticker ({study.panic_label} higher total power?)",
            f"- c2c: **{c2c_higher}/{n_t}** tickers higher on {study.panic_date}",
            f"- c2r: **{c2r_higher}/{n_t}** tickers higher on {study.panic_date}",
            "",
            "## Validation",
        ]
    )
    if all_errors:
        md_lines.append("**FAILED** — differences:")
        for e in all_errors:
            md_lines.append(f"- {e}")
    elif study.expected_overall:
        md_lines.append("**PASSED** — totals match archive reference tables.")
    else:
        md_lines.append("**OK** — no fixed reference totals for this study preset.")

    report_path = out_dir / "POWER_AGGREGATE_REPORT.md"
    report_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    print(f"Wrote {out_dir / 'power_overall_summary.csv'}")
    print(f"Wrote {out_dir / 'power_by_aspect_type.csv'}")
    print(f"Wrote {out_dir / 'power_by_ticker.csv'}")
    print(f"Wrote {out_dir / 'power_ticker_breakdown_summary.csv'}")
    print(f"Wrote {out_dir / 'power_ticker_breakdown_by_aspect.csv'}")
    print(f"Wrote {out_dir / 'power_ticker_breakdown.html'}")
    print(f"Wrote {report_path}")
    if all_errors:
        print("\nValidation issues:", file=sys.stderr)
        for e in all_errors:
            print(f"  - {e}", file=sys.stderr)
        return 1 if strict else 0
    if study.expected_overall and not all_errors:
        print("\nValidation PASSED (matches archive reference totals).")
    return 0


def main() -> None:
    p = argparse.ArgumentParser(description="Aggregate qualifying astrolog aspect power")
    p.add_argument(
        "--study",
        choices=("election_2026", "covid_2020"),
        default="election_2026",
        help="Which event pair (sets default output dir and reference totals)",
    )
    p.add_argument(
        "--debug-dir",
        type=Path,
        default=None,
        help="Override output directory with *_c2c.txt / *_c2r.txt",
    )
    p.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 if validation fails (default: warn only)",
    )
    args = p.parse_args()
    from astrolog_study_config import COVID_2020

    study = ELECTION_2026 if args.study == "election_2026" else COVID_2020
    debug_dir = args.debug_dir.resolve() if args.debug_dir else None
    raise SystemExit(build_report(debug_dir, study=study, strict=args.strict))


if __name__ == "__main__":
    main()
