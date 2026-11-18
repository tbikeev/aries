# Phase BR-2 — Historical Brazilian shocks

Primary BR-2 longitude set (same as BR-1 / UBER benchmark): Sun, Moon, Mercury, Venus, Mars, Jupiter, Saturn, Uranus, Neptune, Pluto, Node. Optional bodies (Chiron, Lilith) excluded from primary counts.

- Unique shock **dates** in registry: **97**
- Independent **episodes** (clustered): **84**
- Validation-eligible dates (excl. 2026-10-26 discovery): **96**
- Panel rows (ticker×date): **468**

## Decision questions

1. **C2C higher in crashes than rallies?** Validation Pearson(mean C2C hard, EWZ): **0.10819739851663113**. Crash−rally mean C2C hard: **1.0691425120772948** vs **1.210204081632653**.
2. **Survives excluding Oct 2026 election?** Validation sample excludes 2026-10-26; 2026-10-05 remains in validation (same cycle — interpret cautiously).
3. **Genuine FT vs random FT?** Genuine r=0.108; random-FT empirical p≈0.264.
4. **C2C vs C2R?** See `c2c_vs_c2r_comparison.csv` (validation episodes).
5. **Independent episodes?** See `one_day_per_episode_min_ewz` row in market_direction_results.
6. **Cross-sectional abnormal vs C2C?** Median episode Spearman: **0.0**; negative episodes: **39** / **95**.
7. **Walk-forward directional accuracy?** Mean hit rate: **0.52** over **90** expanding-window steps.
8. **Reproducible signal?** Treat negative answers on 3–7 as failure to generalize the 2026 C2C pattern.

## Artifacts

All CSVs under `output/br2/`. Discovery date 2026-10-26 included in descriptive panels only; validation metrics exclude it by construction.

## Strict vs approximate FT

Strict-timestamp rows: **192** / 468
