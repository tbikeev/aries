"""BR-3: full-resolution C2C/C2R aspect-power matrix extraction."""

from __future__ import annotations

import csv
import json
from datetime import date, datetime, time, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

from dataclasses import replace

from astrolog_runner import chart_from_ft, event_chart, ny_standard_time_zone_hours_west, run_mirror_bundle
from brazil_paths import STUDY_ROOT
from brazil_market_reference import EWZ_CSV, MARKET_REF_DIR
from br3_parse import merge_duplicate_cells, parse_aspect_lines
from br3_schema import (
    ASPECTS,
    BR3_TICKERS,
    CACHE_BR3,
    LABELS,
    OUTPUT_BR3,
    PLANETS,
    SPOT_CHECKS,
    aspect_index,
    build_matrix_metadata,
    c2c_pair_index,
    c2c_pair_planets,
    write_matrix_metadata,
)
from ft_registry import build_registry, ft_birth_jd, _parse_ft_date


def _load_registry():
    cached = STUDY_ROOT / "output" / "universe_ft_registry.csv"
    if cached.is_file():
        import pandas as pd

        return pd.read_csv(cached)
    return build_registry()
from yahoo_ohlc import bars_to_return_series, fetch_yahoo_daily_bars

NY = ZoneInfo("America/New_York")
EXTREMES_CSV = MARKET_REF_DIR / "ewz_return_extremes.csv"


def _write_ticker_manifest() -> Path:
    from br3_schema import OUTPUT_BR3 as _out

    path = _out / "ticker_universe_manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "phase": "BR-3",
                "tickers": list(BR3_TICKERS),
                "excluded": {"EBR": "FT and OHLC unresolved"},
                "frozen": True,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return path


def build_event_manifest(*, extremes: int = 50, manifest_path: Path | None = None) -> Path:
    if manifest_path is not None and manifest_path.is_file():
        return manifest_path
    OUTPUT_BR3.mkdir(parents=True, exist_ok=True)
    crashes, rallies = [], []
    with EXTREMES_CSV.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["rank_type"] == "crash":
                crashes.append(row)
            else:
                rallies.append(row)
    crashes.sort(key=lambda r: int(r["rank"]))
    rallies.sort(key=lambda r: int(r["rank"]))
    crashes = crashes[:extremes]
    rallies = rallies[:extremes]

    rows = []
    eid = 0
    for label, block in (("NEG", crashes), ("POS", rallies)):
        for r in block:
            sess = r["session"]
            local = datetime.combine(date.fromisoformat(sess), time(9, 30), tzinfo=NY)
            rows.append(
                {
                    "event_id": eid,
                    "session": sess,
                    "label": label,
                    "rank_within_label": int(r["rank"]),
                    "ewz_return_adj_pct": float(r["return_adj_pct"]),
                    "ewz_return_unadj_pct": float(r["return_cc_pct"]),
                    "selection_source": "ewz_return_extremes.csv:return_adj_pct",
                    "discovery_flag": sess == "2026-10-26",
                    "event_local": local.isoformat(),
                    "event_utc": local.astimezone(timezone.utc).isoformat(),
                    "ny_st_zone": ny_standard_time_zone_hours_west(date.fromisoformat(sess)),
                }
            )
            eid += 1

    import pandas as pd

    out = OUTPUT_BR3 / "event_manifest.parquet"
    pd.DataFrame(rows).to_parquet(out, index=False)
    return out


def _load_manifest_from(path: Path) -> list[dict]:
    import pandas as pd

    df = pd.read_parquet(path)
    return df.sort_values("event_id").to_dict("records")


def _load_manifest() -> list[dict]:
    return _load_manifest_from(OUTPUT_BR3 / "event_manifest.parquet")


def _stock_returns(ticker: str) -> dict[date, float]:
    cache = CACHE_BR3 / "returns" / f"{ticker}.csv"
    if cache.is_file():
        out: dict[date, float] = {}
        with cache.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row.get("return_cc_pct"):
                    out[date.fromisoformat(row["session"])] = float(row["return_cc_pct"])
        return out
    from astrolog_study_config import yahoo_for_ticker

    sym = yahoo_for_ticker(ticker)
    bars = fetch_yahoo_daily_bars(sym, date(2000, 1, 1), date(2026, 12, 31))
    if not bars and ticker == "ERJ":
        bars = fetch_yahoo_daily_bars("ERJ", date(2000, 1, 1), date(2026, 12, 31))
    rets = bars_to_return_series(bars)
    cache.parent.mkdir(parents=True, exist_ok=True)
    with cache.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["session", "return_cc_pct"])
        w.writeheader()
        for d, r in sorted(rets.items()):
            w.writerow({"session": d.isoformat(), "return_cc_pct": r})
    return rets


def build_eligibility(manifest: list[dict], reg) -> tuple[np.ndarray, list[list[dict]]]:
    """Returns eligible bool [T,E] and per-cell reason records."""
    n_t, n_e = len(BR3_TICKERS), len(manifest)
    eligible = np.zeros((n_t, n_e), dtype=bool)
    details: list[list[dict]] = [[{} for _ in range(n_e)] for _ in range(n_t)]
    ret_cache = {t: _stock_returns(t) for t in BR3_TICKERS}
    reg_by = {r["ticker"]: r for _, r in reg.iterrows()}

    for ti, ticker in enumerate(BR3_TICKERS):
        row = reg_by.get(ticker)
        ft_d = _parse_ft_date(row.get("ft_date")) if row is not None else None
        _, strict = ft_birth_jd(row) if row is not None else (None, False)
        for ei, ev in enumerate(manifest):
            sess = date.fromisoformat(ev["session"])
            rec = {
                "ticker": ticker,
                "session": ev["session"],
                "eligible": False,
                "reason": "",
                "ft_strict": bool(strict),
            }
            if row is None or ft_d is None:
                rec["reason"] = "missing_ft"
            elif sess <= ft_d:
                rec["reason"] = "event_before_ft"
            elif ret_cache[ticker].get(sess) is None:
                rec["reason"] = "missing_stock_ohlc"
            else:
                rec["eligible"] = True
                rec["reason"] = "ok"
                eligible[ti, ei] = True
            details[ti][ei] = rec
    return eligible, details


def _raw_cache_path(ticker: str, session: str, mode: str) -> Path:
    return CACHE_BR3 / "raw" / f"{ticker}_{session}_{mode}.txt"


def _fetch_astrolog(ticker: str, session: str, row, *, recompute: bool) -> tuple[str, str]:
    c2c_p = _raw_cache_path(ticker, session, "c2c")
    c2r_p = _raw_cache_path(ticker, session, "c2r")
    if not recompute:
        for mode, path in (("c2c", c2c_p), ("c2r", c2r_p)):
            if not path.is_file():
                legacy = STUDY_ROOT / "output" / "astrolog_debug" / f"{ticker}_{session}_{mode}.txt"
                if legacy.is_file():
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(legacy.read_text(encoding="utf-8"), encoding="utf-8")
        if c2c_p.is_file() and c2r_p.is_file():
            return c2c_p.read_text(encoding="utf-8"), c2r_p.read_text(encoding="utf-8")
    sess = date.fromisoformat(session)
    zone = ny_standard_time_zone_hours_west(sess)
    radix = replace(chart_from_ft(ticker, row), zone=zone)
    ev = event_chart(ticker, sess, session, st_zone=zone)
    c2c, c2r = run_mirror_bundle(radix, ev, event_st_zone=zone)
    c2c_p.parent.mkdir(parents=True, exist_ok=True)
    c2c_p.write_text(c2c, encoding="utf-8")
    c2r_p.write_text(c2r, encoding="utf-8")
    return c2c, c2r


def run_aspect_matrices(
    *,
    extremes: int = 50,
    recompute: bool = False,
    manifest_path: Path | None = None,
    output_subdir: str = "br3",
) -> dict:
    import br3_schema as br3_schema_mod

    out_root = STUDY_ROOT / "output" / output_subdir
    out_root.mkdir(parents=True, exist_ok=True)
    br3_schema_mod.OUTPUT_BR3 = out_root
    CACHE_BR3.mkdir(parents=True, exist_ok=True)
    _write_ticker_manifest()
    mpath = manifest_path or (out_root / "event_manifest.parquet")
    if manifest_path is None and not mpath.is_file():
        build_event_manifest(extremes=extremes)
    manifest = _load_manifest_from(mpath)
    n_e = len(manifest)
    n_t = len(BR3_TICKERS)
    n_pairs = 55
    n_asp = len(ASPECTS)
    n_plan = len(PLANETS)

    reg = _load_registry()
    eligible, elig_detail = build_eligibility(manifest, reg)

    # Save eligibility matrix CSV
    elig_path = out_root / "eligibility_matrix.csv"
    with elig_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["ticker", "session", "event_id", "eligible", "reason", "ft_strict"])
        w.writeheader()
        for ti, ticker in enumerate(BR3_TICKERS):
            for ei, ev in enumerate(manifest):
                d = elig_detail[ti][ei]
                w.writerow(
                    {
                        "ticker": ticker,
                        "session": ev["session"],
                        "event_id": ev["event_id"],
                        "eligible": d["eligible"],
                        "reason": d["reason"],
                        "ft_strict": d["ft_strict"],
                    }
                )

    c2c_active = np.zeros((n_t, n_e, n_pairs, n_asp), dtype=bool)
    c2c_power = np.zeros((n_t, n_e, n_pairs, n_asp), dtype=np.float64)
    c2c_orb = np.full((n_t, n_e, n_pairs, n_asp), np.nan, dtype=np.float64)
    c2c_orb_s = np.full((n_t, n_e, n_pairs, n_asp), np.nan, dtype=np.float64)

    c2r_active = np.zeros((n_t, n_e, n_plan, n_plan, n_asp), dtype=bool)
    c2r_power = np.zeros((n_t, n_e, n_plan, n_plan, n_asp), dtype=np.float64)
    c2r_orb = np.full((n_t, n_e, n_plan, n_plan, n_asp), np.nan, dtype=np.float64)
    c2r_orb_s = np.full((n_t, n_e, n_plan, n_plan, n_asp), np.nan, dtype=np.float64)

    stock_ret = np.full((n_t, n_e), np.nan, dtype=np.float64)
    ewz_adj = np.array([ev["ewz_return_adj_pct"] for ev in manifest], dtype=np.float64)
    stock_vs = np.full((n_t, n_e), np.nan, dtype=np.float64)
    ret_cache = {t: _stock_returns(t) for t in BR3_TICKERS}
    reg_by = {r["ticker"]: r for _, r in reg.iterrows()}

    total_elig = int(eligible.sum())
    done = 0
    for ti, ticker in enumerate(BR3_TICKERS):
        row = reg_by[ticker]
        for ei, ev in enumerate(manifest):
            sess = ev["session"]
            sr = ret_cache[ticker].get(date.fromisoformat(sess))
            if sr is not None:
                stock_ret[ti, ei] = sr
                stock_vs[ti, ei] = sr - ewz_adj[ei]
            if not eligible[ti, ei]:
                continue
            done += 1
            if done % 25 == 0 or done == total_elig:
                print(f"BR-3 astrolog progress {done}/{total_elig} ({ticker} {sess})", flush=True)
            c2c_txt, c2r_txt = _fetch_astrolog(ticker, sess, row, recompute=recompute)
            c2c_cells = merge_duplicate_cells(parse_aspect_lines(c2c_txt, mode="c2c"), mode="c2c")
            c2r_cells = merge_duplicate_cells(parse_aspect_lines(c2r_txt, mode="c2r"), mode="c2r")
            for (pk, ak), asp in c2c_cells.items():
                c2c_active[ti, ei, pk, ak] = True
                c2c_power[ti, ei, pk, ak] = asp.power
                c2c_orb[ti, ei, pk, ak] = asp.orb_deg
                c2c_orb_s[ti, ei, pk, ak] = asp.orb_signed_deg
            for (ci, ri, ak), asp in c2r_cells.items():
                c2r_active[ti, ei, ci, ri, ak] = True
                c2r_power[ti, ei, ci, ri, ak] = asp.power
                c2r_orb[ti, ei, ci, ri, ak] = asp.orb_deg
                c2r_orb_s[ti, ei, ci, ri, ak] = asp.orb_signed_deg

    meta_path = out_root / "matrix_metadata.json"
    write_matrix_metadata(meta_path, extremes=extremes)

    ind_path = out_root / "individual_aspect_matrices.npz"
    np.savez_compressed(
        ind_path,
        c2c_active=c2c_active,
        c2c_power=c2c_power,
        c2c_orb_deg=c2c_orb,
        c2c_orb_signed_deg=c2c_orb_s,
        c2r_active=c2r_active,
        c2r_power=c2r_power,
        c2r_orb_deg=c2r_orb,
        c2r_orb_signed_deg=c2r_orb_s,
        eligible=eligible,
        stock_return_cc_pct=stock_ret,
        ewz_return_adj_pct=ewz_adj,
        stock_return_vs_ewz_pp=stock_vs,
    )

    # Aggregates per ticker × label
    label_idx = {ev["label"]: [] for ev in manifest}
    for ei, ev in enumerate(manifest):
        label_idx[ev["label"]].append(ei)

    c2c_N = np.zeros((2, n_t, n_pairs, n_asp), dtype=np.int32)
    c2c_n = np.zeros((2, n_t, n_pairs, n_asp), dtype=np.int32)
    c2c_sum = np.zeros((2, n_t, n_pairs, n_asp), dtype=np.float64)
    c2r_N = np.zeros((2, n_t, n_plan, n_plan, n_asp), dtype=np.int32)
    c2r_n = np.zeros((2, n_t, n_plan, n_plan, n_asp), dtype=np.int32)
    c2r_sum = np.zeros((2, n_t, n_plan, n_plan, n_asp), dtype=np.float64)

    for li, lab in enumerate(LABELS):
        eix = label_idx[lab]
        for ti in range(n_t):
            mask = eligible[ti, eix]
            N = int(mask.sum())
            if N == 0:
                continue
            sub_a = c2c_active[ti, eix][mask]
            sub_p = c2c_power[ti, eix][mask]
            c2c_N[li, ti] = N
            c2c_n[li, ti] = sub_a.sum(axis=0).astype(np.int32)
            c2c_sum[li, ti] = sub_p.sum(axis=0)

            sub_ra = c2r_active[ti, eix][mask]
            sub_rp = c2r_power[ti, eix][mask]
            c2r_N[li, ti] = N
            c2r_n[li, ti] = sub_ra.sum(axis=0).astype(np.int32)
            c2r_sum[li, ti] = sub_rp.sum(axis=0)

    agg_path = out_root / "aggregate_aspect_matrices.npz"
    np.savez_compressed(
        agg_path,
        c2c_N=c2c_N,
        c2c_n=c2c_n,
        c2c_sum_power=c2c_sum,
        c2r_N=c2r_N,
        c2r_n=c2r_n,
        c2r_sum_power=c2r_sum,
    )

    # Pooled sums (eligible observations only)
    pool_c2c_n = np.zeros((2, n_pairs, n_asp), dtype=np.int32)
    pool_c2c_sum = np.zeros((2, n_pairs, n_asp), dtype=np.float64)
    pool_c2c_N = np.zeros((2, n_pairs, n_asp), dtype=np.int32)
    pool_c2r_n = np.zeros((2, n_plan, n_plan, n_asp), dtype=np.int32)
    pool_c2r_sum = np.zeros((2, n_plan, n_plan, n_asp), dtype=np.float64)
    pool_c2r_N = np.zeros((2, n_plan, n_plan, n_asp), dtype=np.int32)

    for li, lab in enumerate(LABELS):
        eix = np.array(label_idx[lab], dtype=int)
        for ei in eix:
            for ti in range(n_t):
                if not eligible[ti, ei]:
                    continue
                pool_c2c_n[li] += c2c_active[ti, ei].astype(np.int32)
                pool_c2c_sum[li] += c2c_power[ti, ei]
                pool_c2c_N[li] += 1
                pool_c2r_n[li] += c2r_active[ti, ei].astype(np.int32)
                pool_c2r_sum[li] += c2r_power[ti, ei]
                pool_c2r_N[li] += 1

    pool_path = out_root / "pooled_aspect_matrices.npz"
    np.savez_compressed(
        pool_path,
        c2c_n=pool_c2c_n,
        c2c_sum_power=pool_c2c_sum,
        c2c_N=pool_c2c_N,
        c2r_n=pool_c2r_n,
        c2r_sum_power=pool_c2r_sum,
        c2r_N=pool_c2r_N,
        equal_ticker_c2c_activation_frequency=_equal_ticker_freq(c2c_n, c2c_N),
        equal_ticker_c2r_activation_frequency=_equal_ticker_freq(c2r_n, c2r_N),
    )

    _export_parquet(
        manifest,
        c2c_active,
        c2c_power,
        c2c_orb,
        c2r_active,
        c2r_power,
        c2r_orb,
        eligible,
        stock_ret,
        stock_vs,
        ewz_adj,
        out_root=out_root,
    )
    _export_aggregate_parquet(
        c2c_N,
        c2c_n,
        c2c_sum,
        c2r_N,
        c2r_n,
        c2r_sum,
        pool_c2c_n,
        pool_c2c_sum,
        pool_c2c_N,
        pool_c2r_n,
        pool_c2r_sum,
        pool_c2r_N,
        out_root=out_root,
    )

    from br3_validate import run_validation, write_report

    checks = run_validation(
        manifest=manifest,
        eligible=eligible,
        c2c_active=c2c_active,
        c2c_power=c2c_power,
        c2c_n=c2c_n,
        c2c_sum=c2c_sum,
        c2c_N=c2c_N,
        c2r_active=c2r_active,
        c2r_power=c2r_power,
        c2r_n=c2r_n,
        c2r_sum=c2r_sum,
        c2r_N=c2r_N,
        pool_c2c_n=pool_c2c_n,
        pool_c2c_sum=pool_c2c_sum,
        ticker_c2c_n=c2c_n,
        ticker_c2c_sum=c2c_sum,
    )
    write_report(
        manifest=manifest,
        eligible=eligible,
        elig_detail=elig_detail,
        c2c_active=c2c_active,
        c2c_power=c2c_power,
        checks=checks,
        extremes=extremes,
    )

    return {
        "individual": str(ind_path),
        "aggregate": str(agg_path),
        "pooled": str(pool_path),
        "checks_passed": checks["all_passed"],
        "eligible_observations": int(eligible.sum()),
    }


def _equal_ticker_freq(n_arr: np.ndarray, N_arr: np.ndarray) -> np.ndarray:
    """Mean per-ticker activation_frequency across tickers with N>0."""
    out = np.full(n_arr.shape[1:], np.nan, dtype=np.float64)
    for li in range(n_arr.shape[0]):
        freqs = []
        for ti in range(n_arr.shape[1]):
            Nval = int(N_arr[li, ti].max()) if np.ndim(N_arr[li, ti]) else int(N_arr[li, ti])
            if Nval <= 0:
                continue
            freqs.append(n_arr[li, ti].astype(np.float64) / Nval)
        if freqs:
            out[li] = np.nanmean(np.stack(freqs, axis=0), axis=0)
    return out


def _export_parquet(
    manifest,
    c2c_active,
    c2c_power,
    c2c_orb,
    c2r_active,
    c2r_power,
    c2r_orb,
    eligible,
    stock_ret,
    stock_vs,
    ewz_adj,
    *,
    out_root: Path,
):
    import pandas as pd

    c2c_rows, c2r_rows = [], []
    for ti, ticker in enumerate(BR3_TICKERS):
        for ei, ev in enumerate(manifest):
            if not eligible[ti, ei]:
                continue
            for pk in range(55):
                p1, p2 = c2c_pair_planets(pk)
                for ak, asp in enumerate(ASPECTS):
                    c2c_rows.append(
                        {
                            "ticker": ticker,
                            "session": ev["session"],
                            "event_label": ev["label"],
                            "planet_1": p1,
                            "planet_2": p2,
                            "aspect": asp,
                            "active": bool(c2c_active[ti, ei, pk, ak]),
                            "power": float(c2c_power[ti, ei, pk, ak]),
                            "orb_deg": float(c2c_orb[ti, ei, pk, ak]),
                            "ewz_return_adj_pct": float(ewz_adj[ei]),
                            "stock_return_cc_pct": float(stock_ret[ti, ei]),
                            "stock_return_vs_ewz_pp": float(stock_vs[ti, ei]),
                        }
                    )
            for ci, cp in enumerate(PLANETS):
                for ri, rp in enumerate(PLANETS):
                    for ak, asp in enumerate(ASPECTS):
                        c2r_rows.append(
                            {
                                "ticker": ticker,
                                "session": ev["session"],
                                "event_label": ev["label"],
                                "converse_planet": cp,
                                "radix_planet": rp,
                                "aspect": asp,
                                "active": bool(c2r_active[ti, ei, ci, ri, ak]),
                                "power": float(c2r_power[ti, ei, ci, ri, ak]),
                                "orb_deg": float(c2r_orb[ti, ei, ci, ri, ak]),
                                "ewz_return_adj_pct": float(ewz_adj[ei]),
                                "stock_return_cc_pct": float(stock_ret[ti, ei]),
                                "stock_return_vs_ewz_pp": float(stock_vs[ti, ei]),
                            }
                        )
    pd.DataFrame(c2c_rows).to_parquet(out_root / "c2c_event_cells.parquet", index=False)
    pd.DataFrame(c2r_rows).to_parquet(out_root / "c2r_event_cells.parquet", index=False)


def _metrics_scalar(N: int, n: int, s: float) -> tuple[float, float, float]:
    if N <= 0:
        return float("nan"), float("nan"), float("nan")
    af = n / N
    ppo = s / N
    ppa = s / n if n > 0 else float("nan")
    return af, ppo, ppa


def _export_aggregate_parquet(
    c2c_N,
    c2c_n,
    c2c_sum,
    c2r_N,
    c2r_n,
    c2r_sum,
    pool_c2c_n,
    pool_c2c_sum,
    pool_c2c_N,
    pool_c2r_n,
    pool_c2r_sum,
    pool_c2r_N,
    *,
    out_root: Path,
):
    import pandas as pd

    rows = []
    for li, lab in enumerate(LABELS):
        for ti, ticker in enumerate(BR3_TICKERS):
            N = int(c2c_N[li, ti, 0, 0]) if c2c_N[li, ti].any() else 0
            if N == 0:
                N = int(c2c_N[li, ti].max())
            for pk in range(55):
                p1, p2 = c2c_pair_planets(pk)
                for ak, asp in enumerate(ASPECTS):
                    n = int(c2c_n[li, ti, pk, ak])
                    s = float(c2c_sum[li, ti, pk, ak])
                    Ncell = int(c2c_N[li, ti, pk, ak]) or N
                    af, ppo, ppa = _metrics_scalar(Ncell, n, s)
                    rows.append(
                        {
                            "label": lab,
                            "ticker": ticker,
                            "planet_1": p1,
                            "planet_2": p2,
                            "aspect": asp,
                            "N": Ncell,
                            "n": n,
                            "sum_power": s,
                            "activation_frequency": float(af),
                            "power_per_observation": float(ppo),
                            "power_per_activation": float(ppa),
                        }
                    )
    pd.DataFrame(rows).to_parquet(out_root / "c2c_aggregates.parquet", index=False)

    rows = []
    for li, lab in enumerate(LABELS):
        for ti, ticker in enumerate(BR3_TICKERS):
            N = int(c2r_N[li, ti].max()) if c2r_N[li, ti].any() else 0
            for ci, cp in enumerate(PLANETS):
                for ri, rp in enumerate(PLANETS):
                    for ak, asp in enumerate(ASPECTS):
                        n = int(c2r_n[li, ti, ci, ri, ak])
                        s = float(c2r_sum[li, ti, ci, ri, ak])
                        Ncell = int(c2r_N[li, ti, ci, ri, ak]) or N
                        af, ppo, ppa = _metrics_scalar(Ncell, n, s)
                        rows.append(
                            {
                                "label": lab,
                                "ticker": ticker,
                                "converse_planet": cp,
                                "radix_planet": rp,
                                "aspect": asp,
                                "N": Ncell,
                                "n": n,
                                "sum_power": s,
                                "activation_frequency": float(af),
                                "power_per_observation": float(ppo),
                                "power_per_activation": float(ppa),
                            }
                        )
    pd.DataFrame(rows).to_parquet(out_root / "c2r_aggregates.parquet", index=False)

    pooled = []
    for li, lab in enumerate(LABELS):
        for pk in range(55):
            p1, p2 = c2c_pair_planets(pk)
            for ak, asp in enumerate(ASPECTS):
                n = int(pool_c2c_n[li, pk, ak])
                s = float(pool_c2c_sum[li, pk, ak])
                N = int(pool_c2c_N[li, pk, ak])
                af, ppo, ppa = _metrics_scalar(N, n, s)
                pooled.append(
                    {
                        "label": lab,
                        "mode": "C2C",
                        "aggregation_method": "pooled_eligible_observations",
                        "planet_1": p1,
                        "planet_2": p2,
                        "aspect": asp,
                        "N": N,
                        "n": n,
                        "sum_power": s,
                        "activation_frequency": float(af),
                        "power_per_observation": float(ppo),
                        "power_per_activation": float(ppa),
                    }
                )
        for ci, cp in enumerate(PLANETS):
            for ri, rp in enumerate(PLANETS):
                for ak, asp in enumerate(ASPECTS):
                    n = int(pool_c2r_n[li, ci, ri, ak])
                    s = float(pool_c2r_sum[li, ci, ri, ak])
                    N = int(pool_c2r_N[li, ci, ri, ak])
                    af, ppo, ppa = _metrics_scalar(N, n, s)
                    pooled.append(
                        {
                            "label": lab,
                            "mode": "C2R",
                            "aggregation_method": "pooled_eligible_observations",
                            "converse_planet": cp,
                            "radix_planet": rp,
                            "aspect": asp,
                            "N": N,
                            "n": n,
                            "sum_power": s,
                            "activation_frequency": float(af),
                            "power_per_observation": float(ppo),
                            "power_per_activation": float(ppa),
                        }
                    )
    pd.DataFrame(pooled).to_parquet(out_root / "pooled_aggregates.parquet", index=False)
