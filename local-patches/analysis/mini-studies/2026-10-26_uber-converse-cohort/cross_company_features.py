"""Frozen converse-square features (same rules as UBER DK) for any radix JD."""

from __future__ import annotations

import pandas as pd

from aspects import full_directed_aspect_matrix
from converse import jd_to_utc_tuple, mirrored_jd
from cross_company_paths import FROZEN_SQ_ORB_DEG, FROZEN_SQ_ORB_HALF_DEG
from earnings_converse import converse_count_features_for_birth_jd
from ephemeris import iter_benchmark_names, positions_at_jd


def feature_row_for_event(
    *,
    birth_jd: float,
    event_jd: float,
    ticker: str,
    sector_bucket: str,
    radix_kind: str,
    radix_label: str,
    time_convention: str,
    quality_note: str,
    market_row: pd.Series,
    include_aspects: bool = True,
) -> tuple[dict, pd.DataFrame]:
    counts_half = converse_count_features_for_birth_jd(
        birth_jd, event_jd, orb_max=FROZEN_SQ_ORB_HALF_DEG
    )
    counts_one = converse_count_features_for_birth_jd(
        birth_jd, event_jd, orb_max=FROZEN_SQ_ORB_DEG
    )
    cjd = mirrored_jd(birth_jd, event_jd)
    asp_rows = []
    if include_aspects:
        conv = positions_at_jd(cjd, include_optional=False)
        rad = positions_at_jd(birth_jd, include_optional=False)
        conv_lon = {k: p.longitude_deg for k, p in conv.items()}
        rad_lon = {k: p.longitude_deg for k, p in rad.items()}
        matrix = full_directed_aspect_matrix(
            conv_lon, rad_lon, body_names=list(iter_benchmark_names())
        )
        for row in matrix:
            if row["best_orb"] > FROZEN_SQ_ORB_DEG + 1e-12:
                continue
            asp_rows.append(
                {
                    "ticker": ticker.upper(),
                    "radix_kind": radix_kind,
                    "report_date": market_row["report_date"],
                    "reaction_date": market_row["reaction_date"],
                    "from_body": row["from_body"],
                    "to_body": row["to_body"],
                    "best_aspect": row["best_aspect"],
                    "best_orb": row["best_orb"],
                }
            )

    out = {
        "ticker": ticker.upper(),
        "sector_bucket": sector_bucket,
        "radix_kind": radix_kind,
        "radix_label": radix_label,
        "report_date": market_row["report_date"],
        "reaction_date": market_row["reaction_date"],
        "event_jd_ut": event_jd,
        "birth_jd_ut": birth_jd,
        "converse_jd_ut": cjd,
        "converse_utc": str(jd_to_utc_tuple(cjd)),
        "square_count_1deg": counts_one["sq_count"],
        "square_count_0p5deg": counts_half["sq_count"],
        "tight_count_1deg": counts_one["tight_aspect_count"],
        "return_cc": market_row.get("return_cc"),
        "return_gap": market_row.get("return_gap"),
        "return_intraday": market_row.get("return_intraday"),
        "abs_return_cc": market_row.get("abs_return_cc"),
        "return_2d": market_row.get("return_2d"),
        "return_5d": market_row.get("return_5d"),
        "pre_event_volatility": market_row.get("pre_event_volatility"),
        "event_quality": market_row.get("event_quality"),
        "timing": market_row.get("timing"),
        "birth_time_convention": time_convention,
        "radix_quality_note": quality_note,
        "eps_surprise_pct": market_row.get("eps_surprise_pct"),
    }
    vol = out.get("pre_event_volatility")
    if vol and vol > 0 and out.get("return_cc") is not None:
        out["volatility_normalised_return"] = out["return_cc"] / vol
    return out, pd.DataFrame(asp_rows)


def extract_event_features(
    *,
    birth_jd: float,
    event_jd: float,
    ticker: str,
    universe_row: pd.Series,
    radix,
    reaction,
) -> tuple[dict, pd.DataFrame]:
    """CEO-only legacy wrapper for v1 pipeline."""
    from market_reactions import report_date_key

    market_row = pd.Series(
        {
            "report_date": report_date_key(reaction.report_date),
            "reaction_date": report_date_key(reaction.reaction_session),
            "return_cc": reaction.r_cc_pct,
            "return_gap": reaction.r_gap_pct,
            "return_intraday": reaction.r_intra_pct,
            "abs_return_cc": reaction.abs_r_cc_pct,
            "return_2d": reaction.r_2d_pct,
            "return_5d": reaction.r_5d_pct,
            "event_quality": "ambiguous_timing" if reaction.mapping_uncertain else "ok",
            "timing": reaction.timing,
            "eps_surprise_pct": reaction.eps_surprise_pct,
        }
    )
    row, asp = feature_row_for_event(
        birth_jd=birth_jd,
        event_jd=event_jd,
        ticker=ticker,
        sector_bucket=str(universe_row.get("bucket", "")),
        radix_kind="CEO",
        radix_label=getattr(radix, "executive", "CEO"),
        time_convention=getattr(radix, "time_convention", ""),
        quality_note=getattr(radix, "dob_quality", ""),
        market_row=market_row,
    )
    row["executive"] = getattr(radix, "executive", "")
    row["dob_quality"] = getattr(radix, "dob_quality", "")
    return row, asp
