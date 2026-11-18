# Report I5 — Incremental models

| model   | target    | features                                                 |   n |   r2_in_sample |   delta_r2_vs_L |     loo_r2 |   partial_corr_DK_sq_given_decl |
|:--------|:----------|:---------------------------------------------------------|----:|---------------:|----------------:|-----------:|--------------------------------:|
| L       | r_cc_pct  | DK_sq_count_orb10                                        |  26 |      0.269343  |     0           |  0.141787  |                      nan        |
| D       | r_cc_pct  | DK_par_count_orb05,DK_cpar_count_orb05                   |  26 |      0.0836816 |    -0.185661    | -0.138498  |                      nan        |
| L+D     | r_cc_pct  | DK_sq_count_orb10,DK_par_count_orb05,DK_cpar_count_orb05 |  26 |      0.349025  |     0.0796821   |  0.0855926 |                       -0.538122 |
| L+R     | r_cc_pct  | DK_sq_count_orb10,DK_double_activation_count             |  26 |      0.269649  |     0.000306586 |  0.0437385 |                      nan        |
| L+N     | r_cc_pct  | DK_sq_count_orb10,network_both_endpoints                 |  26 |      0.287486  |     0.0181429   |  0.100158  |                      nan        |
| L       | r_gap_pct | DK_sq_count_orb10                                        |  26 |      0.212504  |     0           |  0.0734832 |                      nan        |
| D       | r_gap_pct | DK_par_count_orb05,DK_cpar_count_orb05                   |  26 |      0.0214977 |    -0.191006    | -0.206492  |                      nan        |
| L+D     | r_gap_pct | DK_sq_count_orb10,DK_par_count_orb05,DK_cpar_count_orb05 |  26 |      0.261366  |     0.0488627   | -0.0352317 |                       -0.495115 |
| L+R     | r_gap_pct | DK_sq_count_orb10,DK_double_activation_count             |  26 |      0.251347  |     0.0388436   |  0.0371899 |                      nan        |
| L+N     | r_gap_pct | DK_sq_count_orb10,network_both_endpoints                 |  26 |      0.23536   |     0.022856    |  0.0384832 |                      nan        |