"""BR-3 validation checks and QA report."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from br3_schema import BR3_TICKERS, LABELS, OUTPUT_BR3, PLANETS, SPOT_CHECKS, c2c_pair_index


def run_validation(
    *,
    manifest: list[dict],
    eligible: np.ndarray,
    c2c_active: np.ndarray,
    c2c_power: np.ndarray,
    c2c_n: np.ndarray,
    c2c_sum: np.ndarray,
    c2c_N: np.ndarray,
    c2r_active: np.ndarray,
    c2r_power: np.ndarray,
    c2r_n: np.ndarray,
    c2r_sum: np.ndarray,
    c2r_N: np.ndarray,
    pool_c2c_n: np.ndarray,
    pool_c2c_sum: np.ndarray,
    ticker_c2c_n: np.ndarray,
    ticker_c2c_sum: np.ndarray,
) -> dict:
    errors: list[str] = []
    n_e = len(manifest)
    label_events = {lab: [i for i, ev in enumerate(manifest) if ev["label"] == lab] for lab in LABELS}

    # A. shapes
    if c2c_active.shape != (len(BR3_TICKERS), n_e, 55, 5):
        errors.append(f"c2c_active bad shape {c2c_active.shape}")

    # B. inactive power zero
    if np.any(c2c_power[~c2c_active] != 0):
        errors.append("c2c inactive cells with nonzero power")
    if np.any(c2r_power[~c2r_active] != 0):
        errors.append("c2r inactive cells with nonzero power")

    # C. aggregation identity per ticker/label
    for li, lab in enumerate(LABELS):
        eix = label_events[lab]
        for ti, ticker in enumerate(BR3_TICKERS):
            elig_e = [ei for ei in eix if eligible[ti, ei]]
            if not elig_e:
                continue
            ind_n = c2c_active[ti, elig_e].sum(axis=0).astype(np.int32)
            ind_s = c2c_power[ti, elig_e].sum(axis=0)
            if not np.array_equal(ind_n, c2c_n[li, ti]):
                errors.append(f"c2c_n mismatch {ticker} {lab}")
            if not np.allclose(ind_s, c2c_sum[li, ti], rtol=0, atol=1e-6):
                errors.append(f"c2c_sum mismatch {ticker} {lab}")

    # D. pooled equals sum of ticker sums
    ticker_pool_n = ticker_c2c_n.sum(axis=1)
    ticker_pool_s = ticker_c2c_sum.sum(axis=1)
    if not np.array_equal(ticker_pool_n, pool_c2c_n):
        errors.append("pooled c2c_n != sum ticker c2c_n")
    if not np.allclose(ticker_pool_s, pool_c2c_sum, rtol=0, atol=1e-4):
        errors.append("pooled c2c_sum != sum ticker c2c_sum")

    # E. active powers finite nonnegative
    if np.any(c2c_power[c2c_active] < 0):
        errors.append("negative c2c power")
    if np.any(~np.isfinite(c2c_power[c2c_active])):
        errors.append("non-finite c2c power")

    # F. spot checks
    sess_index = {ev["session"]: ei for ei, ev in enumerate(manifest)}
    ti_map = {t: i for i, t in enumerate(BR3_TICKERS)}
    for sc in SPOT_CHECKS:
        ei = sess_index.get(sc["session"])
        ti = ti_map.get(sc["ticker"])
        if ei is None or ti is None:
            errors.append(f"spot check missing index {sc['ticker']} {sc['session']}")
            continue
        if sc["mode"] == "c2c":
            pk = c2c_pair_index(sc["planet_a"], sc["planet_b"])
            ak = ["con", "opp", "squ", "tri", "sex"].index(sc["aspect"])
            p = float(c2c_power[ti, ei, pk, ak])
            if not c2c_active[ti, ei, pk, ak]:
                errors.append(f"spot inactive {sc}")
            elif abs(p - sc["power"]) > sc["tolerance"]:
                errors.append(f"spot power {sc['ticker']} {sc['session']} got {p} want {sc['power']}")
        else:
            ci = PLANETS.index(sc["converse"])
            ri = PLANETS.index(sc["radix"])
            ak = ["con", "opp", "squ", "tri", "sex"].index(sc["aspect"])
            p = float(c2r_power[ti, ei, ci, ri, ak])
            if not c2r_active[ti, ei, ci, ri, ak]:
                errors.append(f"spot inactive {sc}")
            elif abs(p - sc["power"]) > sc["tolerance"]:
                errors.append(f"spot power {sc['ticker']} {sc['session']} got {p} want {sc['power']}")

    return {"all_passed": len(errors) == 0, "errors": errors}


def write_report(
    *,
    manifest: list[dict],
    eligible: np.ndarray,
    elig_detail: list[list[dict]],
    c2c_active: np.ndarray,
    c2c_power: np.ndarray,
    checks: dict,
    extremes: int,
) -> Path:
    path = OUTPUT_BR3 / "REPORT_BR3_MATRIX_EXTRACTION.md"
    n_e = len(manifest)
    per_event_elig = eligible.sum(axis=0)
    per_ticker_elig = eligible.sum(axis=1)
    active_counts = c2c_active.sum(axis=(2, 3))
    lines = [
        "# BR-3 matrix extraction report",
        "",
        "## Dimensions",
        f"- Tickers: {len(BR3_TICKERS)}",
        f"- Events: {n_e} ({extremes} NEG + {extremes} POS)",
        f"- C2C tensor: {eligible.shape[0]}×{n_e}×55×5",
        f"- C2R tensor: {eligible.shape[0]}×{n_e}×11×11×5",
        "",
        "## Event selection",
        f"- Source: `ewz_return_extremes.csv` adjusted returns",
        f"- Discovery flag on 2026-10-26",
        "",
        "## Eligibility",
        f"- Total eligible observations: {int(eligible.sum())} / {eligible.size}",
        f"- Eligible tickers per event — min/median/max: "
        f"{int(per_event_elig.min())}/{float(np.median(per_event_elig)):.0f}/{int(per_event_elig.max())}",
        "",
        "### Per ticker (NEG+POS eligible count)",
    ]
    for ti, t in enumerate(BR3_TICKERS):
        neg = sum(1 for ei, ev in enumerate(manifest) if ev["label"] == "NEG" and eligible[ti, ei])
        pos = sum(1 for ei, ev in enumerate(manifest) if ev["label"] == "POS" and eligible[ti, ei])
        lines.append(f"- {t}: {int(per_ticker_elig[ti])} total ({neg} NEG, {pos} POS)")
    lines.extend(
        [
            "",
            "## Active aspects",
            f"- Mean active C2C cells per eligible obs: {active_counts[eligible].mean():.1f}",
            f"- Power mean (active): {c2c_power[c2c_active].mean():.4f}",
            f"- Power max (active): {c2c_power[c2c_active].max():.4f}",
            "",
            "## Validation",
            f"- All checks passed: **{checks['all_passed']}**",
        ]
    )
    if checks["errors"]:
        lines.append("- Errors:")
        for e in checks["errors"][:20]:
            lines.append(f"  - {e}")
    lines.extend(
        [
            "",
            "## Example load (NumPy)",
            "```python",
            "import numpy as np",
            "z = np.load('individual_aspect_matrices.npz')",
            "ti = list(" + repr(list(BR3_TICKERS)) + ").index('PAGS')",
            "ei = 1  # set from event_manifest session index",
            "pk = 44  # Mars–Pluto pair index — see matrix_metadata.json",
            "squ = 2",
            "z['c2c_power'][ti, ei, pk, squ]",
            "```",
            "",
            "## Files",
            "- `individual_aspect_matrices.npz`",
            "- `aggregate_aspect_matrices.npz`",
            "- `pooled_aspect_matrices.npz`",
            "- `matrix_metadata.json`",
            "- Parquet: `c2c_event_cells.parquet`, `c2r_event_cells.parquet`, aggregates, pooled",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
