# Report G — Daily converse panel (frozen hypotheses)

Trading sessions: **1825**; earnings-reaction labels: **26**.
Slow-body activation episodes (≤1°, outer converse): **566** (effective independent structure ≪ session count).

## Primary question

Does **DK square count** relate negatively to daily CC returns on ordinary days, or only around earnings?

| Panel | DK sq @ 1° vs CC r |
|-------|-------------------|
| Full sample | -0.0260 |
| Ordinary days only | -0.0105 |
| Earnings-reaction days | -0.5190 |

## Frozen feature correlations by stratum

| stratum           | feature                  | target   |    n |   pearson_r |
|:------------------|:-------------------------|:---------|-----:|------------:|
| earnings_reaction | DK_sq_count_orb05        | r_cc_pct |   26 | -0.458938   |
| earnings_reaction | DK_sq_count_orb10        | r_cc_pct |   26 | -0.518983   |
| earnings_reaction | FT_sq_count_orb05        | r_cc_pct |   26 |  0.128492   |
| earnings_reaction | FT_sq_count_orb10        | r_cc_pct |   26 |  0.178634   |
| earnings_reaction | INC_sq_count_orb05       | r_cc_pct |   26 | -0.176871   |
| earnings_reaction | INC_sq_count_orb10       | r_cc_pct |   26 |  0.0943672  |
| earnings_reaction | tight_aspect_count_orb05 | r_cc_pct |   26 | -0.460682   |
| earnings_reaction | tight_aspect_count_orb10 | r_cc_pct |   26 | -0.384655   |
| ordinary          | DK_sq_count_orb05        | r_cc_pct | 1799 | -0.0092453  |
| ordinary          | DK_sq_count_orb10        | r_cc_pct | 1799 | -0.0105283  |
| ordinary          | FT_sq_count_orb05        | r_cc_pct | 1799 |  0.0177892  |
| ordinary          | FT_sq_count_orb10        | r_cc_pct | 1799 |  0.018619   |
| ordinary          | INC_sq_count_orb05       | r_cc_pct | 1799 | -0.00584668 |
| ordinary          | INC_sq_count_orb10       | r_cc_pct | 1799 | -0.0112995  |
| ordinary          | tight_aspect_count_orb05 | r_cc_pct | 1799 | -0.0123184  |
| ordinary          | tight_aspect_count_orb10 | r_cc_pct | 1799 |  0.00250499 |

## Multiple-testing-aware null (max |r| across frozen features, label shuffle)

```json
{
  "observed_max_abs_r": 0.02999021902550797,
  "per_feature_r": {
    "DK_sq_count_orb05": -0.022398560559439114,
    "DK_sq_count_orb10": -0.025984570169404968,
    "FT_sq_count_orb05": 0.01856558672971323,
    "FT_sq_count_orb10": 0.021061343335834818,
    "INC_sq_count_orb05": -0.011767538295209113,
    "INC_sq_count_orb10": -0.007111677237469101,
    "tight_aspect_count_orb05": -0.02999021902550795,
    "tight_aspect_count_orb10": -0.01022287433150732
  },
  "p_max_stat_shuffle": 0.744,
  "n_features": 8,
  "n_perm": 999,
  "note": "Compares best |r| among frozen features to shuffle null (not full mining search)."
}
```

## Interpretation guide

- Negative r on **ordinary** + **earnings**: candidate general directional link.
- Negative only on **earnings**: event-conditioned (consistent with small-sample discovery).
- Near zero on ordinary with earnings-only signal: daily panel mostly dilutes event effect.

Earnings discovery stage remains frozen under `earnings-study/output/`.