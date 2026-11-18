# Report D — Feature reduction (exploratory)

## Correlation with CC return
| feature            |   corr_with_r_cc |   mean_when_up |   mean_when_down |
|:-------------------|-----------------:|---------------:|-----------------:|
| DK_sq_count        |       -0.518983  |       1.07143  |         2.16667  |
| DK_opp_count       |       -0.456159  |       0.214286 |         0.833333 |
| DK_tight_count     |       -0.450205  |       4.71429  |         6.75     |
| INC_conj_count     |       -0.394595  |       0.428571 |         1.08333  |
| tight_aspect_count |       -0.384655  |      15.0714   |        17.8333   |
| DK_conj_count      |        0.341442  |       0.714286 |         0.25     |
| FT_opp_count       |       -0.199253  |       0.928571 |         1.16667  |
| INC_sext_count     |        0.180356  |       1.57143  |         1.41667  |
| FT_sq_count        |        0.178634  |       0.928571 |         0.5      |
| FT_tri_count       |       -0.167644  |       1.28571  |         1.83333  |
| FT_tight_count     |       -0.153667  |       5        |         5.5      |
| DK_sext_count      |       -0.120626  |       1.28571  |         1.83333  |
| INC_tri_count      |        0.113739  |       1.21429  |         1.25     |
| DK_tri_count       |       -0.100252  |       1.42857  |         1.66667  |
| INC_sq_count       |        0.0943672 |       1.85714  |         1.5      |
| FT_conj_count      |       -0.0606016 |       0.428571 |         0.5      |
| FT_sext_count      |       -0.0500584 |       1.42857  |         1.5      |
| INC_opp_count      |       -0.0448201 |       0.285714 |         0.333333 |
| INC_tight_count    |        0.0405232 |       5.35714  |         5.58333  |

## Frequent in extremes
| signature                          |   count_all |   count_extreme | extreme_report_dates                                              |   mean_orb |
|:-----------------------------------|------------:|----------------:|:------------------------------------------------------------------|-----------:|
| DK|conv:Pluto|radix:Saturn|sext    |           6 |               6 | 2020-08-06;2021-05-05;2021-11-04;2022-02-09;2022-05-04;2023-02-08 |   0.363971 |
| INC|conv:Sun|radix:Moon|sq         |           5 |               5 | 2020-05-07;2020-11-05;2021-11-04;2023-11-07;2024-05-08            |   0.412208 |
| DK|conv:Pluto|radix:Uranus|sq      |           6 |               4 | 2023-08-01;2024-05-08;2024-08-06;2024-10-31                       |   0.450387 |
| DK|conv:Neptune|radix:Neptune|tri  |           4 |               4 | 2023-08-01;2024-05-08;2024-10-31;2025-02-05                       |   0.513402 |
| FT|conv:Pluto|radix:Node|opp       |           4 |               4 | 2019-11-04;2020-02-06;2020-08-06;2021-05-05                       |   0.243007 |
| FT|conv:Pluto|radix:Sun|tri        |           4 |               4 | 2019-11-04;2020-02-06;2020-08-06;2021-05-05                       |   0.425199 |
| INC|conv:Neptune|radix:Uranus|sext |           4 |               4 | 2023-08-01;2024-05-08;2024-10-31;2025-02-05                       |   0.533284 |
| FT|conv:Pluto|radix:Neptune|sext   |           5 |               3 | 2019-11-04;2020-11-05;2022-05-04                                  |   0.731977 |
| DK|conv:Neptune|radix:Uranus|sext  |           4 |               3 | 2022-08-02;2023-05-02;2023-11-07                                  |   0.249863 |
| DK|conv:Sun|radix:Jupiter|sq       |           4 |               3 | 2019-11-04;2020-05-07;2021-11-04                                  |   0.407052 |
| FT|conv:Neptune|radix:Mercury|sext |           4 |               3 | 2022-11-01;2023-08-01;2024-05-08                                  |   0.392345 |
| INC|conv:Neptune|radix:Saturn|sq   |           4 |               3 | 2022-08-02;2022-11-01;2023-05-02                                  |   0.604175 |
| INC|conv:Pluto|radix:Sun|sq        |           4 |               3 | 2019-08-08;2019-11-04;2021-05-05                                  |   0.42248  |
| INC|conv:Pluto|radix:Venus|sq      |           4 |               3 | 2021-11-04;2022-05-04;2023-02-08                                  |   0.674528 |
| INC|conv:Uranus|radix:Moon|sext    |           4 |               3 | 2022-08-02;2023-05-02;2023-11-07                                  |   0.538999 |
| DK|conv:Neptune|radix:Node|tri     |           3 |               3 | 2023-08-01;2024-10-31;2025-02-05                                  |   0.161011 |
| DK|conv:Sun|radix:Uranus|sq        |           3 |               3 | 2022-05-04;2022-11-01;2024-10-31                                  |   0.555622 |
| FT|conv:Sun|radix:Node|tri         |           3 |               3 | 2019-11-04;2020-11-05;2021-11-04                                  |   0.735831 |
| INC|conv:Moon|radix:Node|sext      |           3 |               3 | 2019-08-08;2020-11-05;2021-11-04                                  |   0.259682 |
| INC|conv:Saturn|radix:Uranus|sq    |           3 |               3 | 2022-02-09;2022-05-04;2022-11-01                                  |   0.414686 |