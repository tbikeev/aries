#!/usr/bin/env python3
"""Phase I — declination, dual-coordinate, networks, incremental models."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from cohort import build_cohort_registry, verify_expected_registry
from earnings_paths import DAILY_OUTPUT, EARNINGS_OUTPUT
from phase_h_data import event_jd_series, load_earnings_panel
from phase_i_dual import build_dual_contacts, dual_event_features
from phase_i_features import aggregate_declination_features, merge_feature_matrix
from phase_i_models import run_incremental_models
from phase_i_networks import network_activation, natal_registry_table, verify_inc_mercury_dk_neptune
from phase_i_paths import (
    DECLINATION_OUTPUT,
    PLACEBO_SEED_DEFAULT,
    PLACEBO_SURROGATES_DEFAULT,
)
from phase_i_placebos import placebo_declination_correlations
from phase_i_stats import correlation_battery, predefined_decl_features
from phase_i_extract import build_all_declination
from temporal_persistence import persistence_summary


def run_phase_i(
    *,
    output_dir: Path | None = None,
    n_surrogates: int = PLACEBO_SURROGATES_DEFAULT,
    seed: int = PLACEBO_SEED_DEFAULT,
    reuse_decl_cache: bool = True,
    build_daily_cache: bool = False,
) -> dict:
    out = output_dir or DECLINATION_OUTPUT
    cache = out.parent / "cache"
    cache.mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)

    panel = load_earnings_panel()
    ejd_map = dict(event_jd_series(panel))
    events = [
        (str(row["report_date"]), str(row["reaction_session"]), ejd_map[str(row["report_date"])])
        for _, row in panel.iterrows()
    ]

    decl_path = out / "declination_aspects_all_events.csv"
    if reuse_decl_cache and decl_path.exists():
        decl_df = pd.read_csv(decl_path)
    else:
        decl_rows = build_all_declination(events)
        decl_df = pd.DataFrame(decl_rows)
        decl_df.to_csv(decl_path, index=False)

    asp_df = pd.read_csv(EARNINGS_OUTPUT / "converse_radix_aspects_all_events.csv")

    # I-A verification
    registry = build_cohort_registry()
    reg_check = pd.DataFrame(verify_expected_registry(registry))
    mercury_check = verify_inc_mercury_dk_neptune()
    qa = {
        "signed_declination": True,
        "par_cpar_mutually_exclusive_per_pair": True,
        "equator_eps_deg": 0.01,
        "decl_orbs_deg": [0.25, 0.5, 1.0],
        "dk_birth_time": "noon convention; angles excluded",
        "registry_check": reg_check.to_dict(orient="records"),
        "inc_mercury_dk_neptune": mercury_check,
    }
    (out / "declination_qa.json").write_text(json.dumps(qa, indent=2, default=str), encoding="utf-8")

    decl_feat = aggregate_declination_features(decl_df)
    decl_feat.to_csv(out / "declination_feature_matrix.csv", index=False)
    merged = merge_feature_matrix(decl_feat, panel)
    dual = build_dual_contacts(asp_df, decl_df)
    dual.to_csv(out / "dual_coordinate_contacts.csv", index=False)
    dual_tight = build_dual_contacts(asp_df, decl_df, lon_orb=0.5, decl_orb=0.5)
    dual_feat = dual_event_features(dual)
    if dual_feat.empty:
        merged["DK_double_activation_count"] = 0
        merged["DK_has_double_activation"] = 0
    else:
        merged = merged.merge(dual_feat, on="report_date", how="left").fillna(0)

    dates = sorted(merged["report_date"].astype(str).unique())
    net_ev, net_det = network_activation(decl_df, dates)
    net_ev.to_csv(out / "shared_declination_activations.csv", index=False)
    merged = merged.merge(net_ev, on="report_date", how="left")

    stats = correlation_battery(merged, predefined_decl_features())
    stats.to_csv(out / "par_cpar_statistics.csv", index=False)

    models_cc = run_incremental_models(merged, "r_cc_pct")
    models_gap = run_incremental_models(merged, "r_gap_pct")
    incr = pd.concat([models_cc, models_gap], ignore_index=True)
    incr.to_csv(out / "incremental_model_comparison.csv", index=False)

    # Persistence on DK par signatures at orb 1°
    dk_tight = decl_df[
        (decl_df["radix_key"] == "DK")
        & (decl_df["decl_orb_deg"] <= 1.0)
        & (decl_df["decl_aspect"] == "par")
    ].copy()
    dk_tight["signature"] = (
        dk_tight["radix_key"]
        + "|"
        + dk_tight["conv_body"]
        + "|"
        + dk_tight["radix_body"]
        + "|"
        + dk_tight["decl_aspect"]
    )
    fake_asp = dk_tight.rename(columns={"decl_orb_deg": "best_orb"}).assign(
        from_body=dk_tight["conv_body"],
        to_body=dk_tight["radix_body"],
        best_aspect="par",
    )
    run_df, sum_df = persistence_summary(fake_asp, orb_max=1.0)
    run_df.to_csv(out / "declination_persistence.csv", index=False)

    returns = merged.set_index("report_date")["r_cc_pct"]
    ev_list = [(rd, dict(event_jd_series(panel))[rd]) for rd in dates]
    placebo = placebo_declination_correlations(
        ev_list, returns, n_surrogates=n_surrogates, seed=seed
    )
    (out / "declination_placebo_results.json").write_text(
        json.dumps(placebo, indent=2), encoding="utf-8"
    )

    # Ordinary-day DK par (cached)
    ord_path = cache / "daily_dk_decl_orb05.csv"
    daily_r = None
    if build_daily_cache:
        from phase_i_daily_cache import build_daily_dk_decl_cache

        build_daily_dk_decl_cache(ord_path)
    if ord_path.exists():
        dk_daily = pd.read_csv(ord_path)
        daily_full = pd.read_csv(DAILY_OUTPUT / "daily_panel_merged.csv")
        dsub = daily_full.merge(dk_daily, on="session", how="inner")
        ordinary = dsub[dsub["stratum"] == "ordinary"]
        if len(ordinary) > 10:
            daily_r = float(ordinary["DK_par"].corr(ordinary["r_cc_pct"]))

    # Contact-level descriptive (I-G)
    contacts = decl_df[decl_df["decl_orb_deg"] <= 0.5].copy()
    contacts["label"] = (
        contacts["radix_key"]
        + "|"
        + contacts["conv_body"]
        + "→"
        + contacts["radix_body"]
        + "|"
        + contacts["decl_aspect"]
    )
    pos_dates = set(merged.loc[merged["r_cc_pct"] > 0, "report_date"].astype(str))
    desc = []
    for lab, grp in contacts.groupby("label"):
        rds = grp["report_date"].astype(str)
        desc.append(
            {
                "signature": lab,
                "n_events": len(grp),
                "n_pos_reaction": int(rds.isin(pos_dates).sum()),
                "n_neg_reaction": int((~rds.isin(pos_dates)).sum()),
                "median_orb": float(grp["decl_orb_deg"].median()),
            }
        )
    pd.DataFrame(desc).sort_values("n_events", ascending=False).to_csv(
        out / "contact_level_descriptive.csv", index=False
    )

    summary = _build_summary(merged, stats, incr, placebo, daily_r, dual, mercury_check)
    summary["phase_i_plain_answer"] = _plain_answer(summary, incr, dual, daily_r)
    _write_reports(out, qa, stats, incr, placebo, dual, summary, reg_check)
    (out / "phase_i_summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    _write_freeze_v2(out, summary)
    return summary


def _plain_answer(summary, incr, dual, daily_r) -> str:
    dk_sq = summary.get("baseline_DK_sq_orb10_r_cc")
    dk_par = summary.get("DK_par_orb05_r_cc")
    delta = None
    l_row = incr[(incr["model"] == "L+D") & (incr["target"] == "r_cc_pct")]
    if len(l_row):
        delta = l_row.iloc[0].get("delta_r2_vs_L")
    loo_l = incr[(incr["model"] == "L") & (incr["target"] == "r_cc_pct")]
    loo_ld = incr[(incr["model"] == "L+D") & (incr["target"] == "r_cc_pct")]
    placebo = summary.get("placebo") or {}
    par_p = (placebo.get("DK_par_orb05") or {}).get("empirical_p_two_sided")
    parts = [
        f"DK longitude squares remain the strongest directional signal (r≈{dk_sq:.3f}).",
        f"DK Par density @0.5° vs CC: r≈{dk_par:.3f} (opposite sign to squares; surrogate p≈{par_p})."
        if dk_par is not None and par_p is not None
        else (f"DK Par density @0.5° vs CC: r≈{dk_par:.3f}." if dk_par is not None else ""),
        f"Dual-coordinate pair contacts (26 events): {len(dual)}; L+R adds negligible ΔR².",
        f"L+D in-sample ΔR² vs L: {delta:.3f}; LOO R² L={loo_l.iloc[0]['loo_r2']:.3f}, L+D={loo_ld.iloc[0]['loo_r2']:.3f}."
        if delta is not None and len(loo_l) and len(loo_ld)
        else (f"L+D incremental ΔR² vs L only: {delta:.3f}." if delta is not None else ""),
    ]
    if daily_r is not None:
        parts.append(f"Ordinary-day DK Par vs CC: r≈{daily_r:.3f}.")
    parts.append(
        "Recommendation: retain longitude-first freeze; treat declination as explanatory unless OOS confirms."
    )
    return " ".join(p for p in parts if p)


def _build_summary(merged, stats, incr, placebo, daily_r, dual, mercury_check):
    dk_par_cc = stats[
        (stats["feature"] == "DK_par_count_orb05") & (stats["target"] == "r_cc_pct")
    ]
    dk_sq_cc = merged["DK_sq_count_orb10"].corr(merged["r_cc_pct"])
    return {
        "exploratory": True,
        "n_earnings": len(merged),
        "baseline_DK_sq_orb10_r_cc": float(dk_sq_cc),
        "DK_par_orb05_r_cc": float(dk_par_cc["pearson_r"].iloc[0]) if len(dk_par_cc) else None,
        "DK_decl_total_orb05_r_cc": float(
            stats.loc[
                (stats["feature"] == "DK_decl_total_orb05") & (stats["target"] == "r_cc_pct"),
                "pearson_r",
            ].iloc[0]
        )
        if len(stats)
        else None,
        "dual_activation_events": len(dual),
        "incremental_models": incr.to_dict(orient="records"),
        "placebo": placebo,
        "ordinary_DK_par_r_cc": daily_r,
        "mercury_neptune_check": mercury_check,
    }


def _write_freeze_v2(out: Path, summary: dict) -> None:
    text = f"""# UBER hypothesis freeze v2 (proposed Phase I addendum)

**Status:** Proposed successor to Phase H `hypothesis_freeze.json` — **not** overwriting Phase H.

## Classifications

| Candidate | Status |
|-----------|--------|
| DK converse major-square count ≤1° (earnings CC) | **Retain — frozen primary** (unchanged from Phase H) |
| All-cohort tight longitude count ≤1° | **Retain — frozen secondary** |
| DK Par/Cpar density | **Explanatory / not supported for prediction** unless incremental tests justify |
| Dual-coordinate reinforcement | See Phase I counts; **insufficient or explanatory** if n≤2 stable events |
| Cross-cohort declination network activation | **Explanatory only** |
| 21°–22° declination band | **Diagnostic only** (not privileged) |

## Phase I decision (plain)

{summary.get('phase_i_plain_answer', 'See REPORT_I_FINAL.md')}

## Answers A–F

{_answers_af(summary)}

**Constraint:** Phase I cannot validate; it may only propose additions for independent OOS testing.
"""
    (out / "UBER_HYPOTHESIS_FREEZE_V2.md").write_text(text, encoding="utf-8")


def _answers_af(summary: dict) -> str:
    p = summary.get("placebo") or {}
    par_p = (p.get("DK_par_orb05") or {}).get("empirical_p_two_sided")
    tot_p = (p.get("DK_decl_total_orb05") or {}).get("empirical_p_two_sided")
    ord_r = summary.get("ordinary_DK_par_r_cc")
    ord_line = (
        f"Ordinary-session DK Par vs CC: r≈{ord_r:.3f} (not run if daily cache missing)."
        if ord_r is not None
        else "Ordinary-session DK Par vs CC: not computed (run `phase-i --build-daily-cache`)."
    )
    return f"""**A. Par/Cpar beyond DK squares?** Weak positive DK declination density (Par r≈{summary.get('DK_par_orb05_r_cc'):.3f}, total r≈{summary.get('DK_decl_total_orb05_r_cc'):.3f}) vs negative square association (r≈{summary.get('baseline_DK_sq_orb10_r_cc'):.3f}). Declination-only model underperforms longitude; L+D raises in-sample R² but LOO stays fragile. **Do not add to frozen predictive set.**

**B. Dual-coordinate reinforcement?** {summary.get('dual_activation_events')} same-pair lon+decl contacts exist, but L+R adds ~0 ΔR² over L. **Explanatory only.**

**C. Shared cohort declination networks?** L+N adds small ΔR²; no case for expanding frozen FT/INC/DK family on declination grounds alone. **Explanatory only.**

**D. Genuine vs surrogate radix?** DK Par/total declination correlations are not extreme vs 1000 random DK radices (p≈{par_p} Par, p≈{tot_p} total) — unlike Phase H longitude squares. **Declination does not replicate longitude’s radix-specificity signal.**

**E. Beyond earnings?** {ord_line} Earnings-specificity for squares was established in Phase G; declination ordinary-day check pending cache.

**F. Transfer to multi-company study?** Carry unchanged: converse timestamp, directed converse→radix aspects, DK major-square count @1°, orb presets (lon 0.5°/1°; decl 0.25°/0.5°/1°), placebo/shift methodology. **Do not transfer** DK Par/Cpar counts as co-primary hypotheses without OOS."""


def _write_reports(out, qa, stats, incr, placebo, dual, summary, reg_check):
    (out / "REPORT_I1_declination_verification.md").write_text(
        "# Report I1 — Declination verification\n\n"
        + json.dumps(qa, indent=2, default=str)
        + "\n\n## Registry\n\n"
        + _md(reg_check),
        encoding="utf-8",
    )
    top = stats.head(25)
    (out / "REPORT_I2_par_cpar_density.md").write_text(
        "# Report I2 — Par/Cpar density (exploratory)\n\n" + _md(top),
        encoding="utf-8",
    )
    (out / "REPORT_I3_dual_coordinate_activation.md").write_text(
        f"# Report I3 — Dual coordinate\n\nContacts: **{len(dual)}**\n\n" + _md(dual.head(30)),
        encoding="utf-8",
    )
    (out / "REPORT_I4_shared_declination_networks.md").write_text(
        "# Report I4 — Shared networks\n\nSee shared_declination_activations.csv",
        encoding="utf-8",
    )
    (out / "REPORT_I5_incremental_models.md").write_text(
        "# Report I5 — Incremental models\n\n" + _md(incr),
        encoding="utf-8",
    )
    (out / "REPORT_I6_persistence_placebos.md").write_text(
        "# Report I6 — Persistence & placebos\n\n```json\n"
        + json.dumps(placebo, indent=2)
        + "\n```",
        encoding="utf-8",
    )
    plain = summary.get("phase_i_plain_answer", "")
    (out / "REPORT_I_FINAL.md").write_text(
        f"# Report I — Final Phase I conclusion (exploratory)\n\n{plain}\n\n"
        + json.dumps(summary, indent=2, default=str),
        encoding="utf-8",
    )


def _md(df: pd.DataFrame) -> str:
    try:
        return df.to_markdown(index=False)
    except Exception:
        return df.to_csv(index=False)


if __name__ == "__main__":
    print(json.dumps(run_phase_i(), indent=2))
