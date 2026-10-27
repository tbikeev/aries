# BR-3.5 — Coverage audit and balanced sample design

## Original BR-3 sample (sensitivity)
- 100 EWZ adj extremes (50 NEG + 50 POS), unchanged.
- Copied to `event_manifest_all_history_sensitivity.parquet`.

## Ticker × tail eligible counts (original 100 events)

```
ticker,NEG,POS,total
ABEV,14,15,29
BBD,44,48,92
ERJ,1,1,2
ITUB,46,48,94
NU,3,2,5
PAGS,12,10,22
PBR,50,50,100
STNE,12,9,21
VALE,17,17,34
XP,12,9,21
```

## ERJ audit (2 eligible observations)

Almost all BR-3 events are excluded by event_before_ft, not missing OHLC. universe_ft_registry.csv lists ERJ/EMBJ ft_date=2025-11-03 (Munkasey), while Yahoo EMBJ daily bars begin 2000-07-21. Only sessions strictly after 2025-11-03 can qualify; among the top-100 EWZ extremes that is 2026-10-05 and 2026-10-26.

- Registry FT date: **2025-11-03**
- EMBJ OHLC from: **2000-07-24** (6605 return days)
- Eligible sessions in top-100: **['2026-10-26', '2026-10-05']**
- Ineligible reasons: `{'event_before_ft': 98, 'ok': 2}`

Source a historically correct Embraer ADR first-trade timestamp for strict cohorts, or exclude ERJ from pre-2025 event panels until FT is corrected. Do not infer listing from Yahoo alone without documentary FT.

## EWZ sessions by minimum eligible tickers (full calendar)

- ≥5 tickers: **3258** sessions
- ≥7 tickers: **2010** sessions
- ≥9 tickers: **1224** sessions

## Coverage-controlled reselection
- Rule: sessions with ≥**7** eligible tickers, then top/bottom EWZ **adj** returns.
- Pool size (≥7): **2010** sessions
- Selected per tail: **50** (neg avail 956, pos avail 1040)

Artifacts:
- `event_manifest_coverage_controlled.parquet`
- `ewz_session_eligible_ticker_counts.csv`
- `crash_rally_composition_by_year.csv`

## Next step (BR-4)
Re-run `aspect-matrices` against the coverage-controlled manifest before cell-level crash/rally diffs.