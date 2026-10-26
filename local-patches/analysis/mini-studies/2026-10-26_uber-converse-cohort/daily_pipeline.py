#!/usr/bin/env python3
"""Daily UBER converse panel (frozen hypothesis set from earnings discovery)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from daily_episodes import build_activation_episodes
from daily_features import compute_daily_features
from daily_market import build_daily_panel, load_earnings_reaction_sessions
from daily_validation import (
    FROZEN_DAILY_COLUMNS,
    chronological_split_correlation,
    circular_shift_permutation,
    episode_adjusted_n,
    label_strata,
    max_stat_search_permutation,
    stratum_correlations,
)
from earnings_paths import DAILY_OUTPUT, EARNINGS_OUTPUT, FROZEN_ORB_THRESHOLDS_DEG, resolve_ohlc_csv
from market_reactions import load_ohlc_csv


def run_daily_study(
    *,
    ohlc_csv: Path | None = None,
    earnings_reactions_csv: Path | None = None,
    output_dir: Path | None = None,
    reuse_features: bool = True,
) -> dict:
    out = output_dir or DAILY_OUTPUT
    out.mkdir(parents=True, exist_ok=True)
    opath = resolve_ohlc_csv(ohlc_csv)
    ereact = earnings_reactions_csv or (EARNINGS_OUTPUT / "earnings_reactions_all.csv")

    settings = {
        "ohlc_csv": str(opath),
        "earnings_reactions_csv": str(ereact),
        "frozen_orb_deg": list(FROZEN_ORB_THRESHOLDS_DEG),
        "frozen_features": FROZEN_DAILY_COLUMNS,
        "converse_event_time": "09:30 America/New_York",
        "discovery_stage_frozen": "earnings-study/ (N=26); daily panel is first out-of-discovery-scale test",
        "run_utc": datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + "Z",
    }
    (out / "run_settings.json").write_text(json.dumps(settings, indent=2), encoding="utf-8")

    ohlc = load_ohlc_csv(opath)
    panel = build_daily_panel(ohlc)
    panel.to_csv(out / "daily_market_panel.csv", index=False)

    feat_path = out / "daily_converse_features.csv"
    slow_path = out / "daily_slow_signatures_long.csv"
    if reuse_features and feat_path.exists() and slow_path.exists():
        feat_df = pd.read_csv(feat_path)
        slow_long = pd.read_csv(slow_path)
    else:
        feat_df, slow_long = compute_daily_features(panel)
        feat_df.to_csv(feat_path, index=False)
        slow_long.to_csv(slow_path, index=False)

    merged = panel.merge(feat_df, on="session", how="inner")
    earnings_days = load_earnings_reaction_sessions(ereact)
    merged = label_strata(merged, earnings_days)
    session_order = merged.sort_values("session")["session"].tolist()
    ep_df, ep_per = build_activation_episodes(slow_long, session_order)
    if not ep_per.empty:
        merged = merged.merge(ep_per, on="session", how="left")
    merged.to_csv(out / "daily_panel_merged.csv", index=False)
    ep_df.to_csv(out / "slow_body_episodes.csv", index=False)

    corr_all = stratum_correlations(merged, target="r_cc_pct")
    corr_all.to_csv(out / "correlations_by_stratum.csv", index=False)
    ordinary = merged[merged["stratum"] == "ordinary"]
    corr_ord = stratum_correlations(ordinary, target="r_cc_pct")
    corr_ord.to_csv(out / "correlations_ordinary_only.csv", index=False)

    splits = []
    for col in ("DK_sq_count_orb05", "DK_sq_count_orb10", "tight_aspect_count_orb10"):
        splits.append(chronological_split_correlation(merged, feature=col))
    pd.DataFrame(splits).to_csv(out / "chronological_train_test_corr.csv", index=False)

    circ = []
    for col in ("DK_sq_count_orb10", "tight_aspect_count_orb10"):
        circ.append(circular_shift_permutation(merged, col))
    pd.DataFrame(circ).to_csv(out / "permutation_circular_shift.csv", index=False)

    max_stat = max_stat_search_permutation(merged, FROZEN_DAILY_COLUMNS, n_perm=999)
    (out / "permutation_max_stat_frozen.json").write_text(
        json.dumps(max_stat, indent=2), encoding="utf-8"
    )

    ep_n = episode_adjusted_n(merged, ep_df)
    summary = {
        "output_dir": str(out),
        "n_sessions": len(merged),
        "n_earnings_reaction_sessions": int((merged["stratum"] == "earnings_reaction").sum()),
        "episode_stats": ep_n,
        "key_question": "DK_sq vs r_cc across ordinary vs earnings vs full panel",
        "dk_sq_orb10_r_full": float(merged["DK_sq_count_orb10"].corr(merged["r_cc_pct"])),
        "dk_sq_orb10_r_ordinary": float(ordinary["DK_sq_count_orb10"].corr(ordinary["r_cc_pct"]))
        if len(ordinary) > 3
        else None,
        "dk_sq_orb10_r_earnings": float(
            merged.loc[merged["stratum"] == "earnings_reaction", "DK_sq_count_orb10"].corr(
                merged.loc[merged["stratum"] == "earnings_reaction", "r_cc_pct"]
            )
        )
        if (merged["stratum"] == "earnings_reaction").sum() > 3
        else None,
        "max_stat_permutation": max_stat,
        "chronological_splits": splits,
    }
    (out / "pipeline_summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    _write_report(out, merged, corr_all, summary, max_stat, ep_df)
    return summary


def _write_report(out, merged, corr_all, summary, max_stat, ep_df) -> None:
    dk = corr_all[corr_all["feature"].str.startswith("DK_sq")]
    lines = [
        "# Report G — Daily converse panel (frozen hypotheses)",
        "",
        f"Trading sessions: **{summary['n_sessions']}**; earnings-reaction labels: **{summary['n_earnings_reaction_sessions']}**.",
        f"Slow-body activation episodes (≤1°, outer converse): **{len(ep_df)}** "
        f"(effective independent structure ≪ session count).",
        "",
        "## Primary question",
        "",
        "Does **DK square count** relate negatively to daily CC returns on ordinary days, or only around earnings?",
        "",
        "| Panel | DK sq @ 1° vs CC r |",
        "|-------|-------------------|",
    ]
    rf = summary.get("dk_sq_orb10_r_full")
    lines.append(f"| Full sample | {rf:.4f} |" if rf is not None else "| Full sample | n/a |")
    ro = summary.get("dk_sq_orb10_r_ordinary")
    re = summary.get("dk_sq_orb10_r_earnings")
    lines.append(f"| Ordinary days only | {ro:.4f} |" if ro is not None else "| Ordinary days only | n/a |")
    lines.append(f"| Earnings-reaction days | {re:.4f} |" if re is not None else "| Earnings-reaction days | n/a |")
    lines.extend(
        [
            "",
            "## Frozen feature correlations by stratum",
            "",
            _md(corr_all),
            "",
            "## Multiple-testing-aware null (max |r| across frozen features, label shuffle)",
            "",
            "```json",
            json.dumps(max_stat, indent=2),
            "```",
            "",
            "## Interpretation guide",
            "",
            "- Negative r on **ordinary** + **earnings**: candidate general directional link.",
            "- Negative only on **earnings**: event-conditioned (consistent with small-sample discovery).",
            "- Near zero on ordinary with earnings-only signal: daily panel mostly dilutes event effect.",
            "",
            "Earnings discovery stage remains frozen under `earnings-study/output/`.",
        ]
    )
    (out / "REPORT_G_daily_panel.md").write_text("\n".join(lines), encoding="utf-8")


def _md(df: pd.DataFrame) -> str:
    try:
        return df.to_markdown(index=False)
    except Exception:
        return df.to_csv(index=False)


if __name__ == "__main__":
    print(json.dumps(run_daily_study(), indent=2))
