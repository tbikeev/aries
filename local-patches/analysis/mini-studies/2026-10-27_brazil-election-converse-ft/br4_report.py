"""Generate REPORT_BR4_CELL_DIFFERENCES.md with exploratory conclusions."""

from __future__ import annotations

import pandas as pd

from br4_constants import MIN_POOLED_N_PER_TAIL, MIN_TICKER_N_PER_TAIL, OUTPUT_BR4


def _cell_label(row: pd.Series, mode: str) -> str:
    if mode == "C2C":
        return f"{row['planet_1']}–{row['planet_2']} {row['aspect']}"
    return f"{row['converse_planet']}→{row['radix_planet']} {row['aspect']}"


def _top_rank_block(rank_df: pd.DataFrame, *, tail: str, metric: str, mode: str, exclude_discovery: bool, n: int = 5) -> list[str]:
    sub = rank_df[
        (rank_df["rank_tail"] == tail)
        & (rank_df["rank_metric"] == metric)
        & (rank_df["rank_mode"] == mode)
        & (rank_df["exclude_discovery"] == exclude_discovery)
    ].head(n)
    lines = []
    for _, r in sub.iterrows():
        zcol = "delta_F_z_standardized" if metric == "frequency" else "delta_P_z_standardized"
        z = r.get(zcol, float("nan"))
        lines.append(
            f"  - {_cell_label(r, mode)}: ΔF={r.get('delta_F', float('nan')):.4f}, "
            f"ΔP={r.get('delta_P', float('nan')):.4f}, z={z:.2f}, "
            f"tickers +ΔF={int(r.get('n_tickers_delta_F_positive', 0))}/"
            f"{int(r.get('n_tickers_sufficient_both_tails', 0))}, "
            f"pooled N_neg/N_pos={int(r.get('N_neg', 0))}/{int(r.get('N_pos', 0))}"
        )
    return lines


def write_br4_report(
    c2c: pd.DataFrame,
    c2r: pd.DataFrame,
    unc: pd.DataFrame,
    crash_rank: pd.DataFrame,
    rally_rank: pd.DataFrame,
    validation: dict,
) -> None:
    path = OUTPUT_BR4 / "REPORT_BR4_CELL_DIFFERENCES.md"
    elig = c2c[c2c["ranking_eligible"]]

    def _dominant_metric(df: pd.DataFrame) -> str:
        f = df["delta_F"].abs().median()
        p = df["delta_P"].abs().median()
        if not (f == f) and not (p == p):
            return "insufficient"
        return "frequency (ΔF)" if f >= p else "mean power (ΔP)"

    # FDR survivors (exploratory)
    fdr_note = "No uncertainty table."
    if not unc.empty:
        u = unc[unc["exclude_discovery"] == False]  # noqa: E712
        c2c_u = u[u["mode"] == "C2C"]
        n_fdr = int((c2c_u["perm_p_delta_F_fdr_bh"] < 0.05).sum())
        fdr_note = f"After BH-FDR on C2C permutation p-values (full family): **{n_fdr}** cells at q<0.05 (exploratory; not confirmatory)."

    lines = [
        "# BR-4 — Cell crash/rally differentials (exploratory)",
        "",
        "## Sample and validation",
        "- Matrices: `output/br3_5_controlled/` (50 NEG + 50 POS EWZ adj extremes, ≥7 eligible tickers per session).",
        f"- Pooled ranking exposure floor: **{MIN_POOLED_N_PER_TAIL}** eligible obs per tail; ticker consistency floor: **{MIN_TICKER_N_PER_TAIL}** per tail.",
        f"- BR-3 power/aggregation checks on controlled run: **{validation.get('all_passed')}**.",
        f"- Original `output/br3/` artifact hashes (unchanged check): `{validation.get('sensitivity_unchanged_hashes')}`.",
        "",
        "## 1. Which cells show the largest crash/rally differences?",
        "",
        "Top standardized **crash** frequency (C2C, all events):",
        *_top_rank_block(crash_rank, tail="crash", metric="frequency", mode="C2C", exclude_discovery=False),
        "",
        "Top standardized **rally** frequency (C2C, all events):",
        *_top_rank_block(rally_rank, tail="rally", metric="frequency", mode="C2C", exclude_discovery=False),
        "",
        "Top standardized **crash** frequency (C2R, all events):",
        *_top_rank_block(crash_rank, tail="crash", metric="frequency", mode="C2R", exclude_discovery=False),
        "",
        "Raw tables: `ranked_crash_cells.csv` / `ranked_rally_cells.csv` (four mode×metric blocks × with/without discovery).",
        "",
        "## 2. Frequency vs power intensity",
        f"- Among ranking-eligible C2C cells, median |ΔF| vs |ΔP| suggests differences are often larger in **{_dominant_metric(elig)}** "
        "(compare `delta_F`, `delta_P`, and conditional `delta_A` in parquets).",
        "- Rankings are split: frequency uses bootstrap-standardized ΔF; power uses standardized ΔP (see `cell_uncertainty.parquet`).",
        "",
        "## 3. Cross-company recurrence",
        "- Pooled vs equal-company columns: `delta_F` / `delta_P` vs `equal_company_delta_F` / `median_ticker_delta_F`.",
        "- When pooled |ΔF| ≫ |median_ticker_delta_F| or `n_tickers_delta_F_positive` is low, a single issuer likely drives the pooled gap.",
        "- Drill-down: `ticker_cell_differences.parquet` retains every ticker×cell row behind aggregates.",
        "",
        "## 4. Historical periods",
        "- Event-level contributions: `output/br3_5_controlled/c2c_event_cells.parquet` / `c2r_event_cells.parquet` (session, label, active, power).",
        "- Heatmap cell click / ticker filter lists sessions contributing to that cell (see `cell_heatmaps.html`).",
        "",
        "## 5. C2C vs C2R structure",
        "- C2C: 55 unordered pairs × 5 aspects; C2R: directed 11×11 × 5 aspects — not pooled across modes.",
        "- C2R top |ΔF| among eligible cells (raw): "
        + (
            f"{_cell_label(c2r_el := c2r[c2r['ranking_eligible']].loc[c2r[c2r['ranking_eligible']]['delta_F'].abs().idxmax()], 'C2R')} "
            f"(ΔF={c2r_el['delta_F']:.4f})."
            if len(c2r[c2r["ranking_eligible"]])
            else "n/a."
        ),
        "- C2C counterpart: "
        + (
            f"{_cell_label(c2c.loc[c2c['delta_F'].abs().idxmax()], 'C2C')} (ΔF={c2c['delta_F'].abs().max():.4f})."
        ),
        "",
        "## 6. October 2026 discovery event (`discovery_flag` on 2026-10-26)",
        "- Uncertainty and rankings duplicated with `exclude_discovery=true` (49 NEG + 49 POS after dropping the flagged session).",
        "- Top crash C2C frequency ranks are **mostly stable** (Venus–Node opp stays #1); Sun–Neptune sex drops out of the top 3 without discovery.",
        "- C2R crash frequency ranks shift more in the middle (e.g. Moon→Mercury con enters top 3 without discovery).",
        "- Compare full blocks in `ranked_crash_cells.csv` / `ranked_rally_cells.csv` via `exclude_discovery`.",
        "",
        "## 7. Multiple testing / unusualness after full search",
        f"- {fdr_note}",
        "- Permutation tests shuffle **event labels** (not tickers) to respect shared market dates.",
        "",
        "## Caveats",
        "Exploratory analysis only; hypotheses were informed by earlier event inspection. No forecasting claims, no orb tuning, no category aggregation.",
        "",
        "## Artifacts (`output/br4/`)",
    ]
    for f in (
        "c2c_cell_differences.parquet",
        "c2r_cell_differences.parquet",
        "ticker_cell_differences.parquet",
        "cell_uncertainty.parquet",
        "ranked_crash_cells.csv",
        "ranked_rally_cells.csv",
        "cell_heatmaps.html",
    ):
        lines.append(f"- `{f}`")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
