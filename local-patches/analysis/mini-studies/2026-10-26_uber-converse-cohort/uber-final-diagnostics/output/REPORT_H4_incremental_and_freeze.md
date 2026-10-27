# Report H4 — Incremental FT/INC beyond DK (exploratory)

```json
{
  "exploratory": true,
  "n": 26,
  "target": "r_cc_pct",
  "pearson_DK": -0.5189825030597046,
  "pearson_FT": 0.17863425046767006,
  "pearson_INC": 0.09436723103884528,
  "r2_DK_only": 0.2693428384821165,
  "r2_DK_FT_INC": 0.29268552791688585,
  "delta_r2_adding_FT_INC": 0.02334268943476936,
  "partial_corr_DK_given_FT_INC": -0.508309309176359,
  "partial_corr_FT_given_DK_INC": -0.02115824985502938,
  "partial_corr_INC_given_DK_FT": -0.17540312898890092,
  "note": "Large delta_r2 on N=26 is not validated; signs of FT/INC partials indicate incremental direction only."
}
```

# Hypothesis freeze

```json
{
  "status": "frozen_exploratory_hypotheses",
  "as_of_utc": "2026-10-27T06:51:29.856653Z",
  "primary_directional": "DK converse major-square count at orb 1.0\u00b0 on earnings-reaction sessions",
  "secondary_density": "All-cohort tight major-aspect count at orb 1.0\u00b0 on earnings-reaction sessions",
  "cohort_specificity": "Retain FT/INC/DK separately; do not pool squares without preregistration",
  "event_scope": "Earnings-reaction days only until prospective OOS earnings validate",
  "daily_panel_finding": "No meaningful DK square association on ordinary days (see daily-study Report G)",
  "forbidden_until_oos": [
    "New aspect combinations from mining",
    "Orb threshold tuning beyond {0.5\u00b0, 1.0\u00b0}",
    "DK birth-time optimization"
  ]
}
```