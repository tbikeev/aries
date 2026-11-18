#!/usr/bin/env python3
"""Phase H — final diagnostics, placebos, hypothesis freeze (exploratory)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from phase_h1_gap import run_h1
from phase_h2_placebos import (
    run_event_alignment_placebos,
    run_random_surrogate_placebos,
    run_shifted_radix_placebos,
)
from phase_h3_composition import run_h3
from phase_h4_incremental import run_h4
from phase_h_data import event_jd_series, load_earnings_panel
from phase_h_paths import PHASE_H_OUTPUT, PLACEBO_SURROGATE_COUNT


def run_phase_h(
    output_dir: Path | None = None,
    *,
    n_surrogates: int = PLACEBO_SURROGATE_COUNT,
) -> dict:
    out = output_dir or PHASE_H_OUTPUT
    out.mkdir(parents=True, exist_ok=True)

    df = load_earnings_panel()
    df.to_csv(out / "h0_earnings_panel_frozen.csv", index=False)
    events = event_jd_series(df)

    h1_corr, h1_events, h1_timing, h1_conc = run_h1(df)
    h1_corr.to_csv(out / "h1_correlation_matrix.csv", index=False)
    h1_events.to_csv(out / "h1_event_level.csv", index=False)
    h1_timing.to_csv(out / "h1_timing_subgroups.csv", index=False)

    shift_df = run_shifted_radix_placebos(df, events)
    shift_df.to_csv(out / "h2_shifted_radix_placebos.csv", index=False)
    sur_long, sur_summary = run_random_surrogate_placebos(df, events, n_surrogates=n_surrogates)
    sur_long.to_csv(out / "h2_random_surrogate_correlations.csv", index=False)
    align_df, align_summary = run_event_alignment_placebos(df, events)
    align_df.to_csv(out / "h2_event_alignment_controls.csv", index=False)

    h3_detail, h3_pairs, h3_totals = run_h3()
    h3_detail.to_csv(out / "h3_dk_square_contacts.csv", index=False)
    h3_pairs.to_csv(out / "h3_dk_square_pairs.csv", index=False)
    h3_totals.to_csv(out / "h3_dk_square_totals.csv", index=False)

    h4 = run_h4(df)
    h4_gap = run_h4(df, target="r_gap_pct")
    h4_intra = run_h4(df, target="r_intra_pct")

    freeze = {
        "status": "frozen_exploratory_hypotheses",
        "as_of_utc": datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + "Z",
        "primary_directional": "DK converse major-square count at orb 1.0° on earnings-reaction sessions",
        "secondary_density": "All-cohort tight major-aspect count at orb 1.0° on earnings-reaction sessions",
        "cohort_specificity": "Retain FT/INC/DK separately; do not pool squares without preregistration",
        "event_scope": "Earnings-reaction days only until prospective OOS earnings validate",
        "daily_panel_finding": "No meaningful DK square association on ordinary days (see daily-study Report G)",
        "forbidden_until_oos": [
            "New aspect combinations from mining",
            "Orb threshold tuning beyond {0.5°, 1.0°}",
            "DK birth-time optimization",
        ],
    }
    (out / "hypothesis_freeze.json").write_text(json.dumps(freeze, indent=2), encoding="utf-8")

    summary = {
        "exploratory": True,
        "n_earnings": len(df),
        "cc_identity_max_err_bps": float(df["cc_identity_err_bps"].max()),
        "h1_conclusion": h1_conc,
        "h2_shifted_radix": shift_df.to_dict(orient="records"),
        "h2_random_surrogate_summary": sur_summary,
        "h2_event_alignment": align_summary,
        "h4_incremental_cc": h4,
        "h4_incremental_gap": h4_gap,
        "h4_incremental_intra": h4_intra,
        "hypothesis_freeze": freeze,
    }
    (out / "phase_h_summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    _write_reports(out, h1_corr, h1_conc, h1_timing, shift_df, sur_summary, align_summary, h3_pairs, h3_totals, h4, freeze)
    return summary


def _write_reports(out, h1_corr, h1_conc, h1_timing, shift_df, sur_summary, align_summary, h3_pairs, h3_totals, h4, freeze):
    dk_rows = h1_corr[h1_corr["feature"].str.startswith("DK_sq_count_orb10")]
    md_h1 = [
        "# Report H1 — Gap vs intraday decomposition (exploratory)",
        "",
        f"CC identity check max error (bps): see h0 panel.",
        "",
        "## DK square count @ 1° — conclusion",
        "",
        json.dumps(h1_conc, indent=2),
        "",
        "## All frozen feature × target correlations",
        "",
        _md(h1_corr),
        "",
        "## Timing subgroups (unstable if n small)",
        "",
        _md(h1_timing),
    ]
    (out / "REPORT_H1_gap_intraday.md").write_text("\n".join(md_h1), encoding="utf-8")

    md_h2 = [
        "# Report H2 — Genuine cohort vs placebos (exploratory)",
        "",
        "## Shifted radix (Design A)",
        "",
        _md(shift_df),
        "",
        "## Random surrogate rank (Design B)",
        "",
        "```json",
        json.dumps(sur_summary, indent=2),
        "```",
        "",
        "## Event alignment (Design C)",
        "",
        "```json",
        json.dumps(align_summary, indent=2),
        "```",
    ]
    (out / "REPORT_H2_placebos.md").write_text("\n".join(md_h2), encoding="utf-8")

    md_h3 = [
        "# Report H3 — DK square composition (orb ≤1°)",
        "",
        "## Top converse→radix square pairs",
        "",
        _md(h3_pairs.head(20)),
        "",
        "## Totals by planet / class",
        "",
        _md(h3_totals),
    ]
    (out / "REPORT_H3_composition.md").write_text("\n".join(md_h3), encoding="utf-8")

    md_h4 = [
        "# Report H4 — Incremental FT/INC beyond DK (exploratory)",
        "",
        "```json",
        json.dumps(h4, indent=2),
        "```",
        "",
        "# Hypothesis freeze",
        "",
        "```json",
        json.dumps(freeze, indent=2),
        "```",
    ]
    (out / "REPORT_H4_incremental_and_freeze.md").write_text("\n".join(md_h4), encoding="utf-8")


def _md(df: pd.DataFrame) -> str:
    try:
        return df.to_markdown(index=False)
    except Exception:
        return df.to_csv(index=False)


if __name__ == "__main__":
    print(json.dumps(run_phase_h(), indent=2))
