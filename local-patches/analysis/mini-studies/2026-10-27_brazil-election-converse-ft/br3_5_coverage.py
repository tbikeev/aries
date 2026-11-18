"""BR-3.5 — Coverage audit and coverage-controlled EWZ event reselection."""

from __future__ import annotations

import csv
import json
import shutil
from datetime import date, datetime, time, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from astrolog_runner import ny_standard_time_zone_hours_west
from brazil_market_reference import EWZ_CSV
from brazil_paths import STUDY_ROOT
from br3_schema import BR3_TICKERS, OUTPUT_BR3
from br3_pipeline import _load_registry, _stock_returns, build_eligibility
from ft_registry import _parse_ft_date

OUTPUT_BR35 = STUDY_ROOT / "output" / "br3_5"
NY = ZoneInfo("America/New_York")

MIN_ELIGIBLE_DEFAULT = 7


def _load_original_manifest() -> pd.DataFrame:
    return pd.read_parquet(OUTPUT_BR3 / "event_manifest.parquet")


def _load_eligibility_df() -> pd.DataFrame:
    return pd.read_csv(OUTPUT_BR3 / "eligibility_matrix.csv")


def _ewz_adj_returns() -> pd.DataFrame:
    rows = []
    with EWZ_CSV.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("return_adj_pct") in ("", None):
                continue
            rows.append(
                {
                    "session": row["session"],
                    "ewz_return_adj_pct": float(row["return_adj_pct"]),
                    "ewz_return_unadj_pct": float(row["return_cc_pct"]) if row.get("return_cc_pct") else np.nan,
                }
            )
    df = pd.DataFrame(rows)
    df["session_date"] = pd.to_datetime(df["session"]).dt.date
    return df.sort_values("session")


def _ticker_spans(reg: pd.DataFrame) -> pd.DataFrame:
    rows = []
    ret_cache = {t: _stock_returns(t) for t in BR3_TICKERS}
    for _, row in reg.iterrows():
        t = row["ticker"]
        if t not in BR3_TICKERS:
            continue
        ft_d = _parse_ft_date(row.get("ft_date"))
        rets = ret_cache[t]
        ohlc_dates = sorted(rets.keys())
        first_ohlc = ohlc_dates[0] if ohlc_dates else None
        last_ohlc = ohlc_dates[-1] if ohlc_dates else None
        first_eligible = None
        if ft_d and ohlc_dates:
            for d in ohlc_dates:
                if d > ft_d:
                    first_eligible = d
                    break
        rows.append(
            {
                "ticker": t,
                "yahoo_symbol": row.get("yahoo_symbol", t),
                "ft_date": ft_d.isoformat() if ft_d else "",
                "ft_time_hhmm": row.get("ft_time_hhmm", ""),
                "ft_strict": bool(row.get("strict_timestamp_eligible")),
                "ohlc_first_session": first_ohlc.isoformat() if first_ohlc else "",
                "ohlc_last_session": last_ohlc.isoformat() if last_ohlc else "",
                "first_eligible_session": first_eligible.isoformat() if first_eligible else "",
                "n_ohlc_return_days": len(ohlc_dates),
            }
        )
    return pd.DataFrame(rows)


def _eligible_count_by_session(reg: pd.DataFrame) -> pd.DataFrame:
    """For every EWZ session, count tickers passing FT + OHLC (same rules as BR-3)."""
    ret_cache = {t: _stock_returns(t) for t in BR3_TICKERS}
    reg_by = {r["ticker"]: r for _, r in reg.iterrows()}
    ewz = _ewz_adj_returns()
    counts = []
    for _, er in ewz.iterrows():
        sess = er["session_date"]
        n = 0
        tickers_ok = []
        for t in BR3_TICKERS:
            row = reg_by.get(t)
            ft_d = _parse_ft_date(row.get("ft_date")) if row is not None else None
            if ft_d is None or sess <= ft_d:
                continue
            if ret_cache[t].get(sess) is None:
                continue
            n += 1
            tickers_ok.append(t)
        counts.append(
            {
                "session": er["session"],
                "ewz_return_adj_pct": er["ewz_return_adj_pct"],
                "ewz_return_unadj_pct": er.get("ewz_return_unadj_pct", np.nan),
                "n_eligible_tickers": n,
                "eligible_tickers": ",".join(tickers_ok),
            }
        )
    return pd.DataFrame(counts)


def audit_erj(reg: pd.DataFrame, elig: pd.DataFrame) -> dict:
    erj = reg[reg["ticker"] == "ERJ"].iloc[0]
    ft_d = _parse_ft_date(erj.get("ft_date"))
    rets = _stock_returns("ERJ")
    ohlc_first = min(rets) if rets else None
    erj_elig = elig[elig["ticker"] == "ERJ"]
    ok = erj_elig[erj_elig["eligible"] == True]  # noqa: E712
    # Counterfactual: if FT were EMBJ first OHLC (illustrative ADR history anchor only)
    counterfactual_ft = ohlc_first
    cf_count = 0
    if counterfactual_ft and ft_d:
        for _, row in _ewz_adj_returns().iterrows():
            sess = row["session_date"]
            if sess > counterfactual_ft and rets.get(sess) is not None:
                cf_count += 1
    return {
        "registry_ft_date": ft_d.isoformat() if ft_d else None,
        "registry_ft_time": str(erj.get("ft_time_hhmm", "")),
        "yahoo_symbol": str(erj.get("yahoo_symbol", "EMBJ")),
        "ohlc_first_session": ohlc_first.isoformat() if ohlc_first else None,
        "ohlc_sessions_with_returns": len(rets),
        "br3_eligible_events": int(ok.shape[0]),
        "br3_eligible_sessions": ok["session"].tolist(),
        "br3_ineligible_reason_counts": erj_elig["reason"].value_counts().to_dict(),
        "diagnosis": (
            "Almost all BR-3 events are excluded by event_before_ft, not missing OHLC. "
            "universe_ft_registry.csv lists ERJ/EMBJ ft_date=2025-11-03 (Munkasey), "
            "while Yahoo EMBJ daily bars begin 2000-07-21. "
            "Only sessions strictly after 2025-11-03 can qualify; among the top-100 EWZ "
            "extremes that is 2026-10-05 and 2026-10-26."
        ),
        "counterfactual_eligible_ewz_sessions_if_ft_eq_ohlc_first": cf_count,
        "recommended_action": (
            "Source a historically correct Embraer ADR first-trade timestamp for strict "
            "cohorts, or exclude ERJ from pre-2025 event panels until FT is corrected. "
            "Do not infer listing from Yahoo alone without documentary FT."
        ),
    }


def build_coverage_controlled_manifest(
    session_counts: pd.DataFrame,
    *,
    min_eligible: int = MIN_ELIGIBLE_DEFAULT,
    target_per_tail: int = 50,
) -> tuple[pd.DataFrame, dict]:
    pool = session_counts[session_counts["n_eligible_tickers"] >= min_eligible].copy()
    meta: dict = {
        "min_eligible_tickers": min_eligible,
        "target_per_tail": target_per_tail,
        "pool_sessions": len(pool),
    }
    if pool.empty:
        meta["note"] = "No sessions meet min eligible threshold."
        return pd.DataFrame(), meta

    pool = pool.sort_values("ewz_return_adj_pct")
    n_neg_avail = int((pool["ewz_return_adj_pct"] < 0).sum())
    n_pos_avail = int((pool["ewz_return_adj_pct"] > 0).sum())
    n_per_tail = min(target_per_tail, n_neg_avail, n_pos_avail)
    meta["neg_available_in_pool"] = n_neg_avail
    meta["pos_available_in_pool"] = n_pos_avail
    meta["selected_per_tail"] = n_per_tail
    if n_per_tail == 0:
        meta["note"] = "Insufficient negative or positive sessions in coverage-controlled pool."
        return pd.DataFrame(), meta

    neg = pool[pool["ewz_return_adj_pct"] < 0].head(n_per_tail)
    pos = pool[pool["ewz_return_adj_pct"] > 0].tail(n_per_tail)

    rows = []
    eid = 0
    for label, block in (("NEG", neg), ("POS", pos)):
        ranked = block.sort_values("ewz_return_adj_pct", ascending=(label == "NEG"))
        for rank, (_, r) in enumerate(ranked.iterrows(), start=1):
            sess = r["session"]
            sd = date.fromisoformat(sess[:10])
            local = datetime.combine(sd, time(9, 30), tzinfo=NY)
            rows.append(
                {
                    "event_id": eid,
                    "session": sess,
                    "label": label,
                    "rank_within_label": rank,
                    "ewz_return_adj_pct": float(r["ewz_return_adj_pct"]),
                    "ewz_return_unadj_pct": float(r.get("ewz_return_unadj_pct", np.nan)),
                    "n_eligible_tickers_at_session": int(r["n_eligible_tickers"]),
                    "selection_source": f"coverage_controlled:min_{min_eligible}_eligible_then_ewz_adj_extremes",
                    "discovery_flag": sess.startswith("2026-10-26"),
                    "event_local": local.isoformat(),
                    "event_utc": local.astimezone(timezone.utc).isoformat(),
                    "ny_st_zone": ny_standard_time_zone_hours_west(sd),
                    "sample_set": "coverage_controlled",
                }
            )
            eid += 1
    return pd.DataFrame(rows), meta


def run_coverage_audit(*, min_eligible: int = MIN_ELIGIBLE_DEFAULT, target_per_tail: int = 50) -> dict:
    OUTPUT_BR35.mkdir(parents=True, exist_ok=True)
    reg = _load_registry()
    manifest = _load_original_manifest()
    elig = _load_eligibility_df()

    # 1. Ticker × NEG/POS counts (original BR-3 manifest)
    m = elig.merge(manifest[["event_id", "session", "label"]], on=["event_id", "session"], how="inner")
    pivot = (
        m[m["eligible"] == True]  # noqa: E712
        .groupby(["ticker", "label"])
        .size()
        .unstack(fill_value=0)
        .reset_index()
    )
    for col in ("NEG", "POS"):
        if col not in pivot.columns:
            pivot[col] = 0
    pivot["total"] = pivot["NEG"] + pivot["POS"]
    pivot.to_csv(OUTPUT_BR35 / "ticker_neg_pos_eligible_counts.csv", index=False)

    # 2. FT / OHLC spans
    spans = _ticker_spans(reg)
    spans.to_csv(OUTPUT_BR35 / "ticker_data_span.csv", index=False)

    # 3. Year × ticker coverage (eligible obs in original 100-event sample)
    m["year"] = pd.to_datetime(m["session"]).dt.year
    year_ticker = (
        m[m["eligible"] == True].groupby(["year", "ticker"]).size().unstack(fill_value=0)  # noqa: E712
    )
    year_ticker.to_csv(OUTPUT_BR35 / "year_ticker_coverage_original100.csv")

    # 4. Event dates with >=5, >=7, >=9 eligible (full EWZ calendar)
    session_counts = _eligible_count_by_session(reg)
    session_counts.to_csv(OUTPUT_BR35 / "ewz_session_eligible_ticker_counts.csv", index=False)
    for thr in (5, 7, 9):
        sub = session_counts[session_counts["n_eligible_tickers"] >= thr][
            ["session", "ewz_return_adj_pct", "n_eligible_tickers", "eligible_tickers"]
        ]
        sub.to_csv(OUTPUT_BR35 / f"sessions_min_{thr}_eligible_tickers.csv", index=False)

    # 5. ERJ audit
    erj_audit = audit_erj(reg, elig)
    (OUTPUT_BR35 / "erj_eligibility_audit.json").write_text(json.dumps(erj_audit, indent=2), encoding="utf-8")

    # 6. Period composition: original 100 vs coverage-controlled (after build)
    orig_period = (
        manifest.groupby(pd.to_datetime(manifest["session"]).dt.year)["label"]
        .value_counts()
        .unstack(fill_value=0)
        .rename_axis("year")
    )

    # Preserve sensitivity sample
    sens_path = OUTPUT_BR35 / "event_manifest_all_history_sensitivity.parquet"
    shutil.copy2(OUTPUT_BR3 / "event_manifest.parquet", sens_path)

    cc_manifest, cc_meta = build_coverage_controlled_manifest(
        session_counts, min_eligible=min_eligible, target_per_tail=target_per_tail
    )
    cc_path = OUTPUT_BR35 / "event_manifest_coverage_controlled.parquet"
    if not cc_manifest.empty:
        cc_manifest.to_parquet(cc_path, index=False)
        cc_period = (
            cc_manifest.groupby(pd.to_datetime(cc_manifest["session"]).dt.year)["label"]
            .value_counts()
            .unstack(fill_value=0)
            .rename_axis("year")
        )
        comp = orig_period.add_suffix("_orig").join(cc_period.add_suffix("_controlled"), how="outer").fillna(0).astype(int)
        comp.to_csv(OUTPUT_BR35 / "crash_rally_composition_by_year.csv")

    # Summary markdown
    report = _write_report(
        pivot=pivot,
        spans=spans,
        session_counts=session_counts,
        erj_audit=erj_audit,
        cc_meta=cc_meta,
        min_eligible=min_eligible,
    )

    return {
        "output_dir": str(OUTPUT_BR35),
        "report": str(report),
        "sensitivity_manifest": str(sens_path),
        "coverage_controlled_manifest": str(cc_path) if not cc_manifest.empty else None,
        "coverage_controlled_meta": cc_meta,
        "sessions_min_7_eligible": int((session_counts["n_eligible_tickers"] >= 7).sum()),
    }


def _write_report(
    *,
    pivot: pd.DataFrame,
    spans: pd.DataFrame,
    session_counts: pd.DataFrame,
    erj_audit: dict,
    cc_meta: dict,
    min_eligible: int,
) -> Path:
    path = OUTPUT_BR35 / "REPORT_BR3_5_COVERAGE.md"
    lines = [
        "# BR-3.5 — Coverage audit and balanced sample design",
        "",
        "## Original BR-3 sample (sensitivity)",
        "- 100 EWZ adj extremes (50 NEG + 50 POS), unchanged.",
        "- Copied to `event_manifest_all_history_sensitivity.parquet`.",
        "",
        "## Ticker × tail eligible counts (original 100 events)",
        "",
        "```\n" + pivot.to_csv(index=False) + "```",
        "",
        "## ERJ audit (2 eligible observations)",
        "",
        erj_audit["diagnosis"],
        "",
        f"- Registry FT date: **{erj_audit['registry_ft_date']}**",
        f"- EMBJ OHLC from: **{erj_audit['ohlc_first_session']}** ({erj_audit['ohlc_sessions_with_returns']} return days)",
        f"- Eligible sessions in top-100: **{erj_audit['br3_eligible_sessions']}**",
        f"- Ineligible reasons: `{erj_audit['br3_ineligible_reason_counts']}`",
        "",
        erj_audit["recommended_action"],
        "",
        "## EWZ sessions by minimum eligible tickers (full calendar)",
        "",
    ]
    for thr in (5, 7, 9):
        n = int((session_counts["n_eligible_tickers"] >= thr).sum())
        lines.append(f"- ≥{thr} tickers: **{n}** sessions")
    lines.extend(
        [
            "",
            "## Coverage-controlled reselection",
            f"- Rule: sessions with ≥**{min_eligible}** eligible tickers, then top/bottom EWZ **adj** returns.",
            f"- Pool size (≥{min_eligible}): **{cc_meta.get('pool_sessions', 0)}** sessions",
            f"- Selected per tail: **{cc_meta.get('selected_per_tail', 0)}** "
            f"(neg avail {cc_meta.get('neg_available_in_pool', 0)}, "
            f"pos avail {cc_meta.get('pos_available_in_pool', 0)})",
            "",
            "Artifacts:",
            "- `event_manifest_coverage_controlled.parquet`",
            "- `ewz_session_eligible_ticker_counts.csv`",
            "- `crash_rally_composition_by_year.csv`",
            "",
            "## Next step (BR-4)",
            "Re-run `aspect-matrices` against the coverage-controlled manifest before cell-level crash/rally diffs.",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
