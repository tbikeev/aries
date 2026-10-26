# UBER Converse Transit Cohort Analyzer (local mini-study)

**Zet collection key (confirmed by Thomas): `UBER.zdb`** — not `UEVER.zdb`.

Local-only path in the Aries repo (no remote push required for this study):

`local-patches/analysis/mini-studies/2026-10-26_uber-converse-cohort/`

## Converse clock (Zet coefficient −1 / Aries)

Symbolic event time `S` (market event UT) maps to converse ephemeris instant:

```text
T_conv = 2 · T_radix − T_event     (continuous UT Julian day)
```

Aries canonical code: `engine/converse_transits.py` → `mirrored_jd(birth_jd, event_jd)` (same formula).  
This study uses a **headless** copy in `converse.py` with identical JD↔UTC rounding as Aries.

**Not used:** secondary progressions, solar arc, day-for-a-year, or direct (non-converse) transits.

## Ephemeris conventions (Zet comparison)

| Setting | Value |
|--------|--------|
| Zodiac | Tropical |
| Position | Geocentric |
| Engine | Swiss Ephemeris via Aries `astrology` / `SWEP/src` |
| Node (11-point benchmark) | **True node** (`SE_TRUE_NODE`) |
| Retrograde | `speed_lon < 0` |

Optional (not in 11-point benchmark): Chiron, mean Lilith (`SE_MEAN_APOG`), Placidus Asc/MC at radix/converse JD.

## Validation layers (keep separate)

1. **Position match** — Swiss Ephemeris vs Zet Nat/Mir columns at documented UTC.
2. **Directed aspect extraction** — `converse_body → radix_body` with `orb_for_named_aspect` (never swap bodies; never use “closest aspect” alone for regression).
3. **Manual aspect lists** — Thomas’s named contacts and ≤1° counts are transcription aids, not ground truth.

Output: `converse_radix_directed_aspect_matrix.csv` (all 11×11 pairs × five orbs).

## Phase C reconciliation notes (2026-10-26)

### FT/NEG — converse Uranus ⊗ radix Mercury (~0°47′)

- **Directed check:** `directed_converse_radix_orb(FT, NEG, Uranus, Mercury, conj)` using Swiss at validated converse UTC.
- Radix Mercury matches Zet (7°23′20″ Taurus). Converse Uranus from Swiss is **~8°10′ Aries** (2012 ephemeris), not Taurus — conjunction to Mercury is **~29°** in absolute longitude.
- Zet `ft-neg.png` labels Mir Uranus as **8°10′58″ Taurus**; that would be **~38°** absolute and would yield ~0.47° to Mercury. That sign/degree combo is **inconsistent with Swiss at the same UT instant** (Uranus was in early Aries in 2012).
- **Separate valid contact:** converse **Mercury** square radix **Uranus** orb **~0.96°** (different pair; both can exist).

### DK/NEG — square to radix Mercury

- Zet `DK-neg.png`: **7°58′43″ Pisces** on the Mir row is **Chiron (⚷)**, not the Node (☊ at 12°34′ Aries).
- Directed **Chiron → Mercury** square: **~0.45°** (matches brief within tolerance).
- Do **not** tune DK birth time to fit POS Sun; keep **12:00 Tehran +03:00 → 09:00 UTC** as reference. Optional Zet hint **+03:30 → 08:30 UTC** is documented only (`dk_sensitivity.py`).

### INC Mercury ∥ DK Neptune (declination)

- Manual **0°19′** parallel **not verified**; Swiss at stated radix times gives **~10.3°** separation. Removed from mandatory Phase A pass/fail. Inspect `cohort_declination_contacts.csv` for exact δ values and signs.

### Reference screenshots

Source: `~/Downloads/Archive 2.zip` (extracted to `fixtures/zet_screenshots/`).

Transcribed JSON (partial / growing): `fixtures/zet_transcribed/*.json`.

**DK radix note:** Stated birth `1969-05-28 12:00 +03:00 → 09:00 UTC` matches natal Sun in Zet (~6°50′ Gemini).  
**DK POS mirror Sun** in Zet (`27°04′53″ Pisces`) aligns with converse JD if radix UT is **08:30** (−30 min), not 09:00 — likely noon-LMT convention in `UBER.zdb`. This study keeps **09:00 UTC** for DK; document deviation (~2.5′ on converse Sun) rather than retiming to force a match.

## Fixed inputs (fixed UTC offsets, no DST)

### Radix cohort

| Key | Event | UTC | Location |
|-----|--------|-----|----------|
| FT | First trade | 2019-05-10 **15:50** | NYSE (40.7128°N, 74.0060°W) |
| INC | Delaware incorporation | 2013-03-14 **16:00** | 39°02′45″N, 75°29′32″W |
| DK | Dara Khosrowshahi | 1969-05-28 **09:00** | 35°41′N, 51°25′E |

### Research events (metadata labels only)

| Key | UTC |
|-----|-----|
| NEG-01 | 2026-02-04 **14:30** (from 09:30 −05) |
| POS-01 | 2026-08-07 **16:00** (from 12:00 −04) |

## Rerun steps

```bash
cd ~/Projects/aries   # or OWC volume path to the same repo
export PYTHONPATH="$PWD:$PWD/SWEP/src:local-patches/analysis/mini-studies/2026-10-26_uber-converse-cohort"

# Unit tests (converse UTC + Zet spot longitudes)
bash local-patches/analysis/mini-studies/2026-10-26_uber-converse-cohort/run_tests.sh

# Full Phases A–D CSV + reports
python3 local-patches/analysis/mini-studies/2026-10-26_uber-converse-cohort/analysis.py

# Optional: extra events CSV → one feature row per event (Phase E)
python3 local-patches/analysis/mini-studies/2026-10-26_uber-converse-cohort/cli.py --events-csv path/to/events.csv

# Zet fixture diff (where JSON transcriptions exist)
python3 local-patches/analysis/mini-studies/2026-10-26_uber-converse-cohort/scripts/compare_zet_fixtures.py
```

Outputs land in `output/`:

- `radix_positions.csv`, `converse_positions.csv`
- `cohort_longitude_aspects.csv`, `cohort_declination_contacts.csv`
- `converse_radix_longitude_aspects.csv`, `converse_radix_declination_contacts.csv`
- `event_feature_matrix.csv`, `phase_a_registry_check.csv`, `phase_c_*.csv`
- `report_NEG-01.md`, `report_POS-01.md`

## Mandatory converse UTC tests

| Radix | Event | Converse UTC |
|-------|--------|----------------|
| FT | NEG | 2012-08-12 17:10 |
| FT | POS | 2012-02-10 15:40 |
| INC | NEG | 2000-04-21 17:30 |
| INC | POS | 1999-10-20 16:00 |
| DK | NEG | 1912-09-18 03:30 |
| DK | POS | 1912-03-18 02:00 |

Implemented in `tests/test_converse_timestamps.py`.

## Phase status (see `output/run_summary.json` after run)

- **Phase A:** Inter-radix registry — see `phase_a_registry_check.csv`
- **Phase B:** Converse→radix aspects for 6 pairs — `converse_radix_*.csv`
- **Phase C:** Named contacts + ≤1° counts — `phase_c_*.csv`
- **Phase D:** `event_feature_matrix.csv`
- **Phase E:** `cli.py`
- **Stages 4–5:** `stats_scaffold.py` only (no claims at N=2)

## UBER.zdb on disk

Spotlight did not locate `UBER.zdb` on this Mac during setup; inputs above are taken from the study brief and Zet screenshots. Re-import or paste from Zet into Aries under collection **`UBER.zdb`** when the file is available locally.

## Earnings-reaction converse pipeline (2026-10-26+)

Extends the cohort study with EODHD earnings + OHLC (read-only):

- Earnings: `~/Projects/listok_fd/finance_data_downloader/data/eodhd_earnings/UBER.csv`
- OHLC: `~/Projects/listok/finance-data-downloader/finance_data_downloader/data/eodhd_ohlc/UBER.csv`

Setup venv once:

```bash
cd local-patches/analysis/mini-studies/2026-10-26_uber-converse-cohort
python3 -m venv .venv && .venv/bin/pip install -r requirements-earnings.txt
```

Run:

```bash
.venv/bin/python cli.py earnings-study --top-positive 10 --top-negative 10
# or: .venv/bin/python earnings_pipeline.py
```

Outputs: `earnings-study/output/` — Reports A–F, aspect CSVs, robustness/persistence CSVs, walk-forward JSON.

Report F covers leave-one-out, orb sensitivity, permutation nulls, and **earnings-quarter persistence runs** for slow movers (see `aspect_persistence_*.csv`). Top-10×2 extremes overlap ~77% of events; use `leaderboard_top3_*.csv` for sharper descriptives.

Converse event time: **09:30 America/New_York** on the mapped NYSE reaction session (not press-release time). Pre-IPO row `2019-02-15` excluded from market analysis.
