# Report F — Robustness and temporal persistence

Exploratory statistics on N≈26; permutation p-values are approximate.

## Leave-one-out (correlation with CC return)
| feature            |   corr_full |   corr_loo_min |   corr_loo_max | sign_stable   |   max_abs_delta |
|:-------------------|------------:|---------------:|---------------:|:--------------|----------------:|
| DK_sq_count        |  -0.518983  |     -0.601754  |      -0.46556  | True          |       0.0827718 |
| tight_aspect_count |  -0.384655  |     -0.446846  |      -0.32815  | True          |       0.0621917 |
| FT_sq_count        |   0.178634  |      0.133366  |       0.263708 | True          |       0.0850735 |
| INC_sq_count       |   0.0943672 |      0.0307332 |       0.185976 | True          |       0.0916092 |

## Orb threshold sensitivity
|   orb_max_deg | feature            |   n |   corr_with_r_cc |   corr_with_abs_r_cc |
|--------------:|:-------------------|----:|-----------------:|---------------------:|
|          0.25 | DK_sq_count        |  25 |       -0.202811  |           -0.084627  |
|          0.25 | tight_aspect_count |  25 |       -0.257014  |           -0.307055  |
|          0.25 | FT_sq_count        |  25 |        0.148469  |            0.0253822 |
|          0.25 | INC_sq_count       |  25 |       -0.174619  |           -0.270527  |
|          0.5  | DK_sq_count        |  26 |       -0.458938  |           -0.0373928 |
|          0.5  | tight_aspect_count |  26 |       -0.460682  |           -0.319792  |
|          0.5  | FT_sq_count        |  26 |        0.128492  |           -0.192992  |
|          0.5  | INC_sq_count       |  26 |       -0.176871  |           -0.380041  |
|          1    | DK_sq_count        |  26 |       -0.518983  |           -0.117864  |
|          1    | tight_aspect_count |  26 |       -0.384655  |            0.0851655 |
|          1    | FT_sq_count        |  26 |        0.178634  |           -0.113442  |
|          1    | INC_sq_count       |  26 |        0.0943672 |           -0.0464099 |
|          2    | DK_sq_count        |  26 |       -0.119202  |           -0.167981  |
|          2    | tight_aspect_count |  26 |       -0.0853622 |           -0.0719302 |
|          2    | FT_sq_count        |  26 |        0.25684   |           -0.23136   |
|          2    | INC_sq_count       |  26 |        0.141683  |           -0.180441  |

## Correlations excluding top-10 positive + top-10 negative
| subset                      |   n | feature            |   corr_with_r_cc |   corr_with_abs_r_cc |
|:----------------------------|----:|:-------------------|-----------------:|---------------------:|
| excluding_declared_extremes |   6 | DK_sq_count        |        0.277428  |           -0.192264  |
| excluding_declared_extremes |   6 | tight_aspect_count |        0.0674155 |            0.58074   |
| excluding_declared_extremes |   6 | FT_sq_count        |        0.752299  |           -0.0690751 |
| excluding_declared_extremes |   6 | INC_sq_count       |       -0.469664  |            0.357851  |

## Permutation tests (4999 shuffles, seed=42)
| feature            | target       |   n |   observed_corr |   permutation_p_two_sided |   n_perm |   seed |
|:-------------------|:-------------|----:|----------------:|--------------------------:|---------:|-------:|
| DK_sq_count        | r_cc_pct     |  26 |      -0.518983  |                    0.0074 |     4999 |     42 |
| DK_sq_count        | abs_r_cc_pct |  26 |      -0.117864  |                    0.565  |     4999 |     42 |
| tight_aspect_count | r_cc_pct     |  26 |      -0.384655  |                    0.0586 |     4999 |     42 |
| tight_aspect_count | abs_r_cc_pct |  26 |       0.0851655 |                    0.6852 |     4999 |     42 |

## Slow-body signatures: event hits vs independent earnings-quarter runs
| signature                          | radix_key   | converse_body   | radix_body   | aspect   | slow_converse_body   |   event_hits |   independent_runs |   max_run_length_quarters | all_report_dates                                                  |   persistence_ratio |
|:-----------------------------------|:------------|:----------------|:-------------|:---------|:---------------------|-------------:|-------------------:|--------------------------:|:------------------------------------------------------------------|--------------------:|
| DK|conv:Pluto|radix:Saturn|sext    | DK          | Pluto           | Saturn       | sext     | True                 |            6 |                  4 |                         3 | 2020-08-06;2021-05-05;2021-11-04;2022-02-09;2022-05-04;2023-02-08 |            0.666667 |
| DK|conv:Pluto|radix:Uranus|sq      | DK          | Pluto           | Uranus       | sq       | True                 |            6 |                  3 |                         3 | 2023-08-01;2024-05-08;2024-08-06;2024-10-31;2025-05-06;2025-05-07 |            0.5      |
| FT|conv:Pluto|radix:Neptune|sext   | FT          | Pluto           | Neptune      | sext     | True                 |            5 |                  4 |                         2 | 2019-11-04;2020-11-05;2021-02-10;2021-08-04;2022-05-04            |            0.8      |
| FT|conv:Pluto|radix:Sun|tri        | FT          | Pluto           | Sun          | tri      | True                 |            4 |                  3 |                         2 | 2019-11-04;2020-02-06;2020-08-06;2021-05-05                       |            0.75     |
| INC|conv:Uranus|radix:Moon|sext    | INC         | Uranus          | Moon         | sext     | True                 |            4 |                  3 |                         2 | 2022-08-02;2023-05-02;2023-11-07;2024-02-07                       |            0.75     |
| INC|conv:Pluto|radix:Venus|sq      | INC         | Pluto           | Venus        | sq       | True                 |            4 |                  3 |                         2 | 2021-08-04;2021-11-04;2022-05-04;2023-02-08                       |            0.75     |
| INC|conv:Pluto|radix:Sun|sq        | INC         | Pluto           | Sun          | sq       | True                 |            4 |                  2 |                         2 | 2019-08-08;2019-11-04;2021-02-10;2021-05-05                       |            0.5      |
| INC|conv:Neptune|radix:Saturn|sq   | INC         | Neptune         | Saturn       | sq       | True                 |            4 |                  3 |                         2 | 2022-08-02;2022-11-01;2023-05-02;2024-02-07                       |            0.75     |
| INC|conv:Neptune|radix:Uranus|sext | INC         | Neptune         | Uranus       | sext     | True                 |            4 |                  3 |                         2 | 2023-08-01;2024-05-08;2024-10-31;2025-02-05                       |            0.75     |
| FT|conv:Pluto|radix:Node|opp       | FT          | Pluto           | Node         | opp      | True                 |            4 |                  3 |                         2 | 2019-11-04;2020-02-06;2020-08-06;2021-05-05                       |            0.75     |
| FT|conv:Neptune|radix:Mercury|sext | FT          | Neptune         | Mercury      | sext     | True                 |            4 |                  3 |                         2 | 2022-11-01;2023-08-01;2024-02-07;2024-05-08                       |            0.75     |
| DK|conv:Neptune|radix:Uranus|sext  | DK          | Neptune         | Uranus       | sext     | True                 |            4 |                  3 |                         2 | 2022-08-02;2023-05-02;2023-11-07;2024-02-07                       |            0.75     |
| DK|conv:Neptune|radix:Sun|sext     | DK          | Neptune         | Sun          | sext     | True                 |            4 |                  2 |                         2 | 2019-05-30;2019-08-08;2020-11-05;2021-02-10                       |            0.5      |
| DK|conv:Neptune|radix:Neptune|tri  | DK          | Neptune         | Neptune      | tri      | True                 |            4 |                  3 |                         2 | 2023-08-01;2024-05-08;2024-10-31;2025-02-05                       |            0.75     |
| INC|conv:Neptune|radix:Node|sq     | INC         | Neptune         | Node         | sq       | True                 |            4 |                  2 |                         3 | 2019-05-30;2019-08-08;2019-11-04;2021-02-10                       |            0.5      |
| DK|conv:Neptune|radix:Node|tri     | DK          | Neptune         | Node         | tri      | True                 |            3 |                  2 |                         2 | 2023-08-01;2024-10-31;2025-02-05                                  |            0.666667 |
| DK|conv:Saturn|radix:Venus|tri     | DK          | Saturn          | Venus        | tri      | True                 |            3 |                  2 |                         2 | 2019-05-30;2019-08-08;2020-02-06                                  |            0.666667 |
| FT|conv:Saturn|radix:Mars|opp      | FT          | Saturn          | Mars         | opp      | True                 |            3 |                  2 |                         2 | 2020-11-05;2021-05-05;2021-08-04                                  |            0.666667 |
| INC|conv:Saturn|radix:Uranus|sq    | INC         | Saturn          | Uranus       | sq       | True                 |            3 |                  2 |                         2 | 2022-02-09;2022-05-04;2022-11-01                                  |            0.666667 |
| INC|conv:Uranus|radix:Jupiter|sq   | INC         | Uranus          | Jupiter      | sq       | True                 |            3 |                  2 |                         2 | 2020-05-07;2020-11-05;2021-02-10                                  |            0.666667 |
| INC|conv:Uranus|radix:Mercury|conj | INC         | Uranus          | Mercury      | conj     | True                 |            3 |                  2 |                         2 | 2020-08-06;2021-11-04;2022-02-09                                  |            0.666667 |
| INC|conv:Uranus|radix:Saturn|tri   | INC         | Uranus          | Saturn       | tri      | True                 |            3 |                  2 |                         2 | 2019-05-30;2019-08-08;2020-11-05                                  |            0.666667 |

## Longest consecutive earnings-quarter activation runs (≤1°)
| signature                          | run_start   | run_end    |   quarters_in_run | report_dates                     | slow_converse_body   |   mean_orb_in_run |
|:-----------------------------------|:------------|:-----------|------------------:|:---------------------------------|:---------------------|------------------:|
| DK|conv:Pluto|radix:Saturn|sext    | 2021-11-04  | 2022-05-04 |                 3 | 2021-11-04;2022-02-09;2022-05-04 | True                 |         0.557941  |
| DK|conv:Pluto|radix:Uranus|sq      | 2024-05-08  | 2024-10-31 |                 3 | 2024-05-08;2024-08-06;2024-10-31 | True                 |         0.535998  |
| INC|conv:Neptune|radix:Node|sq     | 2019-05-30  | 2019-11-04 |                 3 | 2019-05-30;2019-08-08;2019-11-04 | True                 |         0.644182  |
| DK|conv:Mars|radix:Pluto|conj      | 2020-08-06  | 2020-11-05 |                 2 | 2020-08-06;2020-11-05            | False                |         0.540712  |
| DK|conv:Neptune|radix:Jupiter|sext | 2024-05-08  | 2024-08-06 |                 2 | 2024-05-08;2024-08-06            | True                 |         0.601161  |
| DK|conv:Neptune|radix:Mercury|sext | 2019-11-04  | 2020-02-06 |                 2 | 2019-11-04;2020-02-06            | True                 |         0.282414  |
| DK|conv:Neptune|radix:Neptune|tri  | 2024-10-31  | 2025-02-05 |                 2 | 2024-10-31;2025-02-05            | True                 |         0.534677  |
| DK|conv:Neptune|radix:Node|tri     | 2024-10-31  | 2025-02-05 |                 2 | 2024-10-31;2025-02-05            | True                 |         0.194035  |
| DK|conv:Neptune|radix:Sun|sext     | 2019-05-30  | 2019-08-08 |                 2 | 2019-05-30;2019-08-08            | True                 |         0.0603042 |
| DK|conv:Neptune|radix:Sun|sext     | 2020-11-05  | 2021-02-10 |                 2 | 2020-11-05;2021-02-10            | True                 |         0.403372  |
| DK|conv:Neptune|radix:Uranus|sext  | 2023-11-07  | 2024-02-07 |                 2 | 2023-11-07;2024-02-07            | True                 |         0.0657649 |
| DK|conv:Pluto|radix:Uranus|sq      | 2025-05-06  | 2025-05-07 |                 2 | 2025-05-06;2025-05-07            | True                 |         0.418774  |
| DK|conv:Saturn|radix:Venus|tri     | 2019-05-30  | 2019-08-08 |                 2 | 2019-05-30;2019-08-08            | True                 |         0.577525  |
| DK|conv:Uranus|radix:Mars|sext     | 2024-05-08  | 2024-08-06 |                 2 | 2024-05-08;2024-08-06            | True                 |         0.495625  |
| DK|conv:Uranus|radix:Mercury|tri   | 2023-11-07  | 2024-02-07 |                 2 | 2023-11-07;2024-02-07            | True                 |         0.514943  |
| DK|conv:Uranus|radix:Sun|tri       | 2025-05-06  | 2025-05-07 |                 2 | 2025-05-06;2025-05-07            | True                 |         0.167381  |
| FT|conv:Neptune|radix:Mercury|sext | 2024-02-07  | 2024-05-08 |                 2 | 2024-02-07;2024-05-08            | True                 |         0.359576  |
| FT|conv:Neptune|radix:Uranus|sext  | 2024-10-31  | 2025-02-05 |                 2 | 2024-10-31;2025-02-05            | True                 |         0.898941  |
| FT|conv:Pluto|radix:Neptune|sext   | 2020-11-05  | 2021-02-10 |                 2 | 2020-11-05;2021-02-10            | True                 |         0.850298  |
| FT|conv:Pluto|radix:Node|opp       | 2019-11-04  | 2020-02-06 |                 2 | 2019-11-04;2020-02-06            | True                 |         0.0738338 |