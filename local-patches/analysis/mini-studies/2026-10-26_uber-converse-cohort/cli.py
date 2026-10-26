#!/usr/bin/env python3
"""Phase E: run cohort analysis for an arbitrary events CSV."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from analysis import OUTPUT_DIR, run_full_analysis
from radix import EVENTS, EventSpec


def load_events_csv(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            rows.append(row)
    return rows


def parse_event_row(row: dict) -> EventSpec:
    """Columns: label, year, month, day, hour, minute, second, utc_offset_hours, lat, lon."""
    off = float(row.get("utc_offset_hours", 0))
    hour = int(row["hour"])
    minute = int(row.get("minute", 0))
    second = int(row.get("second", 0))
    # Local civil time → UTC (fixed offset, no DST).
    from datetime import datetime, timedelta, timezone

    local = datetime(
        int(row["year"]),
        int(row["month"]),
        int(row["day"]),
        hour,
        minute,
        second,
        tzinfo=timezone(timedelta(hours=off)),
    )
    utc = local.astimezone(timezone.utc)
    return EventSpec(
        key=str(row.get("label", row.get("key", "EVENT"))),
        label=str(row.get("label", "EVENT")),
        year=utc.year,
        month=utc.month,
        day=utc.day,
        hour=utc.hour,
        minute=utc.minute,
        second=utc.second,
        latitude_deg=float(row.get("lat", 40.7128)),
        longitude_deg=float(row.get("lon", -74.0060)),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="UBER converse cohort analyzer")
    sub = parser.add_subparsers(dest="command")
    p_cohort = sub.add_parser("cohort", help="Original NEG/POS mini-study")
    p_cohort.add_argument(
        "--events-csv",
        type=Path,
        help="Optional CSV of extra events (label,timestamp fields). Merged with built-in NEG/POS.",
    )
    p_cohort.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_DIR,
        help="Output directory for CSVs and reports",
    )

    p_earn = sub.add_parser("earnings-study", help="Earnings reaction converse pipeline")
    p_earn.add_argument("--ticker", default="UBER")
    p_earn.add_argument("--earnings-csv", type=Path, default=None)
    p_earn.add_argument("--ohlc-csv", type=Path, default=None)
    p_earn.add_argument("--top-positive", type=int, default=10)
    p_earn.add_argument("--top-negative", type=int, default=10)
    p_earn.add_argument("--output-dir", type=Path, default=None)

    p_daily = sub.add_parser("daily-study", help="Daily UBER panel (frozen DK/FT/INC hypotheses)")
    p_daily.add_argument("--ohlc-csv", type=Path, default=None)
    p_daily.add_argument("--earnings-reactions-csv", type=Path, default=None)
    p_daily.add_argument("--output-dir", type=Path, default=None)
    p_daily.add_argument(
        "--recompute-features",
        action="store_true",
        help="Ignore cached daily_converse_features.csv",
    )

    args = parser.parse_args()
    if args.command == "daily-study":
        from daily_pipeline import run_daily_study

        summary = run_daily_study(
            ohlc_csv=args.ohlc_csv,
            earnings_reactions_csv=args.earnings_reactions_csv,
            output_dir=args.output_dir,
            reuse_features=not args.recompute_features,
        )
        print(json.dumps(summary, indent=2))
        return
    if args.command == "earnings-study":
        from earnings_pipeline import run_earnings_study

        summary = run_earnings_study(
            earnings_csv=args.earnings_csv,
            ohlc_csv=args.ohlc_csv,
            output_dir=args.output_dir,
            top_positive=args.top_positive,
            top_negative=args.top_negative,
        )
        print(json.dumps(summary, indent=2))
        return
    if args.command is None:
        args.command = "cohort"
        args.events_csv = None
        args.output_dir = OUTPUT_DIR

    extra = None
    if args.events_csv:
        extra = load_events_csv(args.events_csv)
        for row in extra:
            spec = parse_event_row(row)
            EVENTS[spec.key] = spec  # type: ignore[index]

    if args.output_dir != OUTPUT_DIR:
        import analysis as analysis_mod

        analysis_mod.OUTPUT_DIR = args.output_dir

    summary = run_full_analysis(extra_events=extra)
    print(f"Wrote outputs to {summary['output_dir']}")


if __name__ == "__main__":
    main()
