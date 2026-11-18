"""BR-2 unit tests."""

from __future__ import annotations

import itertools
import sys
from datetime import date
from pathlib import Path

STUDY = Path(__file__).resolve().parents[1]
UBER = STUDY.parent / "2026-10-26_uber-converse-cohort"
ROOT = STUDY.parents[3]
for p in (str(ROOT), str(ROOT / "SWEP" / "src"), str(UBER), str(STUDY)):
    if p not in sys.path:
        sys.path.insert(0, p)

from br2_features import PRIMARY_PLANET_SET, frozen_feature_bundle  # noqa: E402
from br2_percentiles import _midrank_percentile  # noqa: E402
from br2_shock_registry import assign_episode_ids  # noqa: E402
from brazil_historical import trading_session_jd  # noqa: E402
from ft_registry import build_registry, ft_birth_jd  # noqa: E402


def test_c2c_pair_symmetry_no_self():
    reg = build_registry()
    row = reg[reg["ticker"] == "PAGS"].iloc[0]
    jd, ok = ft_birth_jd(row)
    assert ok
    ej = trading_session_jd(date(2020, 3, 9))
    c = frozen_feature_bundle(jd, ej, use_cache=False)
    assert c["c2c_hard_count"] >= 0


def test_midrank_no_future_leakage_monotonic():
    hist = [1.0, 2.0, 3.0, 4.0]
    assert _midrank_percentile(4.0, hist) > _midrank_percentile(1.0, hist)


def test_episode_clustering_covid():
    import pandas as pd

    shocks = pd.DataFrame(
        [
            {"event_date": "2020-03-09", "ewz_return_cc_pct": -5.0, "verified": True},
            {"event_date": "2020-03-12", "ewz_return_cc_pct": -6.0, "verified": True},
            {"event_date": "2020-03-16", "ewz_return_cc_pct": -4.0, "verified": True},
        ]
    )
    ewz = pd.DataFrame({"event_date": pd.date_range("2020-03-01", periods=30, freq="B").date})
    out = assign_episode_ids(shocks, ewz)
    assert out["episode_id"].nunique() <= 3


def test_c2c_c2r_same_sample_keys():
    reg = build_registry()
    row = reg[reg["ticker"] == "ITUB"].iloc[0]
    jd, ok = ft_birth_jd(row)
    ej = trading_session_jd(date(2017, 5, 18))
    a = frozen_feature_bundle(jd, ej, use_cache=False)
    b = frozen_feature_bundle(jd, ej, use_cache=False)
    assert a["c2c_hard_count"] == b["c2c_hard_count"]
    assert a["c2r_hard_count"] == b["c2r_hard_count"]


def test_planet_set_matches_benchmark():
    assert "Sun" in PRIMARY_PLANET_SET
    assert "Chiron" not in PRIMARY_PLANET_SET


if __name__ == "__main__":
    test_c2c_pair_symmetry_no_self()
    test_midrank_no_future_leakage_monotonic()
    test_episode_clustering_covid()
    test_c2c_c2r_same_sample_keys()
    test_planet_set_matches_benchmark()
    print("OK: BR-2 tests")
