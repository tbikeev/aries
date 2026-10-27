"""End-to-end Brazil election converse FT study."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import numpy as np
import pandas as pd

from brazil_historical import ewz_shock_sessions, sample_ordinary_sessions, trading_session_jd
from brazil_paths import (
    CACHE,
    EVENT_DATE,
    EVENT_LOCAL,
    OUTPUT,
    PREV_CLOSE_DATE,
    STUDY_ROOT,
    UNIVERSE_TICKERS,
    UBER_STUDY,
)

_PUBLISH_NAMES = (
    "universe_ft_registry.csv",
    "event_ohlc_returns.csv",
    "pags_zet_reproduction.md",
    "converse_positions.csv",
    "converse_to_radix_aspects.csv",
    "converse_to_converse_aspects.csv",
    "declination_contacts.csv",
    "cross_sectional_feature_matrix.csv",
    "historical_percentiles.csv",
    "placebo_results.csv",
    "REPORT_BRAZIL_ELECTION.md",
)


def _publish_outputs() -> None:
    for name in _PUBLISH_NAMES:
        src = OUTPUT / name
        if src.exists():
            shutil.copy2(src, STUDY_ROOT / name)
from brazil_placebos import run_placebos
from brazil_stats import correlation_table, leave_one_out_correlations, loser_resilient_ranks
from converse_features import (
    converse_positions_table,
    converse_to_converse_aspects,
    converse_to_radix_aspects,
    declination_contacts,
    event_jd_from_local,
    feature_vector,
)
from event_returns import fetch_event_returns
from ft_registry import approximate_ft_jd_noon, build_registry, ft_birth_jd
from pags_reproduction import write_pags_report


def _enrich_returns(reg: pd.DataFrame, returns: pd.DataFrame) -> pd.DataFrame:
    import yfinance as yf

    out = returns.merge(reg[["ticker", "yahoo_symbol"]], on="ticker", how="left", suffixes=("", "_reg"))
    for i, row in out.iterrows():
        if row["ticker"] in ("EWZ", "SPY") or row.get("data_flag") != "ok":
            continue
        ysym = row.get("yahoo_symbol") or row["ticker"]
        hist = yf.download(ysym, start="2025-01-01", end="2026-11-05", progress=False, auto_adjust=False)
        if hist.empty:
            continue
        if isinstance(hist.columns, pd.MultiIndex):
            hist = hist.droplevel(1, axis=1)
        hist = hist.reset_index()
        hist["date"] = pd.to_datetime(hist["Date"]).dt.date
        hist = hist.sort_values("date")
        # 60-session vol before event
        pre = hist[hist["date"] < EVENT_DATE].tail(60)
        if len(pre) >= 20:
            rets = pre["Close"].pct_change().dropna()
            vol = float(rets.std() * 100.0)
            if vol > 0 and pd.notna(row.get("return_cc_pct")):
                out.at[i, "vol_normalized_return"] = float(row["return_cc_pct"]) / vol
        # 2d and 5d cumulative from prev close
        idx = hist[hist["date"] == PREV_CLOSE_DATE]
        if idx.empty:
            continue
        c0 = float(idx["Close"].iloc[0])
        dates_after = hist[hist["date"] > PREV_CLOSE_DATE]["date"].tolist()
        if len(dates_after) >= 1:
            c1 = float(hist[hist["date"] == dates_after[0]]["Close"].iloc[0])
            out.at[i, "return_2session_pct"] = 100.0 * (c1 / c0 - 1.0)
        if len(dates_after) >= 5:
            c5 = float(hist[hist["date"] == dates_after[4]]["Close"].iloc[0])
            out.at[i, "return_5session_pct"] = 100.0 * (c5 / c0 - 1.0)
    return out


def historical_percentiles(ft_jds: dict[str, float], reg: pd.DataFrame) -> pd.DataFrame:
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / "historical_hard_counts.json"
    cached = json.loads(path.read_text()) if path.exists() else {}
    event_jd = event_jd_from_local(EVENT_LOCAL)
    rows = []
    for ticker, ft_jd in ft_jds.items():
        ysym = reg.loc[reg["ticker"] == ticker, "yahoo_symbol"].iloc[0]
        key = f"{ticker}|{ysym}"
        if key not in cached:
            sessions = sample_ordinary_sessions(ysym)
            dist = []
            for d in sessions:
                ej = trading_session_jd(d)
                from converse_features import c2r_hard_count

                dist.append(c2r_hard_count(ft_jd, ej))
            cached[key] = dist
        dist = cached[key]
        from converse_features import c2r_hard_count

        obs = c2r_hard_count(ft_jd, event_jd)
        if dist:
            pct = float((np.sum(np.asarray(dist) <= obs) + 1) / (len(dist) + 1))
        else:
            pct = float("nan")
        rows.append(
            {
                "ticker": ticker,
                "event_c2r_hard_1deg": obs,
                "historical_n_sessions": len(dist),
                "event_day_percentile": pct,
                "historical_median": float(np.median(dist)) if dist else float("nan"),
            }
        )
    path.write_text(json.dumps(cached, indent=2), encoding="utf-8")
    return pd.DataFrame(rows)


def run_full(*, skip_historical: bool = False) -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    event_jd = event_jd_from_local(EVENT_LOCAL)

    reg = build_registry()
    reg.to_csv(OUTPUT / "universe_ft_registry.csv", index=False)

    # PAGS gate
    pags_row = reg[reg["ticker"] == "PAGS"].iloc[0]
    pags_jd, _ = ft_birth_jd(pags_row)
    write_pags_report(OUTPUT / "pags_zet_reproduction.md", ft_jd=float(pags_jd), event_jd=event_jd)

    returns = fetch_event_returns(list(UNIVERSE_TICKERS))
    returns = _enrich_returns(reg, returns)
    reg2 = reg.merge(
        returns[["ticker", "prev_close_unadj", "event_open_unadj", "event_close_unadj", "return_cc_pct"]],
        on="ticker",
        how="left",
    )
    reg2.to_csv(OUTPUT / "universe_ft_registry.csv", index=False)
    returns.to_csv(OUTPUT / "event_ohlc_returns.csv", index=False)

    pos_frames, c2r_frames, c2c_frames, decl_frames, feat_rows = [], [], [], [], []
    ft_jds_strict: dict[str, float] = {}
    ft_jds_approx: dict[str, float] = {}

    for _, row in reg.iterrows():
        ticker = row["ticker"]
        jd, strict = ft_birth_jd(row)
        if strict and jd is not None:
            ft_jds_strict[ticker] = jd
            use_jd = jd
        else:
            ajd = approximate_ft_jd_noon(row)
            if ajd is not None:
                ft_jds_approx[ticker] = ajd
            use_jd = ajd
        if use_jd is None:
            continue
        pos_frames.append(converse_positions_table(ticker, use_jd, event_jd))
        c2r_frames.append(converse_to_radix_aspects(ticker, use_jd, event_jd))
        c2c_frames.append(converse_to_converse_aspects(ticker, use_jd, event_jd))
        decl_frames.append(declination_contacts(ticker, use_jd, event_jd))
        fv = feature_vector(ticker, use_jd, event_jd)
        fv["strict_timestamp"] = strict
        fv["ft_jd_ut"] = use_jd
        feat_rows.append(fv)

    pd.concat(pos_frames, ignore_index=True).to_csv(OUTPUT / "converse_positions.csv", index=False)
    pd.concat(c2r_frames, ignore_index=True).to_csv(OUTPUT / "converse_to_radix_aspects.csv", index=False)
    pd.concat(c2c_frames, ignore_index=True).to_csv(OUTPUT / "converse_to_converse_aspects.csv", index=False)
    pd.concat(decl_frames, ignore_index=True).to_csv(OUTPUT / "declination_contacts.csv", index=False)
    features = pd.DataFrame(feat_rows)
    features.to_csv(OUTPUT / "cross_sectional_feature_matrix.csv", index=False)

    hist = pd.DataFrame()
    if not skip_historical and ft_jds_strict:
        hist = historical_percentiles(ft_jds_strict, reg)
        hist.to_csv(OUTPUT / "historical_percentiles.csv", index=False)
    else:
        if hist.empty:
            hist = pd.DataFrame(
                columns=[
                    "ticker",
                    "event_c2r_hard_1deg",
                    "historical_n_sessions",
                    "event_day_percentile",
                    "historical_median",
                ]
            )
        hist.to_csv(OUTPUT / "historical_percentiles.csv", index=False)

    placebo = run_placebos(ft_jds_strict or ft_jds_approx, event_jd)
    placebo.to_csv(OUTPUT / "placebo_results.csv", index=False)

    shocks = ewz_shock_sessions()
    shocks.to_csv(OUTPUT / "brazil_shock_dates_ewz.csv", index=False)

    write_report(reg, returns, features, hist, placebo)
    _publish_outputs()


def _df_block(df: pd.DataFrame) -> str:
    if df.empty:
        return "_empty_"
    return "```\n" + df.to_csv(index=False).strip() + "\n```"


def write_report(
    reg: pd.DataFrame,
    returns: pd.DataFrame,
    features: pd.DataFrame,
    hist: pd.DataFrame,
    placebo: pd.DataFrame,
) -> None:
    uni = returns[returns["ticker"].isin(UNIVERSE_TICKERS)].dropna(subset=["return_cc_pct"])
    corr = correlation_table(features, returns)
    ranks = loser_resilient_ranks(features, returns)
    loo = leave_one_out_correlations(features, returns, "c2r_hard_count_1deg")

    strict_n = int(reg["strict_timestamp_eligible"].sum())
    with_hard = features[features["c2r_hard_count_1deg"] > 0]

    # Explicit answers (report section J)
    ans = _report_answers(reg, returns, features, hist, placebo, corr, ranks)

    lines = [
        "# Brazil election shock — converse first-trade study",
        "",
        f"Event: **{EVENT_DATE}** 09:30 America/New_York (Brazil presidential runoff 25 Oct 2026).",
        f"Primary return: close({EVENT_DATE}) vs close({PREV_CLOSE_DATE}), unadjusted Yahoo close.",
        "",
        "## 1. PAGS Zet reproduction",
        "",
        "See `pags_zet_reproduction.md`. Without `fixtures/pags_zet_reference.json`, validation is manual.",
        "Engine uses `T_conv = 2×T_FT − T_event`, Swiss Ephemeris, tropical geocentric.",
        "",
        "## 2. Tight hard aspects (converse→radix, ≤1° conj/sq/opp)",
        "",
        f"- Universe with computed charts: **{len(features)}**",
        f"- Strict FT timestamp cohort: **{strict_n}** tickers",
        f"- Names with ≥1 tight c2r hard aspect: **{len(with_hard)}**",
        "",
        "### Returns (close-to-close %)",
        "",
        _df_block(uni.sort_values("return_cc_pct")[["ticker", "return_cc_pct", "return_vs_ewz_pp"]]),
        "",
        "## 3. Historical unusualness (strict cohort)",
        "",
        _df_block(hist) if not hist.empty else "_Not run or no strict timestamps._",
        "",
        "## 4. Losers vs resilient (descriptive)",
        "",
        _df_block(ranks),
        "",
        "## 5. Cross-sectional correlations (exploratory, N≈11, one shared shock)",
        "",
        _df_block(corr),
        "",
        "## 6. Converse→converse vs converse→radix",
        "",
        "Compare `c2r_*` vs `c2c_*` columns in correlation table; do not treat as independent evidence.",
        "",
        "## 7. FT timestamp sensitivity",
        "",
        f"Approximate-noon FT used when Munkasey time missing: {reg[~reg['strict_timestamp_eligible']]['ticker'].tolist()}",
        "",
        "## 8. Placebos",
        "",
        _df_block(placebo),
        "",
        "## 9. Independent historical shocks?",
        "",
        "Eleven names share one election; cross-sectional correlation is **hypothesis-generating only**.",
        "Use `brazil_shock_dates_ewz.csv` and per-company historical percentiles before predictive claims.",
        "",
        "## Leave-one-out (c2r_hard_count_1deg vs return)",
        "",
        _df_block(loo),
        "",
        "## Executive answers",
        "",
        ans,
    ]
    (OUTPUT / "REPORT_BRAZIL_ELECTION.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _report_answers(reg, returns, features, hist, placebo, corr, ranks) -> str:
    ref = (OUTPUT / "pags_zet_reproduction.md").exists()
    p1 = (
        "PAGS engine output is in `pags_zet_reproduction.md`. "
        "Automated Zet diff pending `fixtures/pags_zet_reference.json` (not supplied in repo)."
        if ref
        else "PAGS reproduction not generated."
    )
    n_hard = int((features["c2r_hard_count_1deg"] > 0).sum())
    p2 = f"{n_hard} of {len(features)} tickers show ≥1 converse→radix hard aspect ≤1°."
    if not hist.empty and hist["event_day_percentile"].notna().any():
        med_pct = float(hist["event_day_percentile"].median())
        p3 = f"Median event-day percentile of c2r hard count (strict cohort): {med_pct:.2f} (1.0 = max vs ~100 ordinary sessions)."
    else:
        p3 = "Historical percentiles not computed yet; re-run `cli.py full` without `--skip-historical`."
    losers = ranks[ranks["group"] == "losers_bottom4"]
    res = ranks[ranks["group"] == "resilient_top3"]
    if not losers.empty and not res.empty:
        p4 = (
            f"Losers mean c2r hard @1°: {losers['mean_c2r_hard_1deg'].iloc[0]:.1f} vs "
            f"resilient: {res['mean_c2r_hard_1deg'].iloc[0]:.1f} — descriptive only."
        )
    else:
        p4 = "Insufficient data for loser/resilient comparison."
    c2r_r = corr.loc[corr["feature"] == "c2r_hard_count_1deg", "pearson_r"]
    c2c_r = corr.loc[corr["feature"] == "c2c_hard_count_1deg", "pearson_r"]
    p5 = (
        f"Pearson r(return, c2r hard): {c2r_r.iloc[0]:.3f}; c2c hard: {c2c_r.iloc[0]:.3f} "
        "if |c2c| > |c2r| explore internal geometry; else radix contacts dominate exploratory fit."
        if len(c2r_r) and len(c2c_r)
        else "Correlation not computed."
    )
    approx = reg[~reg["strict_timestamp_eligible"]]["ticker"].tolist()
    p6 = f"Strict timestamp: {int(reg['strict_timestamp_eligible'].sum())} names; noon-ET sensitivity for: {approx}."
    p7 = (
        "One shared shock with N≈10 usable returns does **not** validate prediction; "
        "test on OHLC-defined Brazil shocks (`brazil_shock_dates_ewz.csv`) before any predictive claim."
    )
    return "\n".join(
        [
            f"1. **PAGS reproduction:** {p1}",
            f"2. **Tight hard aspects:** {p2}",
            f"3. **Unusual vs history:** {p3}",
            f"4. **Losers vs resilient:** {p4}",
            f"5. **C2C vs C2R:** {p5}",
            f"6. **FT uncertainty:** {p6}",
            f"7. **Next steps:** {p7}",
        ]
    )
