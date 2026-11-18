#!/usr/bin/env python3
"""Run mirror debug + price fetch + power aggregate for a study preset."""

from __future__ import annotations

from astrolog_study_config import COVID_2020, ELECTION_2026, StudyConfig
from astrolog_power_aggregate import build_report
from brazil_astrolog_debug import run_debug
from event_day_returns import write_event_returns


def run_full_study(study: StudyConfig, *, strict: bool = False) -> None:
    print(f"Mirror debug → {study.output_dir}")
    html = run_debug(study=study)
    print(f"Wrote {html}")
    ret_path = study.output_dir / "event_day_returns.csv"
    print(f"Fetching returns → {ret_path}")
    write_event_returns(study, ret_path)
    print("Aggregating power…")
    build_report(study.output_dir, study=study, strict=strict)


if __name__ == "__main__":
    import sys

    preset = sys.argv[1] if len(sys.argv) > 1 else "covid_2020"
    cfg = COVID_2020 if preset == "covid_2020" else ELECTION_2026
    run_full_study(cfg)
