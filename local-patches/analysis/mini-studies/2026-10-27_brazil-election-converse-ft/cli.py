#!/usr/bin/env python3
"""CLI for Brazil election converse FT mini-study."""

from __future__ import annotations

import os
import sys
from pathlib import Path

_STUDY = Path(__file__).resolve().parent
_ARIES = _STUDY.parents[3]
_UBER = _STUDY.parent / "2026-10-26_uber-converse-cohort"
for _p in (_ARIES, _ARIES / "SWEP" / "src", _UBER, _STUDY):
    _s = str(_p)
    if _s not in sys.path:
        sys.path.insert(0, _s)
os.chdir(_STUDY)

import argparse


def main() -> None:
    p = argparse.ArgumentParser(description="Brazil election converse FT study")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("pags", help="PAGS reproduction only")
    pf = sub.add_parser("full", help="Full pipeline")
    pf.add_argument("--skip-historical", action="store_true")
    pr = sub.add_parser("report", help="Rebuild REPORT from output CSVs")
    ph = sub.add_parser("historical", help="Historical percentiles only (uses cache)")
    pbr = sub.add_parser("historical-shocks", help="Phase BR-2 shock registry and tests")
    pbr.add_argument("--recompute", action="store_true")
    pbr.add_argument("--placebos", type=int, default=200)
    pbr.add_argument("--skip-percentiles", action="store_true", help="Skip slow 250-session percentiles")
    pbr.add_argument("--percentiles-only", action="store_true", help="Only rebuild historical_c2c_percentiles.csv")
    pad = sub.add_parser("astrolog-debug", help="Oct 5 vs Oct 26 mirror tabs (sa_app astrolog -pd -1)")
    pad.add_argument("--ticker", action="append", help="Limit to ticker(s); default all except EBR")
    pag = sub.add_parser(
        "astrolog-aggregate",
        help="Sum qualifying Sun–Pluto aspect power (Oct 5 vs Oct 26); validate archive totals",
    )
    pag.add_argument(
        "--debug-dir",
        type=Path,
        default=_STUDY / "output" / "astrolog_debug",
        help="Directory with *_c2c.txt / *_c2r.txt",
    )
    pag.add_argument("--strict", action="store_true", help="Exit 1 if validation fails")
    pag.add_argument(
        "--study",
        choices=("election_2026", "covid_2020"),
        default="election_2026",
    )
    pc = sub.add_parser(
        "astrolog-covid-2020",
        help="Mar 12 vs Mar 24 2020 COVID dates @ 09:30 NY — mirror + aggregate",
    )
    pc.add_argument("--ticker", action="append", help="Limit tickers (default all except EBR)")
    pm = sub.add_parser(
        "market-reference",
        help="Phase 0: download EWZ OHLC (+ synthetic eq-weight fallback series)",
    )
    pm.add_argument("--start", default="2000-01-01")
    pm.add_argument("--end", default="2026-12-31")
    pm.add_argument("--force", action="store_true", help="Re-download all series")
    pm.add_argument("--no-ibovespa", action="store_true")
    pbr3 = sub.add_parser("aspect-matrices", help="Phase BR-3: C2C/C2R aspect-power matrices")
    pbr3.add_argument("--extremes", type=int, default=50)
    pbr3.add_argument("--recompute", action="store_true")
    args = p.parse_args()
    if args.cmd == "pags":
        from pags_reproduction import main_pags

        main_pags()
    elif args.cmd == "report":
        from brazil_pipeline import OUTPUT, write_report
        import pandas as pd
        from ft_registry import build_registry

        def _read_hist():
            p = OUTPUT / "historical_percentiles.csv"
            if not p.exists() or p.stat().st_size == 0:
                return pd.DataFrame()
            try:
                df = pd.read_csv(p)
            except pd.errors.EmptyDataError:
                return pd.DataFrame()
            return df if len(df.columns) else pd.DataFrame()

        write_report(
            build_registry(),
            pd.read_csv(OUTPUT / "event_ohlc_returns.csv"),
            pd.read_csv(OUTPUT / "cross_sectional_feature_matrix.csv"),
            _read_hist(),
            pd.read_csv(OUTPUT / "placebo_results.csv"),
        )
        from brazil_pipeline import _publish_outputs

        _publish_outputs()
    elif args.cmd == "astrolog-debug":
        from brazil_astrolog_debug import run_debug

        tickers = tuple(args.ticker) if args.ticker else None
        path = run_debug(tickers=tickers)
        print(f"Wrote {path}")
    elif args.cmd == "astrolog-aggregate":
        from astrolog_power_aggregate import build_report
        from astrolog_study_config import COVID_2020, ELECTION_2026

        study = ELECTION_2026 if args.study == "election_2026" else COVID_2020
        debug_dir = args.debug_dir.resolve() if args.debug_dir else None
        raise SystemExit(build_report(debug_dir, study=study, strict=args.strict))
    elif args.cmd == "astrolog-covid-2020":
        from astrolog_study_config import COVID_2020
        from run_astrolog_study import run_full_study

        tickers = tuple(args.ticker) if args.ticker else None
        study = COVID_2020
        if tickers:
            from dataclasses import replace

            study = replace(study, tickers=tickers)
        run_full_study(study)
    elif args.cmd == "market-reference":
        from datetime import date

        from brazil_market_reference import build_market_reference

        meta = build_market_reference(
            start=date.fromisoformat(args.start),
            end=date.fromisoformat(args.end),
            force=args.force,
            include_ibovespa=not args.no_ibovespa,
        )
        import json

        print(json.dumps(meta, indent=2))
    elif args.cmd == "aspect-matrices":
        from br3_pipeline import build_event_manifest, run_aspect_matrices
        import json

        build_event_manifest(extremes=args.extremes)
        result = run_aspect_matrices(extremes=args.extremes, recompute=args.recompute)
        print(json.dumps(result, indent=2))
    elif args.cmd == "historical-shocks":
        from brazil_paths import OUTPUT_BR2
        from br2_pipeline import run_br2
        from br2_percentiles import build_historical_percentiles
        import pandas as pd

        if args.percentiles_only:
            panel = pd.read_csv(OUTPUT_BR2 / "eligible_ticker_event_panel.csv")
            pct = build_historical_percentiles(panel, use_cache=not args.recompute)
            pct.to_csv(OUTPUT_BR2 / "historical_c2c_percentiles.csv", index=False)
        else:
            run_br2(
                recompute=args.recompute,
                placebos=args.placebos,
                skip_percentiles=args.skip_percentiles,
            )
    elif args.cmd == "historical":
        from brazil_pipeline import historical_percentiles, OUTPUT, write_report, run_full
        import pandas as pd
        from ft_registry import build_registry, ft_birth_jd

        reg = build_registry()
        ft_jds = {}
        for _, row in reg.iterrows():
            jd, ok = ft_birth_jd(row)
            if ok and jd:
                ft_jds[row["ticker"]] = jd
        hist = historical_percentiles(ft_jds, reg)
        hist.to_csv(OUTPUT / "historical_percentiles.csv", index=False)
        write_report(
            reg,
            pd.read_csv(OUTPUT / "event_ohlc_returns.csv"),
            pd.read_csv(OUTPUT / "cross_sectional_feature_matrix.csv"),
            hist,
            pd.read_csv(OUTPUT / "placebo_results.csv"),
        )
        from brazil_pipeline import _publish_outputs

        _publish_outputs()
    else:
        from brazil_pipeline import run_full

        run_full(skip_historical=args.skip_historical)


if __name__ == "__main__":
    main()
