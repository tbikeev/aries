# BR-3 matrix extraction report

## Dimensions
- Tickers: 10
- Events: 100 (50 NEG + 50 POS)
- C2C tensor: 10×100×55×5
- C2R tensor: 10×100×11×11×5

## Event selection
- Source: `ewz_return_extremes.csv` adjusted returns
- Discovery flag on 2026-10-26

## Eligibility
- Total eligible observations: 833 / 1000
- Eligible tickers per event — min/median/max: 7/8/10

### Per ticker (NEG+POS eligible count)
- ABEV: 100 total (50 NEG, 50 POS)
- BBD: 100 total (50 NEG, 50 POS)
- ERJ: 8 total (3 NEG, 5 POS)
- ITUB: 100 total (50 NEG, 50 POS)
- NU: 32 total (17 NEG, 15 POS)
- PAGS: 100 total (50 NEG, 50 POS)
- PBR: 100 total (50 NEG, 50 POS)
- STNE: 100 total (50 NEG, 50 POS)
- VALE: 100 total (50 NEG, 50 POS)
- XP: 93 total (47 NEG, 46 POS)

## Active aspects
- Mean active C2C cells per eligible obs: 17.0
- Power mean (active): 4.4066
- Power max (active): 19.9744

## Validation
- All checks passed: **True**

## Example load (NumPy)
```python
import numpy as np
z = np.load('individual_aspect_matrices.npz')
ti = list(['ABEV', 'BBD', 'ERJ', 'ITUB', 'NU', 'PAGS', 'PBR', 'STNE', 'VALE', 'XP']).index('PAGS')
ei = 1  # set from event_manifest session index
pk = 44  # Mars–Pluto pair index — see matrix_metadata.json
squ = 2
z['c2c_power'][ti, ei, pk, squ]
```

## Files
- `individual_aspect_matrices.npz`
- `aggregate_aspect_matrices.npz`
- `pooled_aspect_matrices.npz`
- `matrix_metadata.json`
- Parquet: `c2c_event_cells.parquet`, `c2r_event_cells.parquet`, aggregates, pooled
