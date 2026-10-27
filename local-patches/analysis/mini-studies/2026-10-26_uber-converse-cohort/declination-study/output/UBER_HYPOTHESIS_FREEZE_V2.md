# UBER hypothesis freeze v2 (proposed Phase I addendum)

**Status:** Proposed successor to Phase H `hypothesis_freeze.json` — **not** overwriting Phase H.

## Classifications

| Candidate | Status |
|-----------|--------|
| DK converse major-square count ≤1° (earnings CC) | **Retain — frozen primary** (unchanged from Phase H) |
| All-cohort tight longitude count ≤1° | **Retain — frozen secondary** |
| DK Par/Cpar density | **Explanatory / not supported for prediction** unless incremental tests justify |
| Dual-coordinate reinforcement | See Phase I counts; **insufficient or explanatory** if n≤2 stable events |
| Cross-cohort declination network activation | **Explanatory only** |
| 21°–22° declination band | **Diagnostic only** (not privileged) |

## Phase I decision (plain)

DK longitude squares remain the strongest directional signal (r≈-0.519). DK Par density @0.5° vs CC: r≈0.221 (opposite sign to squares; surrogate p≈0.259). Dual-coordinate pair contacts (26 events): 32; L+R adds negligible ΔR². L+D in-sample ΔR² vs L: 0.080; LOO R² L=0.142, L+D=0.086. Recommendation: retain longitude-first freeze; treat declination as explanatory unless OOS confirms.

## Answers A–F

**A. Par/Cpar beyond DK squares?** Weak positive DK declination density (Par r≈0.221, total r≈0.284) vs negative square association (r≈-0.519). Declination-only model underperforms longitude; L+D raises in-sample R² but LOO stays fragile. **Do not add to frozen predictive set.**

**B. Dual-coordinate reinforcement?** 32 same-pair lon+decl contacts exist, but L+R adds ~0 ΔR² over L. **Explanatory only.**

**C. Shared cohort declination networks?** L+N adds small ΔR²; no case for expanding frozen FT/INC/DK family on declination grounds alone. **Explanatory only.**

**D. Genuine vs surrogate radix?** DK Par/total declination correlations are not extreme vs 1000 random DK radices (p≈0.259 Par, p≈0.147 total) — unlike Phase H longitude squares. **Declination does not replicate longitude’s radix-specificity signal.**

**E. Beyond earnings?** Ordinary-session DK Par vs CC: not computed (run `phase-i --build-daily-cache`). Earnings-specificity for squares was established in Phase G; declination ordinary-day check pending cache.

**F. Transfer to multi-company study?** Carry unchanged: converse timestamp, directed converse→radix aspects, DK major-square count @1°, orb presets (lon 0.5°/1°; decl 0.25°/0.5°/1°), placebo/shift methodology. **Do not transfer** DK Par/Cpar counts as co-primary hypotheses without OOS.

**Constraint:** Phase I cannot validate; it may only propose additions for independent OOS testing.
