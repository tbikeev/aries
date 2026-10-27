"""Phase 0 — Brazilian market reference: EWZ (primary) + optional synthetic equal-weight."""

from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path

from astrolog_study_config import DEBUG_TICKERS, yahoo_for_ticker
from brazil_paths import CACHE, STUDY_ROOT, UNIVERSE_TICKERS, YAHOO_SYMBOL_OVERRIDE
from yahoo_ohlc import DailyBar, bars_to_return_series, fetch_yahoo_daily_bars

MARKET_REF_DIR = CACHE / "market_reference"
EWZ_CSV = MARKET_REF_DIR / "ewz_daily.csv"
BVSP_CSV = MARKET_REF_DIR / "ibovespa_bvsp_daily.csv"
SYNTH_CSV = MARKET_REF_DIR / "synthetic_eq_daily.csv"
MERGED_CSV = MARKET_REF_DIR / "market_returns_daily.csv"
EXTREMES_CSV = MARKET_REF_DIR / "ewz_return_extremes.csv"
META_JSON = MARKET_REF_DIR / "market_reference_meta.json"

DEFAULT_START = date(2000, 1, 1)
DEFAULT_END = date(2026, 12, 31)


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


def download_ewz(*, start: date = DEFAULT_START, end: date = DEFAULT_END) -> Path:
    bars = fetch_yahoo_daily_bars("EWZ", start, end)
    if not bars:
        raise RuntimeError("EWZ download failed (Yahoo chart API and yfinance fallback).")
    _write_bars_csv(EWZ_CSV, bars, symbol="EWZ", source="yahoo_chart_unadj")
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


def _read_return_column(path: Path) -> dict[date, float]:
    out: dict[date, float] = {}
    if not path.is_file():
        return out
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            raw = row.get("return_cc_pct") or row.get("synthetic_return_cc_pct") or ""
            if raw in ("", None):
                continue
            out[date.fromisoformat(row["session"])] = float(raw)
    return out


def merge_market_returns() -> Path:
    ewz = _read_return_column(EWZ_CSV)
    synth: dict[date, float] = {}
    synth_n: dict[date, int] = {}
    if SYNTH_CSV.is_file():
        with SYNTH_CSV.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                d = date.fromisoformat(row["session"])
                synth[d] = float(row["synthetic_return_cc_pct"])
                synth_n[d] = int(row["n_contributors"])

    dates = sorted(set(ewz) | set(synth))
    with MERGED_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "session",
                "ewz_return_cc_pct",
                "synthetic_return_cc_pct",
                "n_synthetic_contributors",
                "primary_for_ranking",
            ],
        )
        w.writeheader()
        for d in dates:
            has_ewz = d in ewz
            w.writerow(
                {
                    "session": d.isoformat(),
                    "ewz_return_cc_pct": ewz.get(d, ""),
                    "synthetic_return_cc_pct": synth.get(d, ""),
                    "n_synthetic_contributors": synth_n.get(d, ""),
                    "primary_for_ranking": "EWZ" if has_ewz else "synthetic",
                }
            )
    return MERGED_CSV


def rank_ewz_extremes(*, top_n: int = 30) -> Path:
    rows: list[dict] = []
    if not EWZ_CSV.is_file():
        return EXTREMES_CSV
    with EWZ_CSV.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("return_cc_pct") in ("", None):
                continue
            rows.append(
                {
                    "session": row["session"],
                    "return_cc_pct": float(row["return_cc_pct"]),
                }
            )
    rows.sort(key=lambda r: r["return_cc_pct"])
    crashes = rows[:top_n]
    rallies = list(reversed(rows[-top_n:]))
    MARKET_REF_DIR.mkdir(parents=True, exist_ok=True)
    with EXTREMES_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["rank_type", "rank", "session", "return_cc_pct"])
        w.writeheader()
        for i, r in enumerate(crashes, start=1):
            w.writerow({"rank_type": "crash", "rank": i, **r})
        for i, r in enumerate(rallies, start=1):
            w.writerow({"rank_type": "rally", "rank": i, **r})
    return EXTREMES_CSV


def build_market_reference(
    *,
    start: date = DEFAULT_START,
    end: date = DEFAULT_END,
    force: bool = False,
    include_ibovespa: bool = True,
    top_n_extremes: int = 30,
) -> dict:
    MARKET_REF_DIR.mkdir(parents=True, exist_ok=True)
    meta: dict = {
        "phase": "0_market_reference",
        "start": start.isoformat(),
        "end": end.isoformat(),
        "primary_index": "EWZ",
        "synthetic_method": "equal_weight_listed_constituents",
        "synthetic_not_ewz_substitute": True,
        "files": {},
    }

    if force or not EWZ_CSV.is_file():
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

    with EWZ_CSV.open(newline="", encoding="utf-8") as f:
        n_ewz = sum(1 for _ in csv.DictReader(f))
    meta["ewz_sessions"] = n_ewz

    META_JSON.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    meta["files"]["meta"] = str(META_JSON)
    return meta


def load_ewz_returns_from_cache() -> dict[date, float]:
    return _read_return_column(EWZ_CSV)
