# Final — Cross-company CEO square-count study

Evaluated **2476** earnings events across **40** non-UBER companies. Company-level Pearson r (sq@1° vs CC): **25** negative / **15** positive (median r≈-0.044). Pooled model with company fixed effects: β(square_count)≈-0.1770 (consistent with preregistered negative sign). Holdout-stage Pearson r≈-0.051. This is independent replication testing on new companies; UBER discovery data are excluded from scoring.

{
  "run_utc": "2026-10-27T08:39:24.436584Z",
  "universe_csv": "cross-company-study/input/universe_cohort_all.csv",
  "exclude_ticker": "UBER",
  "n_companies_evaluated": 40,
  "n_events_evaluated": 2476,
  "companies_negative_pearson": 25,
  "companies_positive_pearson": 15,
  "median_company_pearson_r": -0.043895677722380594,
  "pooled_fe_coef_square_count_1deg": -0.1769900807858431,
  "holdout_pearson_r": -0.05107008923447149,
  "frozen_feature": "square_count_1deg",
  "frozen_orb_deg": 1.0,
  "seed": 20261027,
  "pilot_only": false
}