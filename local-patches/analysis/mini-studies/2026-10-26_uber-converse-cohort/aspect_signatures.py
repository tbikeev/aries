"""Shared directed-aspect signature strings."""

from __future__ import annotations

import pandas as pd


def aspect_signature(row: pd.Series) -> str:
    # from_body / to_body already carry conv:/radix: prefixes from aspects.py
    return f"{row['radix_key']}|{row['from_body']}|{row['to_body']}|{row['best_aspect']}"


def plain_converse_body(from_body: str) -> str:
    return from_body.removeprefix("conv:")


def add_signature_column(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["signature"] = out.apply(aspect_signature, axis=1)
    return out
