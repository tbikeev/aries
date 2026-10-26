# Report E — Predictive feasibility

{
  "feasibility": {
    "valid_earnings_reactions": 26,
    "extreme_discovery_sample": 20,
    "high_dimensional_risk": true,
    "recommendation": "Use 20 extremes for hypothesis generation only; evaluate patterns on all 26 reactions with chronological splits and permutation tests before any predictive claim."
  },
  "walk_forward_baseline": {
    "n_events": 26,
    "n_folds": 18,
    "majority_sign_accuracy": 0.4444444444444444,
    "note": "Astrological features not used in this baseline fold; use feature_reduction for exploratory assoc."
  }
}