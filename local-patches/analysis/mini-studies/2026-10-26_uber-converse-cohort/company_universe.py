"""Load and audit the cross-company universe CSV."""

from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd

def load_universe_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    required = {"bucket", "ticker", "company", "executive", "role", "dob", "verification_status"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"universe CSV missing columns: {sorted(missing)}")
    df["ticker"] = df["ticker"].astype(str).str.upper().str.strip()
    df["bucket"] = df["bucket"].astype(str).str.strip()
    return df


def snapshot_universe(source: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, dest)


def audit_universe_row(row: pd.Series) -> dict:
    dob = str(row.get("dob", "")).strip()
    ok_dob = len(dob) == 10 and dob[4] == "-" and dob[7] == "-"
    return {
        "ticker": row["ticker"],
        "bucket": row["bucket"],
        "executive": row.get("executive", ""),
        "dob": dob,
        "dob_parse_ok": ok_dob,
        "verification_status": row.get("verification_status", ""),
        "tenure_note": row.get("tenure_note", ""),
        "dob_source_url": row.get("dob_source_url", ""),
    }
