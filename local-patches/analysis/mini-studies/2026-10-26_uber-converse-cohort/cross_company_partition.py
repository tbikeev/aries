"""Deterministic company-level train/dev/holdout partitions."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from cross_company_paths import DISCOVERY_TICKER, PARTITION_SEED

# Per bucket: 2 pilot + 5 development + 3 holdout = 10 companies.
SLICES = {"pilot": (0, 2), "development": (2, 7), "holdout": (7, 10)}


def build_partition_manifest(
    universe: pd.DataFrame,
    *,
    exclude_ticker: str = DISCOVERY_TICKER,
    seed: int = PARTITION_SEED,
) -> pd.DataFrame:
    """Assign stages before any target-linked performance review."""
    _ = seed  # reserved for future stratified shuffle; order is sorted-by-ticker within bucket
    rows: list[dict] = []
    sub = universe[universe["ticker"] != exclude_ticker.upper()].copy()
    for bucket, grp in sub.groupby("bucket", sort=True):
        tickers = sorted(grp["ticker"].tolist())
        if len(tickers) != 10:
            rows.append(
                {
                    "bucket": bucket,
                    "warning": f"expected 10 tickers ex-{exclude_ticker}, got {len(tickers)}",
                }
            )
        for stage, (a, b) in SLICES.items():
            for t in tickers[a:b]:
                rows.append({"ticker": t, "bucket": bucket, "stage": stage})
    return pd.DataFrame([r for r in rows if "ticker" in r])


def save_manifest(manifest: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    manifest.to_csv(path, index=False)
    meta = {
        "partition_rule": "sorted ticker within bucket; slices pilot[0:2] dev[2:7] holdout[7:10]",
        "exclude_discovery_ticker": DISCOVERY_TICKER,
        "seed": PARTITION_SEED,
    }
    path.with_suffix(".json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
