# BR-4 — Cell crash/rally differentials (exploratory)

## Sample and validation
- Matrices: `output/br3_5_controlled/` (50 NEG + 50 POS EWZ adj extremes, ≥7 eligible tickers per session).
- Pooled ranking exposure floor: **15** eligible obs per tail; ticker consistency floor: **3** per tail.
- BR-3 power/aggregation checks on controlled run: **True**.
- Original `output/br3/` artifact hashes (unchanged check): `{'individual_aspect_matrices.npz': 'eabf1810895b7dae', 'event_manifest.parquet': '21b47200b7a11e14'}`.

## 1. Which cells show the largest crash/rally differences?

Top standardized **crash** frequency (C2C, all events):
  - Venus–Node opp: ΔF=0.0359, ΔP=0.1026, z=3.98, tickers +ΔF=8/10, pooled N_neg/N_pos=417/416
  - Sun–Neptune sex: ΔF=0.0479, ΔP=0.3044, z=3.41, tickers +ΔF=6/10, pooled N_neg/N_pos=417/416
  - Moon–Venus con: ΔF=0.0407, ΔP=0.3753, z=3.23, tickers +ΔF=7/10, pooled N_neg/N_pos=417/416
  - Mars–Uranus sex: ΔF=0.0454, ΔP=0.1315, z=2.20, tickers +ΔF=6/10, pooled N_neg/N_pos=417/416
  - Mercury–Jupiter tri: ΔF=0.0335, ΔP=0.0735, z=2.19, tickers +ΔF=6/10, pooled N_neg/N_pos=417/416

Top standardized **rally** frequency (C2C, all events):
  - Mars–Node con: ΔF=-0.0433, ΔP=-0.2136, z=-2.89, tickers +ΔF=1/10, pooled N_neg/N_pos=417/416
  - Mercury–Pluto squ: ΔF=-0.0386, ΔP=-0.1999, z=-2.31, tickers +ΔF=3/10, pooled N_neg/N_pos=417/416
  - Sun–Saturn sex: ΔF=-0.0386, ΔP=-0.3002, z=-2.16, tickers +ΔF=2/10, pooled N_neg/N_pos=417/416
  - Sun–Mars con: ΔF=-0.0363, ΔP=-0.4522, z=-2.11, tickers +ΔF=1/10, pooled N_neg/N_pos=417/416
  - Mercury–Uranus con: ΔF=-0.0313, ΔP=-0.1534, z=-2.05, tickers +ΔF=2/10, pooled N_neg/N_pos=417/416

Top standardized **crash** frequency (C2R, all events):
  - Moon→Sun tri: ΔF=0.0478, ΔP=0.2405, z=2.95, tickers +ΔF=7/10, pooled N_neg/N_pos=417/416
  - Neptune→Node opp: ΔF=0.0358, ΔP=0.0462, z=2.67, tickers +ΔF=5/10, pooled N_neg/N_pos=417/416
  - Mars→Jupiter opp: ΔF=0.0264, ΔP=0.1090, z=2.60, tickers +ΔF=3/10, pooled N_neg/N_pos=417/416
  - Uranus→Mercury opp: ΔF=0.0263, ΔP=0.0514, z=2.56, tickers +ΔF=5/10, pooled N_neg/N_pos=417/416
  - Moon→Mercury con: ΔF=0.0335, ΔP=0.2794, z=2.52, tickers +ΔF=8/10, pooled N_neg/N_pos=417/416

Raw tables: `ranked_crash_cells.csv` / `ranked_rally_cells.csv` (four mode×metric blocks × with/without discovery).

## 2. Frequency vs power intensity
- Among ranking-eligible C2C cells, median |ΔF| vs |ΔP| suggests differences are often larger in **mean power (ΔP)** (compare `delta_F`, `delta_P`, and conditional `delta_A` in parquets).
- Rankings are split: frequency uses bootstrap-standardized ΔF; power uses standardized ΔP (see `cell_uncertainty.parquet`).

## 3. Cross-company recurrence
- Pooled vs equal-company columns: `delta_F` / `delta_P` vs `equal_company_delta_F` / `median_ticker_delta_F`.
- When pooled |ΔF| ≫ |median_ticker_delta_F| or `n_tickers_delta_F_positive` is low, a single issuer likely drives the pooled gap.
- Drill-down: `ticker_cell_differences.parquet` retains every ticker×cell row behind aggregates.

## 4. Historical periods
- Event-level contributions: `output/br3_5_controlled/c2c_event_cells.parquet` / `c2r_event_cells.parquet` (session, label, active, power).
- Heatmap cell click / ticker filter lists sessions contributing to that cell (see `cell_heatmaps.html`).

## 5. C2C vs C2R structure
- C2C: 55 unordered pairs × 5 aspects; C2R: directed 11×11 × 5 aspects — not pooled across modes.
- C2R top |ΔF| among eligible cells (raw): Venus→Moon tri (ΔF=-0.0530).
- C2C counterpart: Sun–Neptune sex (ΔF=0.0479).

## 6. October 2026 discovery event (`discovery_flag` on 2026-10-26)
- Uncertainty and rankings duplicated with `exclude_discovery=true` (49 NEG + 49 POS after dropping the flagged session).
- Top crash C2C frequency ranks are **mostly stable** (Venus–Node opp stays #1); Sun–Neptune sex drops out of the top 3 without discovery.
- C2R crash frequency ranks shift more in the middle (e.g. Moon→Mercury con enters top 3 without discovery).
- Compare full blocks in `ranked_crash_cells.csv` / `ranked_rally_cells.csv` via `exclude_discovery`.

## 7. Multiple testing / unusualness after full search
- After BH-FDR on C2C permutation p-values (full family): **0** cells at q<0.05 (exploratory; not confirmatory).
- Permutation tests shuffle **event labels** (not tickers) to respect shared market dates.

## Caveats
Exploratory analysis only; hypotheses were informed by earlier event inspection. No forecasting claims, no orb tuning, no category aggregation.

## Artifacts (`output/br4/`)
- `c2c_cell_differences.parquet`
- `c2r_cell_differences.parquet`
- `ticker_cell_differences.parquet`
- `cell_uncertainty.parquet`
- `ranked_crash_cells.csv`
- `ranked_rally_cells.csv`
- `cell_heatmaps.html`
