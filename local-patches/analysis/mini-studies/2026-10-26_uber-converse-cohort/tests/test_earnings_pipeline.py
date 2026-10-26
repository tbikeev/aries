"""Earnings pipeline acceptance tests."""

from __future__ import annotations

import os
import sys
from datetime import date
from pathlib import Path

STUDY = Path(__file__).resolve().parents[1]
ROOT = STUDY.parents[3]
sys.path[:0] = [str(STUDY), str(ROOT), str(ROOT / "SWEP" / "src")]

from earnings_loader import load_earnings_csv  # noqa: E402
from earnings_paths import resolve_earnings_csv, resolve_ohlc_csv  # noqa: E402
from extreme_events import top_extremes  # noqa: E402
from market_reactions import (  # noqa: E402
    build_reactions,
    is_trading_session,
    load_ohlc_csv,
    map_reaction_session,
    next_session_strictly_after,
    reactions_to_dataframe,
)
from earnings_converse import event_jd_from_datetime, converse_utc_for_event  # noqa: E402
from datetime import datetime, timezone


def test_earnings_csv_loads() -> None:
    rows = load_earnings_csv(resolve_earnings_csv())
    assert len(rows) >= 20
    assert rows[0].report_date < rows[-1].report_date


def test_ohlc_sorted() -> None:
    df = load_ohlc_csv(resolve_ohlc_csv())
    assert df["session"].is_monotonic_increasing


def test_aftermarket_maps_to_next_session() -> None:
    # 2019-05-30 AfterMarket -> 2019-05-31? Actually May 30 2019 was Thursday - after close -> Friday May 31
    sess, _, _ = map_reaction_session(date(2019, 5, 30), "AfterMarket")
    assert sess == date(2019, 5, 31)


def test_beforemarket_same_session() -> None:
    sess, _, _ = map_reaction_session(date(2022, 5, 4), "BeforeMarket")
    assert sess == date(2022, 5, 4)


def test_pre_ipo_excluded() -> None:
    from earnings_loader import load_earnings_csv

    earnings = load_earnings_csv(resolve_earnings_csv())
    ohlc = load_ohlc_csv(resolve_ohlc_csv())
    reactions = build_reactions(earnings, ohlc)
    feb = next(r for r in reactions if r.report_date == date(2019, 2, 15))
    assert feb.excluded
    assert "before first OHLC" in feb.exclusion_reason


def test_return_cc_known_row() -> None:
    earnings = load_earnings_csv(resolve_earnings_csv())
    ohlc = load_ohlc_csv(resolve_ohlc_csv())
    reactions = build_reactions(earnings, ohlc)
    valid = [r for r in reactions if r.report_date == date(2019, 5, 30) and not r.excluded]
    assert len(valid) == 1
    # Reaction session 2019-05-31: prev close 2019-05-30
    assert valid[0].reaction_session == date(2019, 5, 31)
    assert valid[0].r_cc_pct is not None


def test_top10_deterministic() -> None:
    earnings = load_earnings_csv(resolve_earnings_csv())
    ohlc = load_ohlc_csv(resolve_ohlc_csv())
    reactions = build_reactions(earnings, ohlc)
    n1, p1, _ = top_extremes(reactions)
    n2, p2, _ = top_extremes(reactions)
    assert n1["report_date"].tolist() == n2["report_date"].tolist()
    assert p1["report_date"].tolist() == p2["report_date"].tolist()


def test_converse_timestamp_ft_shape() -> None:
    dt = datetime(2026, 2, 4, 14, 30, tzinfo=timezone.utc)
    jd = event_jd_from_datetime(dt)
    utc = converse_utc_for_event("FT", jd)
    assert utc[0] == 2012


def test_consecutive_earnings_runs() -> None:
    from temporal_persistence import consecutive_earnings_runs

    chron = ["2020-01-01", "2020-04-01", "2020-07-01", "2020-10-01", "2021-01-01"]
    runs = consecutive_earnings_runs(chron, {"2020-04-01", "2020-07-01", "2021-01-01"})
    assert len(runs) == 2
    assert runs[0][2] == 2
    assert runs[1][2] == 1


def test_permutation_reproducible() -> None:
    from robustness_checks import merge_features_outcomes, permutation_correlation_test
    from feature_reduction import build_event_feature_matrix

    earnings = load_earnings_csv(resolve_earnings_csv())
    ohlc = load_ohlc_csv(resolve_ohlc_csv())
    reactions = build_reactions(earnings, ohlc)
    react_df = reactions_to_dataframe(reactions)
    # minimal aspects not needed — use feature matrix from empty skip
    from earnings_converse import extract_converse_features, event_jd_from_datetime
    import pandas as pd

    parts = []
    for r in reactions:
        if r.excluded or r.event_datetime_utc is None:
            continue
        ejd = event_jd_from_datetime(r.event_datetime_utc)
        for cohort in ("FT", "INC", "DK"):
            block = extract_converse_features(
                cohort,
                ejd,
                report_date=str(r.report_date),
                reaction_session=str(r.reaction_session),
            )
            parts.append(pd.DataFrame(block["aspect_rows"]))
    aspects_df = pd.concat(parts, ignore_index=True)
    feat = build_event_feature_matrix(aspects_df)
    merged = merge_features_outcomes(feat, react_df[~react_df["excluded"]])
    a = permutation_correlation_test(merged, "DK_sq_count", n_perm=100, seed=7)
    b = permutation_correlation_test(merged, "DK_sq_count", n_perm=100, seed=7)
    assert a["permutation_p_two_sided"] == b["permutation_p_two_sided"]


def test_feature_reduction_merges_report_dates() -> None:
    from feature_reduction import build_event_feature_matrix, rank_feature_groups
    from earnings_converse import extract_converse_features, event_jd_from_datetime

    earnings = load_earnings_csv(resolve_earnings_csv())
    ohlc = load_ohlc_csv(resolve_ohlc_csv())
    reactions = build_reactions(earnings, ohlc)
    react_df = reactions_to_dataframe(reactions)
    parts = []
    for r in reactions:
        if r.excluded or r.event_datetime_utc is None:
            continue
        ejd = event_jd_from_datetime(r.event_datetime_utc)
        for cohort in ("FT", "INC", "DK"):
            block = extract_converse_features(
                cohort,
                ejd,
                report_date=str(r.report_date),
                reaction_session=str(r.reaction_session),
            )
            parts.append(__import__("pandas").DataFrame(block["aspect_rows"]))
    aspects_df = __import__("pandas").concat(parts, ignore_index=True)
    feat_df = build_event_feature_matrix(aspects_df)
    rank_df = rank_feature_groups(feat_df, react_df[~react_df["excluded"]])
    assert len(rank_df) > 0
    assert rank_df["corr_with_r_cc"].notna().any()
