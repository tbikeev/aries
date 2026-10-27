"""Cross-company v2 (CEO/FT/INC) tests."""

from __future__ import annotations

from pathlib import Path

from corporate_radices import build_ft_radix, build_inc_radix
from cross_company_paths import DEFAULT_UNIVERSE_V2_CSV
from munkasey_import import extract_corporate_fields


def test_munkasey_uber_ft_date_and_time():
    u = extract_corporate_fields("UBER")
    assert u["munkasey_found"]
    assert u["ft_date"] == "2019-05-10"
    assert u["ft_time_hhmm"] == "11:50"


def test_ft_radix_from_row():
    u = extract_corporate_fields("MSFT")
    row = {"ticker": "MSFT", **u}
    ft = build_ft_radix(row)
    assert ft is not None
    assert ft.birth_time_uncertain is False or ft.time_convention.startswith("first_trade")


def test_universe_v2_exists():
    assert DEFAULT_UNIVERSE_V2_CSV.exists(), "run build_universe_v2 first"


def test_v2_has_ft_inc_columns():
    import pandas as pd

    df = pd.read_csv(DEFAULT_UNIVERSE_V2_CSV)
    assert "ft_date" in df.columns
    assert "inc_date" in df.columns
    assert df["munkasey_found"].sum() >= 35
