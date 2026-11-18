"""Phase BR-2 orchestration."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from brazil_paths import CACHE_BR2, OUTPUT_BR2
from br2_analysis import (
    c2c_vs_c2r_comparison,
    cross_section_summary,
    cross_sectional_abnormal_results,
    episode_independent_subsample,
    market_direction_results,
    walk_forward_episode_results,
)
from br2_panel import STABLE_SUBUNIVERSE, build_eligible_panel, resolve_ft_jd
from br2_percentiles import build_historical_percentiles
from br2_placebos import run_placebos
from br2_shock_registry import build_historical_shock_registry
from ft_registry import build_registry


def run_br2(*, recompute: bool = False, placebos: int = 200, skip_percentiles: bool = False) -> None:
    OUTPUT_BR2.mkdir(parents=True, exist_ok=True)
    CACHE_BR2.mkdir(parents=True, exist_ok=True)
    panel_path = OUTPUT_BR2 / "eligible_ticker_event_panel.csv"

    shocks, episodes = build_historical_shock_registry()
    shocks.to_csv(OUTPUT_BR2 / "historical_shock_registry.csv", index=False)
    episodes.to_csv(OUTPUT_BR2 / "shock_episode_registry.csv", index=False)

    if recompute or not panel_path.exists():
        panel = build_eligible_panel(shocks, use_cache=not recompute)
        panel.to_csv(panel_path, index=False)
    else:
        panel = pd.read_csv(panel_path)

    if skip_percentiles:
        pct = pd.DataFrame()
    else:
        pct_path = OUTPUT_BR2 / "historical_c2c_percentiles.csv"
        if recompute or not pct_path.exists():
            pct = build_historical_percentiles(panel, use_cache=not recompute)
            pct.to_csv(pct_path, index=False)
        else:
            pct = pd.read_csv(pct_path)
        panel = panel.merge(pct, on=["ticker", "event_date"], how="left", suffixes=("", "_pct"))

    mkt = market_direction_results(panel, pct if not pct.empty else None)
    # Stable sub-universe robustness
    stable = panel[panel["ticker"].isin(STABLE_SUBUNIVERSE)]
    if not stable.empty:
        mkt_s = market_direction_results(stable, None)
        mkt_s["sample"] = mkt_s["sample"].astype(str) + "_stable5"
        mkt = pd.concat([mkt, mkt_s], ignore_index=True)
    ep_ind = episode_independent_subsample(panel)
    mkt = pd.concat([mkt, ep_ind], ignore_index=True)
    mkt.to_csv(OUTPUT_BR2 / "market_direction_results.csv", index=False)

    xs = cross_sectional_abnormal_results(panel)
    xs.to_csv(OUTPUT_BR2 / "cross_sectional_abnormal_results.csv", index=False)
    xs_sum = cross_section_summary(xs)

    cmp_df = c2c_vs_c2r_comparison(panel)
    cmp_df.to_csv(OUTPUT_BR2 / "c2c_vs_c2r_comparison.csv", index=False)

    wf = walk_forward_episode_results(panel)
    wf.to_csv(OUTPUT_BR2 / "walk_forward_episode_results.csv", index=False)

    ft_jds = {}
    for _, row in build_registry().iterrows():
        jd, strict, _ = resolve_ft_jd(row)
        if jd:
            ft_jds[row["ticker"]] = jd
    placebo = run_placebos(panel, ft_jds, n_surrogates=placebos)
    placebo.to_csv(OUTPUT_BR2 / "placebo_c2c_results.csv", index=False)

    write_br2_report(shocks, episodes, panel, mkt, xs, xs_sum, cmp_df, wf, placebo, pct)


def write_br2_report(shocks, episodes, panel, mkt, xs, xs_sum, cmp_df, wf, placebo, pct) -> None:
    from br2_features import planet_set_documentation

    n_dates = shocks["event_date"].nunique()
    n_ep = episodes["episode_id"].nunique()
    val_ep = shocks[shocks["validation_eligible"]]["event_date"].nunique()
    xs_sum = xs_sum or {}
    genuine = placebo[placebo["placebo_type"] == "genuine"]["primary_pearson_r"].iloc[0]
    rnd = placebo[placebo["placebo_type"] == "random_ft_jd"]
    p_val = float(rnd["empirical_p_two_sided_vs_genuine"].iloc[0]) if len(rnd) else float("nan")

    val_mkt = mkt[mkt["sample"] == "validation_excl_2026_10_26"]
    c2c_r = val_mkt[val_mkt["feature"] == "mean_c2c_hard"]["pearson_r"]
    crash_rally = val_mkt[val_mkt["feature"] == "mean_c2c_hard_crash_vs_rally"]

    lines = [
        "# Phase BR-2 — Historical Brazilian shocks",
        "",
        planet_set_documentation(),
        "",
        f"- Unique shock **dates** in registry: **{n_dates}**",
        f"- Independent **episodes** (clustered): **{n_ep}**",
        f"- Validation-eligible dates (excl. 2026-10-26 discovery): **{val_ep}**",
        f"- Panel rows (ticker×date): **{len(panel)}**",
        "",
        "## Decision questions",
        "",
        f"1. **C2C higher in crashes than rallies?** "
        f"Validation Pearson(mean C2C hard, EWZ): **{c2c_r.iloc[0] if len(c2c_r) else 'n/a'}**. "
        f"Crash−rally mean C2C hard: **{crash_rally['crash_mean'].iloc[0] if len(crash_rally) else 'n/a'}** vs "
        f"**{crash_rally['rally_mean'].iloc[0] if len(crash_rally) else 'n/a'}**.",
        "2. **Survives excluding Oct 2026 election?** Validation sample excludes 2026-10-26; "
        f"2026-10-05 remains in validation (same cycle — interpret cautiously).",
        f"3. **Genuine FT vs random FT?** Genuine r={genuine:.3f}; random-FT empirical p≈{p_val:.3f}.",
        f"4. **C2C vs C2R?** See `c2c_vs_c2r_comparison.csv` (validation episodes).",
        "5. **Independent episodes?** See `one_day_per_episode_min_ewz` row in market_direction_results.",
        f"6. **Cross-sectional abnormal vs C2C?** Median episode Spearman: **{xs_sum.get('median_spearman_across_episodes', 'n/a')}**; "
        f"negative episodes: **{xs_sum.get('n_negative_assoc', 'n/a')}** / **{xs_sum.get('n_episodes', 'n/a')}**.",
        f"7. **Walk-forward directional accuracy?** "
        f"Mean hit rate: **{wf['correct'].mean() if len(wf) else float('nan'):.2f}** over **{len(wf)}** expanding-window steps.",
        "8. **Reproducible signal?** Treat negative answers on 3–7 as failure to generalize the 2026 C2C pattern.",
        "",
        "## Artifacts",
        "",
        "All CSVs under `output/br2/`. Discovery date 2026-10-26 included in descriptive panels only; "
        "validation metrics exclude it by construction.",
        "",
        "## Strict vs approximate FT",
        "",
        f"Strict-timestamp rows: **{int(panel['strict_ft_timestamp'].sum()) if 'strict_ft_timestamp' in panel else 'n/a'}** / {len(panel)}",
    ]
    (OUTPUT_BR2 / "REPORT_BR2_HISTORICAL_SHOCKS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
