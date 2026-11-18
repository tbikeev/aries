"""Interactive HTML heatmaps for BR-4 cell metrics."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from br3_schema import ASPECTS, BR3_TICKERS, PLANETS, c2c_pair_planets


def _event_index(controlled_dir: Path | None) -> dict[str, list[dict]]:
    if controlled_dir is None:
        return {}
    path = controlled_dir / "c2c_event_cells.parquet"
    if not path.is_file():
        return {}
    df = pd.read_parquet(path)
    df = df[df["active"] == True]  # noqa: E712
    out: dict[str, list[dict]] = {}
    for _, r in df.iterrows():
        key = f"C2C|{r['planet_1']}|{r['planet_2']}|{r['aspect']}"
        out.setdefault(key, []).append(
            {
                "ticker": r["ticker"],
                "session": str(r["session"])[:10],
                "label": r["event_label"],
                "power": float(r["power"]),
            }
        )
    return out


def write_cell_heatmaps(
    path: Path,
    c2c: pd.DataFrame,
    c2r: pd.DataFrame,
    *,
    controlled_dir: Path | None = None,
    ticker_cells: pd.DataFrame | None = None,
) -> None:
    metrics = [
        ("F_neg", "C2C NEG activation frequency"),
        ("F_pos", "C2C POS activation frequency"),
        ("P_neg", "C2C NEG mean power"),
        ("P_pos", "C2C POS mean power"),
        ("delta_F", "C2C NEG−POS frequency"),
        ("delta_P", "C2C NEG−POS mean power"),
    ]
    c2c_grids = {}
    pair_meta = []
    for col, _title in metrics:
        grid = np.full((55, len(ASPECTS)), np.nan)
        for _, r in c2c.iterrows():
            grid[int(r["pair_index"]), int(r["aspect_index"])] = float(r[col])
        c2c_grids[col] = grid.tolist()

    for i in range(55):
        p1, p2 = c2c_pair_planets(i)
        pair_meta.append({"i": i, "label": f"{p1}–{p2}", "p1": p1, "p2": p2})

    c2r_grids = {}
    for col in ("F_neg", "F_pos", "P_neg", "P_pos", "delta_F", "delta_P"):
        g = np.full((len(PLANETS), len(PLANETS), len(ASPECTS)), np.nan)
        for _, r in c2r.iterrows():
            g[int(r["converse_index"]), int(r["radix_index"]), int(r["aspect_index"])] = float(r[col])
        c2r_grids[col] = g.tolist()

    pair_labels = [m["label"] for m in pair_meta]
    events_by_cell = _event_index(controlled_dir)
    tickers = list(BR3_TICKERS)

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>BR-4 cell heatmaps</title>
<style>
body {{ font-family: system-ui, sans-serif; margin: 1rem; }}
table {{ border-collapse: collapse; font-size: 10px; }}
td {{ border: 1px solid #ccc; padding: 2px 4px; min-width: 36px; text-align: center; cursor: pointer; }}
td:hover {{ outline: 2px solid #333; }}
select {{ margin: 0.5rem; }}
.panel {{ display: none; }}
.panel.active {{ display: block; }}
#detail {{ margin-top: 1rem; padding: 0.75rem; background: #f7f7f7; max-height: 240px; overflow: auto; font-size: 12px; }}
</style></head><body>
<h1>BR-4 cell heatmaps (controlled sample)</h1>
<p>C2C: 55 pairs × 5 aspects. Click a cell for contributing events (all tickers) or filter by ticker below.</p>
<label>View <select id="view">
<option value="c2c_F_neg">C2C NEG F</option>
<option value="c2c_F_pos">C2C POS F</option>
<option value="c2c_P_neg">C2C NEG P</option>
<option value="c2c_P_pos">C2C POS P</option>
<option value="c2c_delta_F">C2C ΔF</option>
<option value="c2c_delta_P">C2C ΔP</option>
<option value="c2r_delta_F">C2R ΔF (by aspect)</option>
</select></label>
<label>Ticker filter (detail panel) <select id="ticker"><option value="">(all)</option>
{''.join(f'<option value="{t}">{t}</option>' for t in tickers)}
</select></label>
<label>C2R aspect <select id="asp">{''.join(f'<option value="{i}">{a}</option>' for i,a in enumerate(ASPECTS))}</select></label>
<div id="c2c" class="panel active"></div>
<div id="c2r" class="panel"></div>
<div id="detail"><em>Click a C2C cell to list active ticker×session rows.</em></div>
<script>
const c2c = {json.dumps(c2c_grids)};
const c2r = {json.dumps(c2r_grids)};
const pairs = {json.dumps(pair_labels)};
const pairMeta = {json.dumps(pair_meta)};
const aspects = {json.dumps(list(ASPECTS))};
const planets = {json.dumps(list(PLANETS))};
const eventsByCell = {json.dumps(events_by_cell)};
let sharedScale = {{}};

function computeSharedScale(keys) {{
  let flat = [];
  for (const k of keys) {{
    if (!c2c[k]) continue;
    for (const row of c2c[k]) for (const v of row) if (v===v) flat.push(v);
  }}
  if (!flat.length) return {{vmin:0,vmax:1}};
  return {{vmin: Math.min(...flat), vmax: Math.max(...flat)}};
}}
sharedScale.F = computeSharedScale(['F_neg','F_pos']);
sharedScale.P = computeSharedScale(['P_neg','P_pos']);

function renderC2c(key) {{
  const metric = key.replace('c2c_','');
  const grid = c2c[metric];
  let flat = grid.flat().filter(x => x===x);
  let vmin, vmax;
  if (metric.startsWith('F_')) {{ vmin = sharedScale.F.vmin; vmax = sharedScale.F.vmax; }}
  else if (metric.startsWith('P_')) {{ vmin = sharedScale.P.vmin; vmax = sharedScale.P.vmax; }}
  else {{ vmin = Math.min(...flat); vmax = Math.max(...flat); }}
  let h = '<table id="c2ct"><tr><th>pair</th>' + aspects.map(a=>'<th>'+a+'</th>').join('') + '</tr>';
  for (let i=0;i<55;i++) {{
    h += '<tr><th>'+pairs[i]+'</th>';
    for (let j=0;j<5;j++) {{
      const v = grid[i][j];
      const bg = color(v, vmin, vmax);
      h += '<td data-pi="'+i+'" data-ai="'+j+'" style="background:'+bg+'">'+(v===v?v.toFixed(3):'')+'</td>';
    }}
    h += '</tr>';
  }}
  h += '</table>';
  document.getElementById('c2c').innerHTML = h;
  document.querySelectorAll('#c2ct td[data-pi]').forEach(td => {{
    td.onclick = () => showDetail(+td.dataset.pi, +td.dataset.ai);
  }});
}}
function showDetail(pi, ai) {{
  const m = pairMeta[pi];
  const asp = aspects[ai];
  const key = 'C2C|'+m.p1+'|'+m.p2+'|'+asp;
  let rows = eventsByCell[key] || [];
  const tk = document.getElementById('ticker').value;
  if (tk) rows = rows.filter(r => r.ticker === tk);
  rows.sort((a,b) => a.session.localeCompare(b.session));
  let h = '<strong>'+m.label+' '+asp+'</strong> — '+rows.length+' active obs';
  if (!rows.length) {{ document.getElementById('detail').innerHTML = h + ' (none)'; return; }}
  h += '<ul>' + rows.map(r => '<li>'+r.ticker+' '+r.session+' '+r.label+' power='+r.power.toFixed(3)+'</li>').join('') + '</ul>';
  document.getElementById('detail').innerHTML = h;
}}
function renderC2r(asp) {{
  const grid = c2r.delta_F;
  let flat = [];
  for (let i=0;i<11;i++) for (let j=0;j<11;j++) {{ const v=grid[i][j][asp]; if(v===v) flat.push(v); }}
  const vmin = Math.min(...flat), vmax = Math.max(...flat);
  let h = '<table><tr><th>c\\\\r</th>' + planets.map(p=>'<th>'+p+'</th>').join('') + '</tr>';
  for (let i=0;i<11;i++) {{
    h += '<tr><th>'+planets[i]+'</th>';
    for (let j=0;j<11;j++) {{
      const v = grid[i][j][asp];
      h += '<td style="background:'+color(v,vmin,vmax)+'">'+(v===v?v.toFixed(3):'')+'</td>';
    }}
    h += '</tr>';
  }}
  document.getElementById('c2r').innerHTML = h;
  document.getElementById('detail').innerHTML = '<em>C2R event drill-down: use c2r_event_cells.parquet in br3_5_controlled.</em>';
}}
function color(val, vmin, vmax) {{
  if (val !== val) return '#eee';
  if (vmax <= vmin) return 'rgb(128,80,128)';
  const t = Math.max(0, Math.min(1, (val - vmin) / (vmax - vmin)));
  const r = Math.round(255*t), b = Math.round(255*(1-t));
  return 'rgb('+r+',80,'+b+')';
}}
document.getElementById('view').onchange = e => {{
  const v = e.target.value;
  document.getElementById('c2c').classList.toggle('active', v.startsWith('c2c'));
  document.getElementById('c2r').classList.toggle('active', v.startsWith('c2r'));
  if (v.startsWith('c2c')) renderC2c(v);
  else renderC2r(+document.getElementById('asp').value);
}};
document.getElementById('asp').onchange = e => renderC2r(+e.target.value);
document.getElementById('ticker').onchange = () => {{}};
renderC2c('c2c_F_neg');
</script></body></html>"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
