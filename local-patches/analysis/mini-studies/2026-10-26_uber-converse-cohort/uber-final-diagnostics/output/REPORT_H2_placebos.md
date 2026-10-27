# Report H2 — Genuine cohort vs placebos (exploratory)

## Shifted radix (Design A)

| design        |   offset_days | direction   |      DK_sq_r |    FT_sq_r |   INC_sq_r |     tight_r | converse_shift_note                                   |
|:--------------|--------------:|:------------|-------------:|-----------:|-----------:|------------:|:------------------------------------------------------|
| genuine       |             0 | real        | -0.518983    |  0.178634  |  0.0943672 | -0.384655   | nan                                                   |
| shifted_radix |           -30 | -1          |  0.0554013   | -0.0151315 |  0.120669  |  0.125928   | converse JD moves +-60 days vs genuine at same event  |
| shifted_radix |            30 | +1          | -0.000913363 | -0.0788623 |  0.0783274 | -0.158963   | converse JD moves +60 days vs genuine at same event   |
| shifted_radix |           -90 | -1          |  0.254195    |  0.174597  |  0.164883  |  0.17816    | converse JD moves +-180 days vs genuine at same event |
| shifted_radix |            90 | +1          | -0.21697     |  0.119256  | -0.319896  |  0.0541629  | converse JD moves +180 days vs genuine at same event  |
| shifted_radix |          -180 | -1          | -0.117815    | -0.264473  |  0.0152009 | -0.252233   | converse JD moves +-360 days vs genuine at same event |
| shifted_radix |           180 | +1          | -0.300138    |  0.0597768 |  0.0187008 | -0.00286294 | converse JD moves +360 days vs genuine at same event  |
| shifted_radix |          -365 | -1          |  0.0785599   | -0.462474  |  0.214587  |  0.198773   | converse JD moves +-730 days vs genuine at same event |
| shifted_radix |           365 | +1          |  0.0704469   |  0.267227  |  0.0696591 |  0.191203   | converse JD moves +730 days vs genuine at same event  |

## Random surrogate rank (Design B)

```json
{
  "independent_random_radix_DK_sq": {
    "observed_r": -0.5189825030597046,
    "null_median": 0.012326355313079806,
    "null_p05": -0.3064601006503251,
    "null_p95": 0.3462492291348701,
    "empirical_p_two_sided": 0.003,
    "rank_percentile": 0.001
  },
  "independent_random_radix_tight": {
    "observed_r": -0.38465460595485124,
    "null_median": 0.00812548702130226,
    "null_p05": -0.31851742493590873,
    "null_p95": 0.35866780671930326,
    "empirical_p_two_sided": 0.053,
    "rank_percentile": 0.017
  },
  "joint_shift_DK_sq": {
    "observed_r": -0.5189825030597046,
    "null_median": -0.01275270043622818,
    "null_p05": -0.31098605151532904,
    "null_p95": 0.3493757629716276,
    "empirical_p_two_sided": 0.011,
    "rank_percentile": 0.003
  },
  "joint_shift_tight": {
    "observed_r": -0.38465460595485124,
    "null_median": 0.007435082472134719,
    "null_p05": -0.3284368662859728,
    "null_p95": 0.3419676517690178,
    "empirical_p_two_sided": 0.065,
    "rank_percentile": 0.028
  },
  "n_surrogates": 1000,
  "seed": 20261027
}
```

## Event alignment (Design C)

```json
{
  "circular_return_shift": {
    "observed_r": -0.5189825030597048,
    "null_median": 0.025023265168774712,
    "empirical_p_two_sided": 0.0,
    "null": "circular_shift_returns"
  },
  "misaligned_event_jd_90d": 0.04879077126572673
}
```