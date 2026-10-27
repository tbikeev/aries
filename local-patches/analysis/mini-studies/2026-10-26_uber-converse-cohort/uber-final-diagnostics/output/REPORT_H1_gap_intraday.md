# Report H1 — Gap vs intraday decomposition (exploratory)

CC identity check max error (bps): see h0 panel.

## DK square count @ 1° — conclusion

{
  "exploratory": true,
  "dk_sq_orb10_pearson_gap": -0.46098106590876736,
  "dk_sq_orb10_pearson_intra": -0.26899143917589774,
  "dk_sq_orb10_pearson_cc": -0.5189825030597046,
  "interpretation_hint": "Compare |r| on gap vs intra; stronger gap suggests overnight repricing channel."
}

## All frozen feature × target correlations

| feature                  | target          |   n |   pearson_r |   spearman_rho |   bootstrap_ci_95_lo |   bootstrap_ci_95_hi |   loo_r_min |   loo_r_max |   observed_r |   p_two_sided_shuffle | null                |   n_perm |
|:-------------------------|:----------------|----:|------------:|---------------:|---------------------:|---------------------:|------------:|------------:|-------------:|----------------------:|:--------------------|---------:|
| DK_sq_count_orb05        | r_cc_pct        |  26 | -0.458938   |    -0.432681   |           -0.685867  |           -0.142792  | -0.520208   |  -0.391086  |  -0.458938   |                0.02   | iid_shuffle_returns |     4999 |
| DK_sq_count_orb05        | r_gap_pct       |  26 | -0.344346   |    -0.315117   |           -0.595419  |           -0.0247091 | -0.418995   |  -0.285968  |  -0.344346   |                0.0864 | iid_shuffle_returns |     4999 |
| DK_sq_count_orb05        | r_intra_pct     |  26 | -0.35148    |    -0.341904   |           -0.620548  |           -0.0123727 | -0.42198    |  -0.294483  |  -0.35148    |                0.0768 | iid_shuffle_returns |     4999 |
| DK_sq_count_orb05        | abs_r_gap_pct   |  26 | -0.107766   |    -0.112356   |           -0.427848  |            0.256979  | -0.182686   |   0.0180586 |  -0.107766   |                0.6018 | iid_shuffle_returns |     4999 |
| DK_sq_count_orb05        | abs_r_intra_pct |  26 | -0.00615539 |    -0.0223223  |           -0.32009   |            0.295932  | -0.0636396  |   0.0780819 |  -0.00615539 |                0.9764 | iid_shuffle_returns |     4999 |
| DK_sq_count_orb10        | r_cc_pct        |  26 | -0.518983   |    -0.518806   |           -0.763777  |           -0.19342   | -0.601754   |  -0.46556   |  -0.518983   |                0.0074 | iid_shuffle_returns |     4999 |
| DK_sq_count_orb10        | r_gap_pct       |  26 | -0.460981   |    -0.458902   |           -0.720312  |           -0.120354  | -0.56417    |  -0.396909  |  -0.460981   |                0.0174 | iid_shuffle_returns |     4999 |
| DK_sq_count_orb10        | r_intra_pct     |  26 | -0.268991   |    -0.246388   |           -0.589164  |            0.103119  | -0.353476   |  -0.191641  |  -0.268991   |                0.1814 | iid_shuffle_returns |     4999 |
| DK_sq_count_orb10        | abs_r_gap_pct   |  26 | -0.163539   |    -0.111249   |           -0.521211  |            0.303377  | -0.263615   |  -0.012222  |  -0.163539   |                0.4316 | iid_shuffle_returns |     4999 |
| DK_sq_count_orb10        | abs_r_intra_pct |  26 |  0.0393804  |     0.00606165 |           -0.28749   |            0.334445  | -0.0118701  |   0.143652  |   0.0393804  |                0.8502 | iid_shuffle_returns |     4999 |
| tight_aspect_count_orb05 | r_cc_pct        |  26 | -0.460682   |    -0.409528   |           -0.765898  |           -0.0495709 | -0.588659   |  -0.382494  |  -0.460682   |                0.0186 | iid_shuffle_returns |     4999 |
| tight_aspect_count_orb05 | r_gap_pct       |  26 | -0.309796   |    -0.310593   |           -0.637565  |            0.0886559 | -0.393986   |  -0.201724  |  -0.309796   |                0.127  | iid_shuffle_returns |     4999 |
| tight_aspect_count_orb05 | r_intra_pct     |  26 | -0.393641   |    -0.309904   |           -0.682794  |            0.014988  | -0.494751   |  -0.242994  |  -0.393641   |                0.0506 | iid_shuffle_returns |     4999 |
| tight_aspect_count_orb05 | abs_r_gap_pct   |  26 | -0.263881   |    -0.155124   |           -0.521498  |            0.13078   | -0.310592   |  -0.117615  |  -0.263881   |                0.1868 | iid_shuffle_returns |     4999 |
| tight_aspect_count_orb05 | abs_r_intra_pct |  26 |  0.0930005  |     0.0117205  |           -0.33343   |            0.460509  | -0.152576   |   0.147038  |   0.0930005  |                0.654  | iid_shuffle_returns |     4999 |
| tight_aspect_count_orb10 | r_cc_pct        |  26 | -0.384655   |    -0.421822   |           -0.666987  |           -0.0744654 | -0.446846   |  -0.32815   |  -0.384655   |                0.0586 | iid_shuffle_returns |     4999 |
| tight_aspect_count_orb10 | r_gap_pct       |  26 | -0.296124   |    -0.40049    |           -0.623052  |            0.0414809 | -0.377988   |  -0.240334  |  -0.296124   |                0.1474 | iid_shuffle_returns |     4999 |
| tight_aspect_count_orb10 | r_intra_pct     |  26 | -0.270382   |    -0.289013   |           -0.604108  |            0.103486  | -0.364831   |  -0.197778  |  -0.270382   |                0.1906 | iid_shuffle_returns |     4999 |
| tight_aspect_count_orb10 | abs_r_gap_pct   |  26 |  0.0386867  |     0.0808549  |           -0.230626  |            0.300258  | -0.00540679 |   0.0847496 |   0.0386867  |                0.8534 | iid_shuffle_returns |     4999 |
| tight_aspect_count_orb10 | abs_r_intra_pct |  26 |  0.162198   |     0.0822312  |           -0.194896  |            0.465481  |  0.0669538  |   0.233131  |   0.162198   |                0.4236 | iid_shuffle_returns |     4999 |
| FT_sq_count_orb10        | r_cc_pct        |  26 |  0.178634   |     0.197786   |           -0.135709  |            0.486575  |  0.133366   |   0.263708  |   0.178634   |                0.3884 | iid_shuffle_returns |     4999 |
| FT_sq_count_orb10        | r_gap_pct       |  26 | -0.0279051  |     0.103029   |           -0.349967  |            0.392005  | -0.084067   |   0.062125  |  -0.0279051  |                0.8948 | iid_shuffle_returns |     4999 |
| FT_sq_count_orb10        | r_intra_pct     |  26 |  0.428866   |     0.403844   |            0.0774758 |            0.688234  |  0.313419   |   0.517647  |   0.428866   |                0.0306 | iid_shuffle_returns |     4999 |
| FT_sq_count_orb10        | abs_r_gap_pct   |  26 | -0.0532706  |    -0.0229371  |           -0.347512  |            0.294112  | -0.119322   |   0.0357924 |  -0.0532706  |                0.789  | iid_shuffle_returns |     4999 |
| FT_sq_count_orb10        | abs_r_intra_pct |  26 |  0.4243     |     0.422645   |            0.0409056 |            0.681826  |  0.305335   |   0.528941  |   0.4243     |                0.032  | iid_shuffle_returns |     4999 |
| INC_sq_count_orb10       | r_cc_pct        |  26 |  0.0943672  |     0.151394   |           -0.283541  |            0.508839  |  0.0307332  |   0.185976  |   0.0943672  |                0.6436 | iid_shuffle_returns |     4999 |
| INC_sq_count_orb10       | r_gap_pct       |  26 |  0.0923984  |     0.0876676  |           -0.260064  |            0.444281  |  0.0033169  |   0.171775  |   0.0923984  |                0.6552 | iid_shuffle_returns |     4999 |
| INC_sq_count_orb10       | r_intra_pct     |  26 |  0.0469672  |     0.0478827  |           -0.343466  |            0.448445  | -0.0300998  |   0.158958  |   0.0469672  |                0.8202 | iid_shuffle_returns |     4999 |
| INC_sq_count_orb10       | abs_r_gap_pct   |  26 | -0.0402547  |     0.0154915  |           -0.417749  |            0.404549  | -0.159232   |   0.0911693 |  -0.0402547  |                0.8488 | iid_shuffle_returns |     4999 |
| INC_sq_count_orb10       | abs_r_intra_pct |  26 |  0.170064   |     0.157731   |           -0.1789    |            0.482694  |  0.100725   |   0.240776  |   0.170064   |                0.4042 | iid_shuffle_returns |     4999 |

## Timing subgroups (unstable if n small)

| timing       |   n | note   |   DK_sq_orb10_vs_cc |   DK_sq_orb10_vs_gap |   DK_sq_orb10_vs_intra |
|:-------------|----:|:-------|--------------------:|---------------------:|-----------------------:|
| AfterMarket  |  12 |        |          -0.0938679 |            0.0176624 |              -0.182333 |
| BeforeMarket |  14 |        |          -0.821076  |           -0.725316  |              -0.43787  |