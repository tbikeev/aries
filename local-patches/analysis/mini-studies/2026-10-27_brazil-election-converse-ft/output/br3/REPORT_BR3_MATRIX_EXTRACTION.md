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
- Total eligible observations: 420 / 1000
- Eligible tickers per event — min/median/max: 1/3/10

### Per ticker (NEG+POS eligible count)
- ABEV: 29 total (14 NEG, 15 POS)
- BBD: 92 total (44 NEG, 48 POS)
- ERJ: 2 total (1 NEG, 1 POS)
- ITUB: 94 total (46 NEG, 48 POS)
- NU: 5 total (3 NEG, 2 POS)
- PAGS: 22 total (12 NEG, 10 POS)
- PBR: 100 total (50 NEG, 50 POS)
- STNE: 21 total (12 NEG, 9 POS)
- VALE: 34 total (17 NEG, 17 POS)
- XP: 21 total (12 NEG, 9 POS)

## Active aspects
- Mean active C2C cells per eligible obs: 17.3
- Power mean (active): 4.4276
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
