"""Frozen CEO converse-square features (same rules as UBER DK)."""

from __future__ import annotations

import pandas as pd

from aspects import full_directed_aspect_matrix
from converse import jd_to_utc_tuple, mirrored_jd
from cross_company_paths import FROZEN_SQ_ORB_DEG, FROZEN_SQ_ORB_HALF_DEG
from earnings_converse import converse_count_features_for_birth_jd
from ephemeris import iter_benchmark_names, positions_at_jd
from executive_radices import ExecutiveRadix
from market_reactions import EarningsReaction, report_date_key


def extract_event_features(
    *,
    birth_jd: float,
    event_jd: float,
    ticker: str,
    universe_row: pd.Series,
    radix: ExecutiveRadix,
    reaction: EarningsReaction,
) -> tuple[dict, pd.DataFrame]:
    counts_half = converse_count_features_for_birth_jd(
        birth_jd, event_jd, orb_max=FROZEN_SQ_ORB_HALF_DEG
    )
    counts_one = converse_count_features_for_birth_jd(
        birth_jd, event_jd, orb_max=FROZEN_SQ_ORB_DEG
    )
    cjd = mirrored_jd(birth_jd, event_jd)
    conv = positions_at_jd(cjd, include_optional=False)
    rad = positions_at_jd(birth_jd, include_optional=False)
    conv_lon = {k: p.longitude_deg for k, p in conv.items()}
    rad_lon = {k: p.longitude_deg for k, p in rad.items()}
    bodies = list(iter_benchmark_names())
    matrix = full_directed_aspect_matrix(conv_lon, rad_lon, body_names=bodies)
    asp_rows = []
    for row in matrix:
        if row["best_orb"] > FROZEN_SQ_ORB_DEG + 1e-12:
            continue
        asp_rows.append(
            {
                "ticker": ticker.upper(),
                "report_date": report_date_key(reaction.report_date),
                "reaction_date": report_date_key(reaction.reaction_session),
                "converse_utc": jd_to_utc_tuple(cjd),
                "from_body": row["from_body"],
                "to_body": row["to_body"],
                "best_aspect": row["best_aspect"],
                "best_orb": row["best_orb"],
            }
        )

    vol = None
    if reaction.r_cc_pct is not None and reaction.prev_session is not None:
        # filled later in pipeline when ohlc available
        pass

    row = {
        "ticker": ticker.upper(),
        "sector_bucket": str(universe_row.get("bucket", "")),
        "executive": radix.executive,
        "report_date": report_date_key(reaction.report_date),
        "reaction_date": report_date_key(reaction.reaction_session),
        "event_jd_ut": event_jd,
        "converse_jd_ut": cjd,
        "converse_utc": str(jd_to_utc_tuple(cjd)),
        "square_count_1deg": counts_one["sq_count"],
        "square_count_0p5deg": counts_half["sq_count"],
        "tight_count_1deg": counts_one["tight_aspect_count"],
        "return_cc": reaction.r_cc_pct,
        "return_gap": reaction.r_gap_pct,
        "return_intraday": reaction.r_intra_pct,
        "abs_return_cc": reaction.abs_r_cc_pct,
        "return_2d": reaction.r_2d_pct,
        "return_5d": reaction.r_5d_pct,
        "dob_quality": radix.dob_quality,
        "event_quality": "ambiguous_timing" if reaction.mapping_uncertain else "ok",
        "timing": reaction.timing,
        "birth_time_convention": radix.time_convention,
        "eps_surprise_pct": reaction.eps_surprise_pct,
    }
    return row, pd.DataFrame(asp_rows)
