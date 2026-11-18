"""Phase 0 — Brazilian market reference: EWZ (primary) + optional synthetic equal-weight."""

from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path

from astrolog_study_config import DEBUG_TICKERS, yahoo_for_ticker
from brazil_paths import BR2_SYSTEMATIC_TOP_N, CACHE, STUDY_ROOT, UNIVERSE_TICKERS
from yahoo_ohlc import DailyBar, bars_to_adj_return_series, bars_to_return_series, fetch_yahoo_daily_bars

MARKET_REF_DIR = CACHE / "market_reference"
EWZ_CSV = MARKET_REF_DIR / "ewz_daily.csv"
BVSP_CSV = MARKET_REF_DIR / "ibovespa_bvsp_daily.csv"
SYNTH_CSV = MARKET_REF_DIR / "synthetic_eq_daily.csv"
MERGED_CSV = MARKET_REF_DIR / "market_returns_daily.csv"
EXTREMES_CSV = MARKET_REF_DIR / "ewz_return_extremes.csv"
ADJ_SENSITIVITY_CSV = MARKET_REF_DIR / "ewz_adj_unadj_sensitivity.csv"
META_JSON = MARKET_REF_DIR / "market_reference_meta.json"

DEFAULT_START = date(2000, 1, 1)
DEFAULT_END = date(2026, 12, 31)
# Flag sessions where unadjusted vs adjusted returns diverge materially.
MATERIAL_RETURN_DIFF_PP = 1.0


def _ewz_cache_needs_adj_refresh() -> bool:
    if not EWZ_CSV.is_file():
        return True
    with EWZ_CSV.open(newline="", encoding="utf-8") as f:
        header = next(csv.reader(f), [])
    if not header:
        return True
    return "adjclose" not in header or "return_adj_pct" not in header


def _write_bars_csv(path: Path, bars: list[DailyBar], *, symbol: str, source: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "session",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "return_cc_pct",
                "symbol",
                "data_source",
            ],
        )
        w.writeheader()
        prev_close: float | None = None
        for b in bars:
            ret = ""
            if prev_close is not None and prev_close > 0:
                ret = round(100.0 * (b.close / prev_close - 1.0), 6)
            w.writerow(
                {
                    "session": b.session.isoformat(),
                    "open": b.open,
                    "high": b.high,
                    "low": b.low,
                    "close": b.close,
                    "volume": b.volume if b.volume is not None else "",
                    "return_cc_pct": ret,
                    "symbol": symbol,
                    "data_source": source,
                }
            )
            prev_close = b.close


def _write_ewz_csv(path: Path, bars: list[DailyBar], *, symbol: str, source: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "session",
                "open",
                "high",
                "low",
                "close",
                "adjclose",
                "volume",
                "return_cc_pct",
                "return_adj_pct",
                "symbol",
                "data_source",
            ],
        )
        w.writeheader()
        prev_close: float | None = None
        prev_adj: float | None = None
        for b in bars:
            ret_cc = ""
            ret_adj = ""
            if prev_close is not None and prev_close > 0:
                ret_cc = round(100.0 * (b.close / prev_close - 1.0), 6)
            adj = b.adj_close if b.adj_close is not None else b.close
            if prev_adj is not None and prev_adj > 0:
                ret_adj = round(100.0 * (adj / prev_adj - 1.0), 6)
            w.writerow(
                {
                    "session": b.session.isoformat(),
                    "open": b.open,
                    "high": b.high,
                    "low": b.low,
                    "close": b.close,
                    "adjclose": adj,
                    "volume": b.volume if b.volume is not None else "",
                    "return_cc_pct": ret_cc,
                    "return_adj_pct": ret_adj,
                    "symbol": symbol,
                    "data_source": source,
                }
            )
            prev_close = b.close
            prev_adj = adj


def download_ewz(*, start: date = DEFAULT_START, end: date = DEFAULT_END) -> Path:
    bars = fetch_yahoo_daily_bars("EWZ", start, end)
    if not bars:
        raise RuntimeError("EWZ download failed (Yahoo chart API and yfinance fallback).")
    _write_ewz_csv(EWZ_CSV, bars, symbol="EWZ", source="yahoo_chart_unadj_plus_adjclose")
    return EWZ_CSV


def download_ibovespa(*, start: date = DEFAULT_START, end: date = DEFAULT_END) -> Path | None:
    bars = fetch_yahoo_daily_bars("^BVSP", start, end)
    if not bars:
        return None
    _write_bars_csv(BVSP_CSV, bars, symbol="^BVSP", source="yahoo_chart_unadj")
    return BVSP_CSV


def _load_listing_dates() -> dict[str, date | None]:
    """First date a ticker enters the synthetic universe (FT date from registry)."""
    reg_path = STUDY_ROOT / "output" / "universe_ft_registry.csv"
    out: dict[str, date | None] = {t: None for t in UNIVERSE_TICKERS if t != "EBR"}
    if not reg_path.is_file():
        return out
    with reg_path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            t = row.get("ticker", "")
            if t not in out:
                continue
            raw = (row.get("ft_date") or "").strip()[:10]
            if raw and raw.lower() not in ("nan", "none"):
                y, m, d = raw.split("-")
                out[t] = date(int(y), int(m), int(d))
    return out


def _ticker_bars_cache_path(ticker: str) -> Path:
    return MARKET_REF_DIR / "tickers" / f"{ticker}.csv"


def _load_or_fetch_ticker_bars(
    ticker: str,
    *,
    start: date,
    end: date,
    force: bool,
) -> list[DailyBar]:
    cache = _ticker_bars_cache_path(ticker)
    if cache.is_file() and not force:
        bars = _read_bars_csv(cache)
        if bars:
            return bars
    symbols = [yahoo_for_ticker(ticker)]
    if ticker == "ERJ" and "ERJ" not in symbols:
        symbols.append("ERJ")
    bars: list[DailyBar] = []
    for sym in symbols:
        bars = fetch_yahoo_daily_bars(sym, start, end)
        if bars:
            _write_bars_csv(cache, bars, symbol=sym, source="yahoo_chart_unadj")
            return bars
    return []


def _read_bars_csv(path: Path) -> list[DailyBar]:
    bars: list[DailyBar] = []
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            vol = row.get("volume", "")
            bars.append(
                DailyBar(
                    session=date.fromisoformat(row["session"]),
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(vol) if vol not in ("", None) else None,
                )
            )
    return bars


def build_synthetic_equal_weight(
    *,
    start: date = DEFAULT_START,
    end: date = DEFAULT_END,
    calendar: list[date] | None = None,
    force: bool = False,
) -> Path:
    """Equal-weight mean of constituent C2C returns; only names listed on each date."""
    listing = _load_listing_dates()
    tickers = [t for t in DEBUG_TICKERS]
    by_ticker_ret: dict[str, dict[date, float]] = {}
    for t in tickers:
        bars = _load_or_fetch_ticker_bars(t, start=start, end=end, force=force)
        by_ticker_ret[t] = bars_to_return_series(bars)

    if calendar is None:
        if EWZ_CSV.is_file():
            ewz_bars = _read_bars_csv(EWZ_CSV)
            calendar = [b.session for b in ewz_bars]
        else:
            calendar = sorted(
                {d for rets in by_ticker_ret.values() for d in rets},
            )

    MARKET_REF_DIR.mkdir(parents=True, exist_ok=True)
    with SYNTH_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "session",
                "synthetic_return_cc_pct",
                "n_contributors",
                "contributors",
                "method",
            ],
        )
        w.writeheader()
        for sess in calendar:
            if sess < start or sess > end:
                continue
            parts: list[tuple[str, float]] = []
            for t in tickers:
                listed = listing.get(t)
                if listed is not None and sess < listed:
                    continue
                r = by_ticker_ret.get(t, {}).get(sess)
                if r is not None:
                    parts.append((t, r))
            if not parts:
                continue
            mean_ret = sum(r for _, r in parts) / len(parts)
            w.writerow(
                {
                    "session": sess.isoformat(),
                    "synthetic_return_cc_pct": round(mean_ret, 6),
                    "n_contributors": len(parts),
                    "contributors": ",".join(p[0] for p in parts),
                    "method": "equal_weight_listed_constituents",
                }
            )
    return SYNTH_CSV


def _read_return_column(path: Path, column: str = "return_cc_pct") -> dict[date, float]:
    out: dict[date, float] = {}
    if not path.is_file():
        return out
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            raw = row.get(column) or row.get("synthetic_return_cc_pct") or ""
            if raw in ("", None):
                continue
            out[date.fromisoformat(row["session"])] = float(raw)
    return out


def merge_market_returns() -> Path:
    ewz_cc = _read_return_column(EWZ_CSV, "return_cc_pct")
    ewz_adj = _read_return_column(EWZ_CSV, "return_adj_pct")
    synth: dict[date, float] = {}
    synth_n: dict[date, int] = {}
    if SYNTH_CSV.is_file():
        with SYNTH_CSV.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                d = date.fromisoformat(row["session"])
                synth[d] = float(row["synthetic_return_cc_pct"])
                synth_n[d] = int(row["n_contributors"])

    dates = sorted(set(ewz_cc) | set(ewz_adj) | set(synth))
    with MERGED_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "session",
                "ewz_return_cc_pct",
                "ewz_return_adj_pct",
                "synthetic_return_cc_pct",
                "n_synthetic_contributors",
                "primary_for_ranking",
            ],
        )
        w.writeheader()
        for d in dates:
            w.writerow(
                {
                    "session": d.isoformat(),
                    "ewz_return_cc_pct": ewz_cc.get(d, ""),
                    "ewz_return_adj_pct": ewz_adj.get(d, ""),
                    "synthetic_return_cc_pct": synth.get(d, ""),
                    "n_synthetic_contributors": synth_n.get(d, ""),
                    "primary_for_ranking": "EWZ_adj" if d in ewz_adj else ("EWZ" if d in ewz_cc else "synthetic"),
                }
            )
    return MERGED_CSV


def _load_ewz_return_rows() -> list[dict]:
    rows: list[dict] = []
    if not EWZ_CSV.is_file():
        return rows
    with EWZ_CSV.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            cc = row.get("return_cc_pct")
            adj = row.get("return_adj_pct")
            if cc in ("", None) and adj in ("", None):
                continue
            rows.append(
                {
                    "session": row["session"],
                    "return_cc_pct": float(cc) if cc not in ("", None) else None,
                    "return_adj_pct": float(adj) if adj not in ("", None) else None,
                }
            )
    return rows


def report_ewz_adj_unadj_sensitivity(*, top_n: int = BR2_SYSTEMATIC_TOP_N) -> Path:
    rows = _load_ewz_return_rows()
    if not rows:
        return ADJ_SENSITIVITY_CSV

    def top_sets(key: str) -> tuple[set[str], set[str]]:
        valid = [r for r in rows if r.get(key) is not None]
        valid.sort(key=lambda r: r[key])  # type: ignore[index]
        crash = {r["session"] for r in valid[:top_n]}
        rally = {r["session"] for r in valid[-top_n:]}
        return crash, rally

    crash_adj, rally_adj = top_sets("return_adj_pct")
    crash_cc, rally_cc = top_sets("return_cc_pct")

    MARKET_REF_DIR.mkdir(parents=True, exist_ok=True)
    with ADJ_SENSITIVITY_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "session",
                "return_cc_pct",
                "return_adj_pct",
                "diff_pp",
                "sign_flip",
                "material_diff",
                "ranking_note",
            ],
        )
        w.writeheader()
        for r in rows:
            cc = r["return_cc_pct"]
            adj = r["return_adj_pct"]
            if cc is None or adj is None:
                continue
            diff = cc - adj
            sign_flip = (cc > 0) != (adj > 0)
            material = sign_flip or abs(diff) >= MATERIAL_RETURN_DIFF_PP
            if not material:
                continue
            notes: list[str] = []
            sess = r["session"]
            if sess in crash_cc ^ crash_adj:
                notes.append("top_crash_membership_adj_vs_unadj")
            if sess in rally_cc ^ rally_cc:
                notes.append("top_rally_membership_adj_vs_unadj")
            w.writerow(
                {
                    "session": sess,
                    "return_cc_pct": cc,
                    "return_adj_pct": adj,
                    "diff_pp": round(diff, 6),
                    "sign_flip": sign_flip,
                    "material_diff": material,
                    "ranking_note": ";".join(notes) if notes else "",
                }
            )
    return ADJ_SENSITIVITY_CSV


def rank_ewz_extremes(*, top_n: int = BR2_SYSTEMATIC_TOP_N) -> Path:
    rows = _load_ewz_return_rows()
    if not rows:
        return EXTREMES_CSV
    # Primary ranking: adjusted total-return proxy.
    rows_adj = [r for r in rows if r.get("return_adj_pct") is not None]
    rows_adj.sort(key=lambda r: r["return_adj_pct"])  # type: ignore[index]
    crashes = rows_adj[:top_n]
    rallies = list(reversed(rows_adj[-top_n:]))
    MARKET_REF_DIR.mkdir(parents=True, exist_ok=True)
    with EXTREMES_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "rank_type",
                "rank",
                "session",
                "return_adj_pct",
                "return_cc_pct",
                "ranking_basis",
            ],
        )
        w.writeheader()
        for i, r in enumerate(crashes, start=1):
            w.writerow(
                {
                    "rank_type": "crash",
                    "rank": i,
                    "session": r["session"],
                    "return_adj_pct": r["return_adj_pct"],
                    "return_cc_pct": r["return_cc_pct"],
                    "ranking_basis": "adjclose",
                }
            )
        for i, r in enumerate(rallies, start=1):
            w.writerow(
                {
                    "rank_type": "rally",
                    "rank": i,
                    "session": r["session"],
                    "return_adj_pct": r["return_adj_pct"],
                    "return_cc_pct": r["return_cc_pct"],
                    "ranking_basis": "adjclose",
                }
            )
    return EXTREMES_CSV


def build_market_reference(
    *,
    start: date = DEFAULT_START,
    end: date = DEFAULT_END,
    force: bool = False,
    include_ibovespa: bool = True,
    top_n_extremes: int = BR2_SYSTEMATIC_TOP_N,
) -> dict:
    MARKET_REF_DIR.mkdir(parents=True, exist_ok=True)
    meta: dict = {
        "phase": "0_market_reference",
        "start": start.isoformat(),
        "end": end.isoformat(),
        "primary_index": "EWZ",
        "primary_ranking_return": "return_adj_pct",
        "sensitivity_return": "return_cc_pct",
        "systematic_top_n": top_n_extremes,
        "synthetic_method": "equal_weight_listed_constituents",
        "synthetic_not_ewz_substitute": True,
        "files": {},
    }

    if force or _ewz_cache_needs_adj_refresh():
        meta["files"]["ewz_daily"] = str(download_ewz(start=start, end=end))
    else:
        meta["files"]["ewz_daily"] = str(EWZ_CSV)

    if include_ibovespa:
        if force or not BVSP_CSV.is_file():
            bvsp = download_ibovespa(start=start, end=end)
            if bvsp:
                meta["files"]["ibovespa_bvsp_daily"] = str(bvsp)

    build_synthetic_equal_weight(start=start, end=end, force=force)
    meta["files"]["synthetic_eq_daily"] = str(SYNTH_CSV)
    meta["files"]["market_returns_daily"] = str(merge_market_returns())
    meta["files"]["ewz_return_extremes"] = str(rank_ewz_extremes(top_n=top_n_extremes))
    meta["files"]["ewz_adj_unadj_sensitivity"] = str(
        report_ewz_adj_unadj_sensitivity(top_n=top_n_extremes)
    )

    with EWZ_CSV.open(newline="", encoding="utf-8") as f:
        n_ewz = sum(1 for _ in csv.DictReader(f))
    meta["ewz_sessions"] = n_ewz
    sens_rows = 0
    if ADJ_SENSITIVITY_CSV.is_file():
        with ADJ_SENSITIVITY_CSV.open(newline="", encoding="utf-8") as f:
            sens_rows = sum(1 for _ in csv.DictReader(f))
    meta["ewz_material_adj_unadj_sessions"] = sens_rows

    META_JSON.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    meta["files"]["meta"] = str(META_JSON)
    return meta


def load_ewz_returns_from_cache(*, adjusted: bool = True) -> dict[date, float]:
    col = "return_adj_pct" if adjusted else "return_cc_pct"
    return _read_return_column(EWZ_CSV, col)
