"""Shared cross-cohort declination network activation (Phase I-D)."""

from __future__ import annotations

import pandas as pd

from cohort import EXPECTED_DECLINATION, build_cohort_registry
from phase_i_paths import DECL_ORB_PRIMARY

ABS_DECL_BAND = (21.0, 22.0)


def natal_registry_table() -> pd.DataFrame:
    rows = []
    for left, a, right, b, kind, max_delta in EXPECTED_DECLINATION:
        rows.append(
            {
                "left_cohort": left,
                "left_body": a,
                "right_cohort": right,
                "right_body": b,
                "natal_kind": kind,
                "natal_max_delta_deg": max_delta,
            }
        )
    return pd.DataFrame(rows)


def verify_inc_mercury_dk_neptune() -> dict:
    """Swiss declination at stated radix times (transcription check)."""
    from ephemeris import positions_at_jd
    from radix import RADIX_COHORT

    inc = positions_at_jd(RADIX_COHORT["INC"].birth_jd)
    dk = positions_at_jd(RADIX_COHORT["DK"].birth_jd)
    m_inc = inc["Mercury"].declination_deg
    n_dk = dk["Neptune"].declination_deg
    return {
        "INC_Mercury_decl_deg": m_inc,
        "DK_Neptune_decl_deg": n_dk,
        "par_delta_deg": abs(m_inc - n_dk),
        "cpar_delta_deg": abs(m_inc + n_dk),
        "manual_transcription_par_0.32_unverified": True,
        "note": "Different charts; inter-radix declination uses cross-chart comparison in cohort registry.",
    }


def network_activation(
    decl_df: pd.DataFrame,
    report_dates: list[str],
    *,
    orb_max: float = DECL_ORB_PRIMARY,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    For each registry link, test endpoint activation at each cohort's converse row set.
    Endpoint = converse→radix contact where radix_body matches registered body in that cohort.
    """
    reg = natal_registry_table()
    event_rows = []
    detail_rows = []
    tight = decl_df[decl_df["decl_orb_deg"] <= orb_max + 1e-12]

    for rd in report_dates:
        networks = 0
        both = 0
        for _, link in reg.iterrows():
            lc, lb = link["left_cohort"], link["left_body"]
            rc, rb = link["right_cohort"], link["right_body"]
            left_hit = tight[
                (tight["report_date"] == rd)
                & (tight["radix_key"] == lc)
                & (tight["radix_body"] == lb)
            ]
            right_hit = tight[
                (tight["report_date"] == rd)
                & (tight["radix_key"] == rc)
                & (tight["radix_body"] == rb)
            ]
            one = len(left_hit) > 0 or len(right_hit) > 0
            two = len(left_hit) > 0 and len(right_hit) > 0
            if one:
                networks += 1
            if two:
                both += 1
            detail_rows.append(
                {
                    "report_date": rd,
                    "link": f"{lc}:{lb}-{rc}:{rb}",
                    "natal_kind": link["natal_kind"],
                    "left_endpoint_active": len(left_hit) > 0,
                    "right_endpoint_active": len(right_hit) > 0,
                    "both_endpoints": two,
                }
            )
        band_hits = tight[
            (tight["report_date"] == rd)
            & (
                tight["conv_decl_deg"].abs().between(ABS_DECL_BAND[0], ABS_DECL_BAND[1])
                | tight["radix_decl_deg"].abs().between(ABS_DECL_BAND[0], ABS_DECL_BAND[1])
            )
        ]
        event_rows.append(
            {
                "report_date": rd,
                "network_links_activated": networks,
                "network_both_endpoints": both,
                "any_both_endpoints": int(both > 0),
                "abs_decl_21_22_contact_rows": len(band_hits),
            }
        )
    return pd.DataFrame(event_rows), pd.DataFrame(detail_rows)
