"""Oct 5 vs Oct 26 2026 mirror debug (astrolog -pd -1 via sa_app ast77 scripts)."""

from __future__ import annotations

import csv
import html
import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from astrolog_paths import STUDY_ROOT
from astrolog_runner import chart_from_ft, event_chart, run_mirror_bundle
from brazil_paths import UNIVERSE_TICKERS

DEBUG_TICKERS = tuple(t for t in UNIVERSE_TICKERS if t != "EBR")

EVENTS = (
    ("2026-10-05", "First-round rally"),
    ("2026-10-26", "Second-round crash (discovery)"),
)

_POWER_RE = re.compile(r" - power:\s+([0-9.]+)")
_ASPECT_TYPE_RE = re.compile(
    r"\)\s+(Con|Opp|Squ|Tri|Sex|SSx|Sqq|Inc)\s+(?:with\s+)?",
    re.I,
)
_SUM_POWER_RE = re.compile(r"Sum power:\s*([0-9.]+)", re.I)

_ASPECT_LABEL = {
    "con": "Conjunction",
    "opp": "Opposition",
    "squ": "Square",
    "tri": "Trine",
    "sex": "Sextile",
    "ssx": "SemiSextile",
    "sqq": "SemiSquare",
    "inc": "Inconjunct",
}


@dataclass
class MirrorSnapshot:
    ticker: str
    event_date: str
    event_label: str
    internal_text: str
    radix_cross_text: str
    internal_power_by_type: dict[str, float]
    cross_power_by_type: dict[str, float]
    internal_total: float
    cross_total: float


def parse_aspect_powers(text: str) -> tuple[dict[str, float], float]:
    by_type: dict[str, float] = {}
    for line in text.splitlines():
        mp = _POWER_RE.search(line)
        if not mp:
            continue
        power = float(mp.group(1))
        mt = _ASPECT_TYPE_RE.search(line)
        key = mt.group(1).lower()[:3] if mt else "other"
        by_type[key] = by_type.get(key, 0.0) + power
    sm = _SUM_POWER_RE.search(text)
    total = float(sm.group(1)) if sm else sum(by_type.values())
    return by_type, total


def run_mirror_snapshot(ticker: str, row, event_date: str, event_label: str) -> MirrorSnapshot:
    radix = chart_from_ft(ticker, row)
    ev = event_chart(ticker, date.fromisoformat(event_date), event_label)
    internal, cross = run_mirror_bundle(radix, ev, pd_key="-1.0")
    ip, itot = parse_aspect_powers(internal)
    cp, ctot = parse_aspect_powers(cross)
    return MirrorSnapshot(
        ticker=ticker,
        event_date=event_date,
        event_label=event_label,
        internal_text=internal,
        radix_cross_text=cross,
        internal_power_by_type=ip,
        cross_power_by_type=cp,
        internal_total=itot,
        cross_total=ctot,
    )


def _power_table(by_type: dict[str, float], total: float) -> str:
    if not by_type:
        return "<p><em>No aspect lines parsed.</em></p>"
    rows = sorted(by_type.items(), key=lambda x: -x[1])
    out = ["<table><thead><tr><th>Aspect</th><th>Σ power</th></tr></thead><tbody>"]
    for k, v in rows:
        out.append(f"<tr><td>{html.escape(_ASPECT_LABEL.get(k, k))}</td><td>{v:.4f}</td></tr>")
    out.append(f"<tr><td><strong>Total</strong></td><td><strong>{total:.4f}</strong></td></tr>")
    out.append("</tbody></table>")
    return "\n".join(out)


def _pre(text: str) -> str:
    return f"<pre>{html.escape(text.strip())}</pre>" if text.strip() else "<p><em>empty</em></p>"


def build_html(snapshots: dict[str, dict[str, MirrorSnapshot]], out_path: Path) -> None:
    tickers = sorted(snapshots.keys())
    parts = [
        "<!DOCTYPE html><html><head><meta charset='utf-8'>",
        "<title>Brazil FT mirror — Astrolog −pd 1.0 (converse)</title>",
        "<style>",
        "body{font-family:system-ui,sans-serif;margin:1rem;}",
        ".tabs{display:flex;flex-wrap:wrap;gap:0.25rem;margin-bottom:1rem;}",
        ".tabs button{padding:0.4rem 0.8rem;cursor:pointer;}",
        ".tabs button.active{background:#333;color:#fff;}",
        ".panel{display:none;}.panel.active{display:block;}",
        ".dates{display:flex;gap:1rem;flex-wrap:wrap;}",
        ".dates>div{flex:1;min-width:420px;border:1px solid #ccc;padding:0.75rem;}",
        "table{border-collapse:collapse;width:100%;}",
        "td,th{border:1px solid #ddd;padding:0.35rem;}",
        "pre{white-space:pre-wrap;font-size:0.72rem;max-height:24rem;overflow:auto;background:#f6f6f6;}",
        "</style></head><body>",
        "<h1>Brazil FT — 5 Oct vs 26 Oct 2026 @ 09:30 NY</h1>",
        "<p>Engine: <code>sa_app/.../ast77src/scripts/reverse_chart.sh --key -1.0</code> "
        "(MC–Sun locked converse progression). C2C = internal <code>-a</code> on mirror chart; "
        "C2R = radix↔mirror <code>-rp0 -pd -1.0 -a</code>.</p>",
        "<div class='tabs' id='tabbar'>",
    ]
    for i, t in enumerate(tickers):
        parts.append(
            f"<button type='button' class=\"{'active' if i == 0 else ''}\" data-tab='{t}'>{html.escape(t)}</button>"
        )
    parts.append("</div>")
    for i, t in enumerate(tickers):
        parts.append(f"<div class='panel{' active' if i == 0 else ''}' id='panel-{t}'>")
        parts.append(f"<h2>{html.escape(t)}</h2><div class='dates'>")
        for ed, _ in EVENTS:
            s = snapshots[t][ed]
            parts.append("<div>")
            parts.append(f"<h3>{html.escape(ed)} — {html.escape(s.event_label)}</h3>")
            parts.append(f"<p>C2C total power: <strong>{s.internal_total:.2f}</strong> · "
                         f"C2R total power: <strong>{s.cross_total:.2f}</strong></p>")
            parts.append("<h4>C2C power by aspect</h4>")
            parts.append(_power_table(s.internal_power_by_type, s.internal_total))
            parts.append("<h4>C2C raw output</h4>")
            parts.append(_pre(s.internal_text))
            parts.append("<h4>C2R power by aspect</h4>")
            parts.append(_power_table(s.cross_power_by_type, s.cross_total))
            parts.append("<h4>C2R raw output</h4>")
            parts.append(_pre(s.radix_cross_text))
            parts.append("</div>")
        parts.append("</div></div>")
    parts.append(
        "<script>document.querySelectorAll('#tabbar button').forEach(btn=>{"
        "btn.onclick=()=>{const id=btn.dataset.tab;"
        "document.querySelectorAll('#tabbar button').forEach(b=>b.classList.remove('active'));"
        "document.querySelectorAll('.panel').forEach(p=>p.classList.remove('active'));"
        "btn.classList.add('active');document.getElementById('panel-'+id).classList.add('active');};});</script>"
        "</body></html>"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(parts), encoding="utf-8")


def _load_ft_rows() -> dict[str, dict[str, str]]:
    csv_path = STUDY_ROOT / "output" / "universe_ft_registry.csv"
    if not csv_path.is_file():
        from ft_registry import build_registry

        reg = build_registry()
        return {str(r["ticker"]): r.to_dict() for _, r in reg.iterrows()}
    with csv_path.open(newline="", encoding="utf-8") as f:
        return {r["ticker"]: r for r in csv.DictReader(f)}


def run_debug(*, tickers: tuple[str, ...] | None = None) -> Path:
    reg = _load_ft_rows()
    use = tickers or DEBUG_TICKERS
    out_dir = STUDY_ROOT / "output" / "astrolog_debug"
    out_dir.mkdir(parents=True, exist_ok=True)
    snapshots: dict[str, dict[str, MirrorSnapshot]] = {}
    for ticker in use:
        if ticker not in reg:
            continue
        row = reg[ticker]
        try:
            chart_from_ft(ticker, row)
        except ValueError:
            continue
        snapshots[ticker] = {}
        for ed, elabel in EVENTS:
            snap = run_mirror_snapshot(ticker, row, ed, elabel)
            snapshots[ticker][ed] = snap
            stem = f"{ticker}_{ed}"
            (out_dir / f"{stem}_c2c.txt").write_text(snap.internal_text, encoding="utf-8")
            (out_dir / f"{stem}_c2r.txt").write_text(snap.radix_cross_text, encoding="utf-8")
            (out_dir / f"{stem}_power.json").write_text(
                json.dumps(
                    {
                        "c2c": snap.internal_power_by_type,
                        "c2r": snap.cross_power_by_type,
                        "c2c_total": snap.internal_total,
                        "c2r_total": snap.cross_total,
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
    html_path = out_dir / "brazil_mirror_debug.html"
    build_html(snapshots, html_path)
    return html_path


if __name__ == "__main__":
    print(run_debug())
