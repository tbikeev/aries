"""Resolve CEO / FT / INC radix JD for one universe row."""

from __future__ import annotations

import pandas as pd

from corporate_radices import CompanyRadix, build_ft_radix, build_inc_radix
from executive_radices import build_executive_radix


def radices_for_universe_row(row: pd.Series) -> list[CompanyRadix | object]:
    out = []
    ceo = build_executive_radix(
        ticker=str(row["ticker"]),
        executive=str(row.get("executive", "")),
        dob_str=str(row["dob"]),
        verification_status=str(row.get("verification_status", "")),
    )

    class _CeoWrap:
        radix_kind = "CEO"
        ticker = ceo.ticker
        label = ceo.executive
        birth_jd = ceo.birth_jd
        time_convention = ceo.time_convention
        birth_time_uncertain = ceo.birth_time_uncertain
        quality_note = ceo.notes

    out.append(_CeoWrap())
    if "ft_date" not in row.index:
        return out
    ft = build_ft_radix(row)
    if ft:
        out.append(ft)
    inc = build_inc_radix(row)
    if inc:
        out.append(inc)
    return out
