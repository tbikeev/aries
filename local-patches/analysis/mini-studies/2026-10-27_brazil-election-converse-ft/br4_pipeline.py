"""BR-4 orchestration: cell differentials on coverage-controlled matrices."""

from __future__ import annotations

import pandas as pd

from brazil_paths import STUDY_ROOT
from br4_constants import CONTROLLED_DIR, OUTPUT_BR4
from br4_differences import build_c2c_tables, build_c2r_tables, load_controlled
from br4_heatmaps import write_cell_heatmaps
from br4_rankings import build_rankings
from br4_uncertainty import add_uncertainty_c2c, add_uncertainty_c2r
from br4_report import write_br4_report
from br4_validate_controlled import validate_controlled_extraction


def run_br4(*, skip_uncertainty: bool = False) -> dict:
    ind = CONTROLLED_DIR / "individual_aspect_matrices.npz"
    manifest_path = CONTROLLED_DIR / "event_manifest.parquet"
    if not ind.is_file():
        raise FileNotFoundError(f"Run aspect-matrices first: missing {ind}")

    validation = validate_controlled_extraction(sensitivity_dir=STUDY_ROOT / "output" / "br3")
    data = load_controlled(ind, manifest_path)

    c2c_p, c2c_t = build_c2c_tables(data, exclude_discovery=False)
    c2r_p, c2r_t = build_c2r_tables(data, exclude_discovery=False)
    c2c_p_nodisc, _ = build_c2c_tables(data, exclude_discovery=True)
    c2r_p_nodisc, _ = build_c2r_tables(data, exclude_discovery=True)
    OUTPUT_BR4.mkdir(parents=True, exist_ok=True)
    c2c_p.to_parquet(OUTPUT_BR4 / "c2c_cell_differences.parquet", index=False)
    c2r_p.to_parquet(OUTPUT_BR4 / "c2r_cell_differences.parquet", index=False)
    pd.concat([c2c_t, c2r_t], ignore_index=True).to_parquet(OUTPUT_BR4 / "ticker_cell_differences.parquet", index=False)

    if skip_uncertainty:
        unc = pd.DataFrame()
    else:
        unc_parts = [
            add_uncertainty_c2c(data, c2c_p, exclude_discovery=False),
            add_uncertainty_c2c(data, c2c_p_nodisc, exclude_discovery=True),
            add_uncertainty_c2r(data, c2r_p, exclude_discovery=False),
            add_uncertainty_c2r(data, c2r_p_nodisc, exclude_discovery=True),
        ]
        unc = pd.concat(unc_parts, ignore_index=True)
        unc.to_parquet(OUTPUT_BR4 / "cell_uncertainty.parquet", index=False)

    crash_rank, rally_rank = build_rankings(
        c2c_p,
        c2r_p,
        unc if not unc.empty else pd.DataFrame(),
        c2c_no_discovery=c2c_p_nodisc,
        c2r_no_discovery=c2r_p_nodisc,
    )
    crash_rank.to_csv(OUTPUT_BR4 / "ranked_crash_cells.csv", index=False)
    rally_rank.to_csv(OUTPUT_BR4 / "ranked_rally_cells.csv", index=False)

    write_cell_heatmaps(
        OUTPUT_BR4 / "cell_heatmaps.html",
        c2c_p,
        c2r_p,
        controlled_dir=CONTROLLED_DIR,
        ticker_cells=pd.concat([c2c_t, c2r_t], ignore_index=True),
    )
    write_br4_report(c2c_p, c2r_p, unc, crash_rank, rally_rank, validation)
    report = OUTPUT_BR4 / "REPORT_BR4_CELL_DIFFERENCES.md"

    return {
        "validation": validation,
        "report": str(report),
        "output_dir": str(OUTPUT_BR4),
    }


def run_br4_with_extraction(*, recompute: bool = False) -> dict:
    from br3_pipeline import run_aspect_matrices

    run_aspect_matrices(
        extremes=50,
        recompute=recompute,
        manifest_path=STUDY_ROOT / "output" / "br3_5" / "event_manifest_coverage_controlled.parquet",
        output_subdir="br3_5_controlled",
    )
    return run_br4()
