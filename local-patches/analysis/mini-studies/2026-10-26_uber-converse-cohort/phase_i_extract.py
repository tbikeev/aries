"""Extract directed converse→radix declination matrix (Phase I-A)."""

from __future__ import annotations

from dataclasses import dataclass

from aspects import MAJOR_ASPECTS, orb_for_named_aspect
from converse import mirrored_jd
from declination_geometry import DECL_ORBS, classify_declination_pair, orb_within
from ephemeris import iter_benchmark_names, positions_at_jd
from radix import RADIX_COHORT


def directed_declination_rows(
    radix_key: str,
    event_jd: float,
    *,
    report_date: str,
    reaction_session: str,
) -> list[dict]:
    spec = RADIX_COHORT[radix_key]
    birth_jd = spec.birth_jd
    cjd = mirrored_jd(birth_jd, event_jd)
    conv = positions_at_jd(cjd, include_optional=False)
    rad = positions_at_jd(birth_jd, include_optional=False)
    bodies = list(iter_benchmark_names())
    rows: list[dict] = []
    for a in bodies:
        pc = conv[a]
        for b in bodies:
            pr = rad[b]
            d_conv = pc.declination_deg
            d_rad = pr.declination_deg
            for kind, orb in classify_declination_pair(d_conv, d_rad):
                row = {
                    "report_date": report_date,
                    "reaction_session": reaction_session,
                    "radix_key": radix_key,
                    "converse_jd_ut": cjd,
                    "conv_body": a,
                    "radix_body": b,
                    "conv_decl_deg": d_conv,
                    "radix_decl_deg": d_rad,
                    "decl_aspect": kind,
                    "decl_orb_deg": orb,
                    "conv_retrograde": pc.retrograde,
                }
                for th in DECL_ORBS:
                    tag = str(th).replace(".", "")
                    row[f"le_orb_{tag}"] = orb_within(orb, th)
                rows.append(row)
    return rows


def directed_longitude_for_pair(
    conv_lon: dict[str, float],
    rad_lon: dict[str, float],
    conv_body: str,
    radix_body: str,
) -> tuple[str | None, float]:
    from aspects import full_directed_aspect_matrix

    matrix = full_directed_aspect_matrix(
        conv_lon,
        rad_lon,
        body_names=[conv_body, radix_body] if conv_body != radix_body else [conv_body],
    )
    for row in matrix:
        if row["from_body"].endswith(conv_body) and row["to_body"].endswith(radix_body):
            return row["best_aspect"], float(row["best_orb"])
    lon_f = conv_lon[conv_body]
    lon_t = rad_lon[radix_body]
    best = None
    best_orb = 999.0
    for asp in MAJOR_ASPECTS:
        o = orb_for_named_aspect(lon_f, lon_t, asp)
        if o < best_orb:
            best_orb = o
            best = asp
    return best, best_orb


def build_all_declination(
    events: list[tuple[str, str, float]],
) -> list[dict]:
    out: list[dict] = []
    for report_date, reaction_session, ejd in events:
        for rk in ("FT", "INC", "DK"):
            out.extend(
                directed_declination_rows(
                    rk,
                    ejd,
                    report_date=report_date,
                    reaction_session=reaction_session,
                )
            )
    return out
