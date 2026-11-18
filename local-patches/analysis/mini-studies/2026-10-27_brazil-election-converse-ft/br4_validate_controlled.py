"""Validate BR-3.5 controlled matrix extraction."""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

from br3_validate import run_validation
from br3_schema import SPOT_CHECKS, BR3_TICKERS, PLANETS, c2c_pair_index
from br4_constants import CONTROLLED_DIR


def _file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def validate_controlled_extraction(*, sensitivity_dir: Path) -> dict:
    manifest = pd.read_parquet(CONTROLLED_DIR / "event_manifest.parquet")
    counts = manifest["label"].value_counts()
    errors = []
    if int(counts.get("NEG", 0)) != 50 or int(counts.get("POS", 0)) != 50:
        errors.append(f"Expected 50 NEG and 50 POS, got {counts.to_dict()}")
    if "n_eligible_tickers_at_session" in manifest.columns:
        if int(manifest["n_eligible_tickers_at_session"].min()) < 7:
            errors.append("Some events have fewer than 7 eligible tickers at session level")
    elig = pd.read_csv(CONTROLLED_DIR / "eligibility_matrix.csv")
    per_event = elig.groupby("session")["eligible"].sum()
    if per_event.min() < 7:
        errors.append(f"Eligibility matrix min eligible per event: {int(per_event.min())}")

    z = np.load(CONTROLLED_DIR / "individual_aspect_matrices.npz")
    manifest_list = manifest.sort_values("event_id").to_dict("records")
    agg = np.load(CONTROLLED_DIR / "aggregate_aspect_matrices.npz")

    checks = run_validation(
        manifest=manifest_list,
        eligible=z["eligible"],
        c2c_active=z["c2c_active"],
        c2c_power=z["c2c_power"],
        c2c_n=agg["c2c_n"],
        c2c_sum=agg["c2c_sum_power"],
        c2c_N=agg["c2c_N"],
        c2r_active=z["c2r_active"],
        c2r_power=z["c2r_power"],
        c2r_n=agg["c2r_n"],
        c2r_sum=agg["c2r_sum_power"],
        c2r_N=agg["c2r_N"],
        pool_c2c_n=np.load(CONTROLLED_DIR / "pooled_aspect_matrices.npz")["c2c_n"],
        pool_c2c_sum=np.load(CONTROLLED_DIR / "pooled_aspect_matrices.npz")["c2c_sum_power"],
        ticker_c2c_n=agg["c2c_n"],
        ticker_c2c_sum=agg["c2c_sum_power"],
    )
    errors.extend(checks["errors"])

    sensitivity_hashes = {}
    if sensitivity_dir.is_dir():
        for name in ("individual_aspect_matrices.npz", "event_manifest.parquet"):
            p = sensitivity_dir / name
            if p.is_file():
                sensitivity_hashes[name] = _file_hash(p)

    return {
        "all_passed": len(errors) == 0 and checks["all_passed"],
        "errors": errors,
        "br3_validation": checks,
        "sensitivity_unchanged_hashes": sensitivity_hashes,
        "eligible_observations": int(z["eligible"].sum()),
    }
