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

from brazil_pipeline import run_full
from pags_reproduction import main_pags


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
    args = p.parse_args()
    if args.cmd == "pags":
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
        run_full(skip_historical=args.skip_historical)


if __name__ == "__main__":
    main()
