"""Converse→radix, converse→converse, and declination feature extraction."""

from __future__ import annotations

import itertools
from typing import Iterable

import pandas as pd

from brazil_paths import ORB_PRIMARY, ORB_SECONDARY, UBER_STUDY

import sys

sys.path.insert(0, str(UBER_STUDY))

from aspects import MAJOR_ASPECTS, full_directed_aspect_matrix, orb_for_named_aspect  # noqa: E402
from converse import mirrored_jd  # noqa: E402
from declination_geometry import classify_declination_pair, orb_within  # noqa: E402
from ephemeris import iter_benchmark_names, positions_at_jd  # noqa: E402

HARD = frozenset({"conj", "sq", "opp"})
SOFT = frozenset({"tri", "sext"})
OUTERS = frozenset({"Sun", "Mars", "Saturn", "Uranus", "Pluto"})


def event_jd_from_local(dt) -> float:
    from converse import utc_to_jd

    utc = dt.astimezone(__import__("datetime").timezone.utc)
    return utc_to_jd(utc.year, utc.month, utc.day, utc.hour, utc.minute, utc.second)


def positions_at_event(ft_jd: float, event_jd: float) -> tuple[dict, dict]:
    cjd = mirrored_jd(ft_jd, event_jd)
    conv = positions_at_jd(cjd, include_optional=False)
    rad = positions_at_jd(ft_jd, include_optional=False)
    return conv, rad, cjd


def converse_positions_table(ticker: str, ft_jd: float, event_jd: float) -> pd.DataFrame:
    conv, rad, cjd = positions_at_event(ft_jd, event_jd)
    rows = []
    for name in iter_benchmark_names():
        c = conv[name]
        r = rad[name]
        rows.append(
            {
                "ticker": ticker,
                "body": name,
                "radix_longitude_deg": r.longitude_deg,
                "radix_declination_deg": r.declination_deg,
                "converse_longitude_deg": c.longitude_deg,
                "converse_declination_deg": c.declination_deg,
                "converse_retrograde": c.retrograde,
                "radix_retrograde": r.retrograde,
                "converse_jd_ut": cjd,
            }
        )
    return pd.DataFrame(rows)


def converse_to_radix_aspects(ticker: str, ft_jd: float, event_jd: float) -> pd.DataFrame:
    conv, rad, cjd = positions_at_event(ft_jd, event_jd)
    clon = {k: v.longitude_deg for k, v in conv.items()}
    rlon = {k: v.longitude_deg for k, v in rad.items()}
    matrix = full_directed_aspect_matrix(clon, rlon, body_names=list(iter_benchmark_names()))
    rows = []
    for row in matrix:
        rec = {"ticker": ticker, "family": "converse_to_radix", "converse_jd_ut": cjd}
        rec.update(row)
        rows.append(rec)
    return pd.DataFrame(rows)


def converse_to_converse_aspects(ticker: str, ft_jd: float, event_jd: float) -> pd.DataFrame:
    from aspects import shortest_arc

    conv, _, cjd = positions_at_event(ft_jd, event_jd)
    clon = {k: v.longitude_deg for k, v in conv.items()}
    bodies = sorted(clon.keys())
    rows = []
    for a, b in itertools.combinations(bodies, 2):
        sep = shortest_arc(clon[a], clon[b])
        for asp in MAJOR_ASPECTS:
            orb = orb_for_named_aspect(clon[a], clon[b], asp)
            rows.append(
                {
                    "ticker": ticker,
                    "family": "converse_to_converse",
                    "body_a": a,
                    "body_b": b,
                    "aspect": asp,
                    "separation_deg": sep,
                    "orb_deg": orb,
                    "converse_jd_ut": cjd,
                }
            )
    return pd.DataFrame(rows)


def declination_contacts(ticker: str, ft_jd: float, event_jd: float) -> pd.DataFrame:
    conv, rad, cjd = positions_at_event(ft_jd, event_jd)
    bodies = list(iter_benchmark_names())
    rows = []
    for a in bodies:
        for b in bodies:
            d_conv = conv[a].declination_deg
            d_rad = rad[b].declination_deg
            for kind, orb in classify_declination_pair(d_conv, d_rad):
                rows.append(
                    {
                        "ticker": ticker,
                        "family": "converse_to_radix_decl",
                        "conv_body": a,
                        "other_body": b,
                        "kind": kind,
                        "orb_deg": orb,
                        "converse_jd_ut": cjd,
                    }
                )
    for a, b in itertools.combinations(bodies, 2):
        d1, d2 = conv[a].declination_deg, conv[b].declination_deg
        for kind, orb in classify_declination_pair(d1, d2):
            rows.append(
                {
                    "ticker": ticker,
                    "family": "converse_to_converse_decl",
                    "conv_body": a,
                    "other_body": b,
                    "kind": kind,
                    "orb_deg": orb,
                    "converse_jd_ut": cjd,
                }
            )
    return pd.DataFrame(rows)


def _count_c2r(df: pd.DataFrame, orb: float) -> dict:
    if df.empty:
        return {"sq_tight": 0, "sq_opp_tight": 0, "hard_tight": 0}
    sq = (df["orb_sq"] <= orb + 1e-12).sum()
    opp = (df["orb_opp"] <= orb + 1e-12).sum()
    conj = (df["orb_conj"] <= orb + 1e-12).sum()
    return {
        "sq_tight": int(sq),
        "sq_opp_tight": int(sq + opp),
        "hard_tight": int(sq + opp + conj),
    }


def _count_c2c(df: pd.DataFrame, orb: float) -> dict:
    if df.empty:
        return {"sq_tight": 0, "sq_opp_tight": 0, "hard_tight": 0}
    sq = ((df["aspect"] == "sq") & (df["orb_deg"] <= orb + 1e-12)).sum()
    opp = ((df["aspect"] == "opp") & (df["orb_deg"] <= orb + 1e-12)).sum()
    conj = ((df["aspect"] == "conj") & (df["orb_deg"] <= orb + 1e-12)).sum()
    return {
        "sq_tight": int(sq),
        "sq_opp_tight": int(sq + opp),
        "hard_tight": int(sq + opp + conj),
    }


def c2r_hard_count(ft_jd: float, event_jd: float, orb: float = ORB_PRIMARY) -> int:
    """Lightweight c2r conj/sq/opp count at orb (historical loops)."""
    conv, rad, _ = positions_at_event(ft_jd, event_jd)
    clon = {k: v.longitude_deg for k, v in conv.items()}
    rlon = {k: v.longitude_deg for k, v in rad.items()}
    matrix = full_directed_aspect_matrix(clon, rlon, body_names=list(iter_benchmark_names()))
    n = 0
    for row in matrix:
        if row["orb_conj"] <= orb or row["orb_sq"] <= orb or row["orb_opp"] <= orb:
            n += 1
    return n


def feature_vector(ticker: str, ft_jd: float, event_jd: float) -> dict:
    c2r = converse_to_radix_aspects(ticker, ft_jd, event_jd)
    c2c = converse_to_converse_aspects(ticker, ft_jd, event_jd)
    decl = declination_contacts(ticker, ft_jd, event_jd)
    out = {"ticker": ticker}
    for orb, tag in ((ORB_PRIMARY, "1deg"), (ORB_SECONDARY, "0p5deg")):
        cr = _count_c2r(c2r, orb)
        cc = _count_c2c(c2c, orb)
        out[f"c2r_sq_count_{tag}"] = cr.get("sq_tight", 0)
        out[f"c2r_sq_opp_count_{tag}"] = cr.get("sq_opp_tight", 0)
        out[f"c2r_hard_count_{tag}"] = cr.get("hard_tight", 0)
        out[f"c2c_sq_count_{tag}"] = cc.get("sq_tight", 0)
        out[f"c2c_sq_opp_count_{tag}"] = cc.get("sq_opp_tight", 0)
        out[f"c2c_hard_count_{tag}"] = cc.get("hard_tight", 0)
        d_cr = decl[(decl["family"] == "converse_to_radix_decl") & (decl["orb_deg"] <= orb)]
        d_cc = decl[(decl["family"] == "converse_to_converse_decl") & (decl["orb_deg"] <= orb)]
        out[f"c2r_decl_contact_count_{tag}"] = len(d_cr)
        out[f"c2c_decl_contact_count_{tag}"] = len(d_cc)
    # Outer contacts @1°
    tight = c2r[c2r["best_orb"] <= ORB_PRIMARY]
    outer = tight[
        tight["from_body"].str.replace("conv:", "").isin(OUTERS)
        | tight["to_body"].str.replace("radix:", "").isin(OUTERS)
    ]
    out["c2r_outer_hard_1deg"] = len(outer[outer["best_aspect"].isin(HARD)])
    return out
