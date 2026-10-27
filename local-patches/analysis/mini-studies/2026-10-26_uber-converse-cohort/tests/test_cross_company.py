"""Cross-company study unit tests."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from company_universe import load_universe_csv
from cross_company_partition import build_partition_manifest
from cross_company_paths import CROSS_INPUT, DISCOVERY_TICKER, PRIMARY_FEATURE
from declination_geometry import classify_declination_pair
from executive_radices import birth_jd_for_dob, build_executive_radix
from cross_company_data import resolve_ticker_csv


def test_dob_parsing_and_noon_convention():
    r = build_executive_radix(
        ticker="MSFT",
        executive="Satya Nadella",
        dob_str="1967-08-19",
        verification_status="Strong",
    )
    assert r.dob == date(1967, 8, 19)
    assert r.birth_jd > 0
    assert r.time_convention in ("noon_local_birthplace", "noon_utc_fallback")


def test_universe_load_and_uber_exclusion():
    path = CROSS_INPUT / "universe_cohort_all.csv"
    assert path.exists(), "copy universe_cohort_all.csv into cross-company-study/input"
    df = load_universe_csv(path)
    assert len(df) >= 40
    manifest = build_partition_manifest(df, exclude_ticker=DISCOVERY_TICKER)
    assert DISCOVERY_TICKER not in manifest["ticker"].values
    assert manifest["stage"].isin(["pilot", "development", "holdout"]).all()
    assert len(manifest) == 40


def test_partition_deterministic():
    path = CROSS_INPUT / "universe_cohort_all.csv"
    df = load_universe_csv(path)
    m1 = build_partition_manifest(df)
    m2 = build_partition_manifest(df)
    assert m1.equals(m2)


def test_msft_data_files_exist():
    assert resolve_ticker_csv("MSFT", kind="earnings") is not None
    assert resolve_ticker_csv("MSFT", kind="ohlc") is not None


def test_declination_equator_exclusive():
    kinds = classify_declination_pair(0.005, 0.01)
    assert len(kinds) <= 1


def test_frozen_primary_feature_name():
    assert PRIMARY_FEATURE == "square_count_1deg"
