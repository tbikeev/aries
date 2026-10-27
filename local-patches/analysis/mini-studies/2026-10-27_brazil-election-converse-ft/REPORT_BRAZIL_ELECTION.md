# Brazil election shock — converse first-trade study

Event: **2026-10-26** 09:30 America/New_York (Brazil presidential runoff 25 Oct 2026).
Primary return: close(2026-10-26) vs close(2026-10-23), unadjusted Yahoo close.

## 1. PAGS Zet reproduction

See `pags_zet_reproduction.md`. Without `fixtures/pags_zet_reference.json`, validation is manual.
Engine uses `T_conv = 2×T_FT − T_event`, Swiss Ephemeris, tropical geocentric.

## 2. Tight hard aspects (converse→radix, ≤1° conj/sq/opp)

- Universe with computed charts: **10**
- Strict FT timestamp cohort: **6** tickers
- Names with ≥1 tight c2r hard aspect: **9**

### Returns (close-to-close %)

```
ticker,return_cc_pct,return_vs_ewz_pp
XP,-48.35580400358814,-28.538948881562163
BBD,-28.009829405948793,-8.192974283922815
STNE,-27.43902216146471,-7.622167039438732
PAGS,-25.17481876227574,-5.357963640249764
ITUB,-20.372288019503483,-0.5554328974775053
NU,-16.952504753902954,2.8643503681230236
ABEV,-14.242425315198393,5.574429806827585
PBR,-13.99082518639302,5.826029935632958
VALE,-3.2258034744817476,16.59105164754423
ERJ,0.32468008021420136,20.141535202240178
```

## 3. Historical unusualness (strict cohort)

```
ticker,event_c2r_hard_1deg,historical_n_sessions,event_day_percentile,historical_median
PAGS,2,100,0.6237623762376238,2.0
XP,1,100,0.21782178217821782,3.0
STNE,5,100,0.9801980198019802,2.0
NU,2,100,0.42574257425742573,3.0
ITUB,3,100,0.7326732673267327,2.0
ERJ,2,100,0.6237623762376238,2.0
```

## 4. Losers vs resilient (descriptive)

```
group,tickers,mean_return_cc_pct,mean_c2r_hard_1deg,mean_c2c_hard_1deg,mean_c2r_sq_1deg
losers_bottom4,"BBD,PAGS,STNE,XP",-32.244868583319345,3.25,2.25,0.75
resilient_top3,"ERJ,PBR,VALE",-5.630649526886856,2.3333333333333335,0.6666666666666666,1.3333333333333333
```

## 5. Cross-sectional correlations (exploratory, N≈11, one shared shock)

```
feature,pearson_r,spearman_rho,n
c2r_sq_count_1deg,0.33105931701607527,0.2774167928588263,10
c2r_sq_opp_count_1deg,0.08265789236178632,-0.012712834523274546,10
c2r_hard_count_1deg,-0.0730614663090507,-0.18881372801234023,10
c2c_sq_count_1deg,-0.4627493184758603,-0.36058790975563576,10
c2c_sq_opp_count_1deg,-0.574626129250497,-0.33734954246999316,10
c2c_hard_count_1deg,-0.5531405245493691,-0.424467415469201,10
c2r_decl_contact_count_1deg,-0.22153096053504132,-0.3353720883255073,10
c2c_decl_contact_count_1deg,0.17029542890559374,0.19756474308710287,10
```

## 6. Converse→converse vs converse→radix

Compare `c2r_*` vs `c2c_*` columns in correlation table; do not treat as independent evidence.

## 7. FT timestamp sensitivity

Approximate-noon FT used when Munkasey time missing: ['BBD', 'PBR', 'ABEV', 'EBR', 'VALE']

## 8. Placebos

```
placebo_type,shift,mean_c2r_hard_1deg,observed_election_mean,empirical_p_ge_observed
date_shift_days,-180,2.3333333333333335,2.5,
date_shift_days,-90,3.0,2.5,
date_shift_days,-30,1.1666666666666667,2.5,
date_shift_days,30,1.8333333333333333,2.5,
date_shift_days,90,3.1666666666666665,2.5,
date_shift_days,180,3.3333333333333335,2.5,
radix_shift_days,-180,3.3333333333333335,2.5,
radix_shift_days,-90,3.1666666666666665,2.5,
radix_shift_days,-30,2.3333333333333335,2.5,
radix_shift_days,30,2.8333333333333335,2.5,
radix_shift_days,90,3.3333333333333335,2.5,
radix_shift_days,180,2.8333333333333335,2.5,
random_ft_jd,"n=200, seed=20261027",2.6666666666666665,2.5,0.6417910447761194
```

## 9. Independent historical shocks?

Eleven names share one election; cross-sectional correlation is **hypothesis-generating only**.
Use `brazil_shock_dates_ewz.csv` and per-company historical percentiles before predictive claims.

## Leave-one-out (c2r_hard_count_1deg vs return)

```
dropped_ticker,feature,pearson_r
PAGS,c2r_hard_count_1deg,-0.08979503627054654
XP,c2r_hard_count_1deg,-0.48671147175992446
STNE,c2r_hard_count_1deg,0.043542888620336215
NU,c2r_hard_count_1deg,-0.06575656215634014
ITUB,c2r_hard_count_1deg,-0.07174152608790663
BBD,c2r_hard_count_1deg,0.05358277191313255
PBR,c2r_hard_count_1deg,-0.05780224106153167
ABEV,c2r_hard_count_1deg,0.005534264948593336
VALE,c2r_hard_count_1deg,-0.13265225358392127
ERJ,c2r_hard_count_1deg,-0.019219152971751873
```

## Executive answers

1. **PAGS reproduction:** PAGS engine output is in `pags_zet_reproduction.md`. Automated Zet diff pending `fixtures/pags_zet_reference.json` (not supplied in repo).
2. **Tight hard aspects:** 9 of 10 tickers show ≥1 converse→radix hard aspect ≤1°.
3. **Unusual vs history:** Median event-day percentile of c2r hard count (strict cohort): 0.62 (1.0 = max vs ~100 ordinary sessions).
4. **Losers vs resilient:** Losers mean c2r hard @1°: 3.2 vs resilient: 2.3 — descriptive only.
5. **C2C vs C2R:** Pearson r(return, c2r hard): -0.073; c2c hard: -0.553 if |c2c| > |c2r| explore internal geometry; else radix contacts dominate exploratory fit.
6. **FT uncertainty:** Strict timestamp: 6 names; noon-ET sensitivity for: ['BBD', 'PBR', 'ABEV', 'EBR', 'VALE'].
7. **Next steps:** One shared shock with N≈10 usable returns does **not** validate prediction; test on OHLC-defined Brazil shocks (`brazil_shock_dates_ewz.csv`) before any predictive claim.
