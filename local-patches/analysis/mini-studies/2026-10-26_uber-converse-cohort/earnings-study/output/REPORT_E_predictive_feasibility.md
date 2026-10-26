# Report E — Predictive feasibility

{
  "feasibility": {
    "valid_earnings_reactions": 26,
    "extreme_discovery_sample": 20,
    "extreme_share_of_valid": 0.7692,
    "high_dimensional_risk": true,
    "recommendation": "Use 20 extremes for hypothesis generation only; evaluate patterns on all 26 reactions with chronological splits and permutation tests before any predictive claim."
  },
  "walk_forward_majority_sign_baseline": {
    "n_events": 26,
    "n_folds": 18,
    "majority_sign_accuracy": 0.4444444444444444,
    "note": "Astrological features not used in this baseline fold; use feature_reduction for exploratory assoc."
  },
  "walk_forward_fixed_feature_models_exploratory": {
    "model_a_sq_counts": {
      "model": "model_a_sq_counts",
      "features": [
        "FT_sq_count",
        "INC_sq_count",
        "DK_sq_count"
      ],
      "n_events": 26,
      "n_folds": 18,
      "direction_accuracy": 0.7222222222222222,
      "mae_abs_r_cc": 3.4627342397675993,
      "mae_baseline_predict_train_mean_abs": 6.71724248846365,
      "note": "Exploratory on same sample if features were selected after viewing outcomes."
    },
    "model_b_density_dk_sq": {
      "model": "model_b_density_dk_sq",
      "features": [
        "tight_aspect_count",
        "DK_sq_count"
      ],
      "n_events": 26,
      "n_folds": 18,
      "direction_accuracy": 0.8333333333333334,
      "mae_abs_r_cc": 3.539465713200059,
      "mae_baseline_predict_train_mean_abs": 6.71724248846365,
      "note": "Exploratory on same sample if features were selected after viewing outcomes."
    },
    "model_c_preselected_sigs": {
      "model": "model_c_preselected_sigs",
      "features": [
        "preselected_sig_count",
        "preselected_sig_orb_sum"
      ],
      "n_events": 26,
      "n_folds": 18,
      "direction_accuracy": 0.7222222222222222,
      "mae_abs_r_cc": 3.654316617260278,
      "mae_baseline_predict_train_mean_abs": 6.71724248846365,
      "note": "Exploratory on same sample if features were selected after viewing outcomes."
    }
  },
  "walk_forward_volatility_baseline": {
    "model": "baseline_history_mean_abs",
    "n_folds": 18,
    "direction_accuracy": 0.4444444444444444,
    "mae_abs_r_cc": 3.5954561701768406
  }
}