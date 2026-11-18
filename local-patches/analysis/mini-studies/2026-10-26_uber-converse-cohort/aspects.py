"""Longitude and declination aspect math."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable

MAJOR_ASPECTS: dict[str, float] = {
    "conj": 0.0,
    "sext": 60.0,
    "sq": 90.0,
    "tri": 120.0,
    "opp": 180.0,
}

ORB_THRESHOLDS = (0.25, 0.5, 1.0, 2.0)  # 15', 30', 1°, 2°


@dataclass(frozen=True)
class LongitudeAspect:
    body_a: str
    body_b: str
    aspect: str
    separation_deg: float
    orb_deg: float


@dataclass(frozen=True)
class DeclinationContact:
    body_a: str
    body_b: str
    kind: str  # par | cpar
    delta_deg: float


def shortest_arc(lon_a: float, lon_b: float) -> float:
    diff = (float(lon_b) - float(lon_a)) % 360.0
    if diff > 180.0:
        diff = 360.0 - diff
    return diff


def longitude_aspect(lon_a: float, lon_b: float) -> tuple[str | None, float]:
    """Closest major aspect by orb (exploratory). Do not use for directed regression checks."""
    arc = shortest_arc(lon_a, lon_b)
    best_name = None
    best_orb = 999.0
    for name, angle in MAJOR_ASPECTS.items():
        orb = abs(arc - angle)
        if orb < best_orb:
            best_orb = orb
            best_name = name
    return best_name, best_orb


def orb_for_named_aspect(lon_from: float, lon_to: float, aspect: str) -> float:
    """Orb for a directed pair (from → to) and a **named** aspect type only."""
    if aspect not in MAJOR_ASPECTS:
        raise ValueError(f"unknown aspect: {aspect}")
    arc = shortest_arc(float(lon_from), float(lon_to))
    return abs(arc - MAJOR_ASPECTS[aspect])


def directed_aspect_orb(
    positions_from: dict[str, float],
    positions_to: dict[str, float],
    from_body: str,
    to_body: str,
    aspect: str,
) -> float:
    return orb_for_named_aspect(positions_from[from_body], positions_to[to_body], aspect)


def all_longitude_aspects(
    positions_a: dict[str, float],
    positions_b: dict[str, float],
    *,
    body_names: Iterable[str] | None = None,
) -> list[LongitudeAspect]:
    names = list(body_names) if body_names is not None else sorted(set(positions_a) & set(positions_b))
    out: list[LongitudeAspect] = []
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            aspect, orb = longitude_aspect(positions_a[a], positions_b[b])
            if aspect is None:
                continue
            sep = shortest_arc(positions_a[a], positions_b[b])
            out.append(LongitudeAspect(a, b, aspect, sep, orb))
    return out


def cross_aspects(
    positions_left: dict[str, float],
    positions_right: dict[str, float],
    *,
    left_prefix: str = "",
    right_prefix: str = "",
    body_names: Iterable[str] | None = None,
) -> list[LongitudeAspect]:
    """All directed left→right pairs; aspect = closest major type (see ``orb_for_named_aspect`` for tests)."""
    names = list(body_names) if body_names is not None else sorted(set(positions_left) & set(positions_right))
    out: list[LongitudeAspect] = []
    for a in names:
        for b in names:
            aspect, orb = longitude_aspect(positions_left[a], positions_right[b])
            if aspect is None:
                continue
            sep = shortest_arc(positions_left[a], positions_right[b])
            out.append(
                LongitudeAspect(
                    f"{left_prefix}{a}" if left_prefix else a,
                    f"{right_prefix}{b}" if right_prefix else b,
                    aspect,
                    sep,
                    orb,
                )
            )
    return out


def full_directed_aspect_matrix(
    positions_from: dict[str, float],
    positions_to: dict[str, float],
    *,
    from_prefix: str = "conv:",
    to_prefix: str = "radix:",
    body_names: Iterable[str] | None = None,
) -> list[dict]:
    """Every directed conv→radix pair with separation and orbs for all five major aspects."""
    names = list(body_names) if body_names is not None else sorted(set(positions_from) & set(positions_to))
    rows: list[dict] = []
    for a in names:
        for b in names:
            lon_f = positions_from[a]
            lon_t = positions_to[b]
            sep = shortest_arc(lon_f, lon_t)
            row: dict = {
                "from_body": f"{from_prefix}{a}",
                "to_body": f"{to_prefix}{b}",
                "separation_deg": sep,
            }
            for asp_name in MAJOR_ASPECTS:
                row[f"orb_{asp_name}"] = orb_for_named_aspect(lon_f, lon_t, asp_name)
            row["best_aspect"] = min(MAJOR_ASPECTS, key=lambda k: row[f"orb_{k}"])
            row["best_orb"] = row[f"orb_{row['best_aspect']}"]
            rows.append(row)
    return rows


def declination_contacts(
    decl_a: dict[str, float],
    decl_b: dict[str, float],
    *,
    body_names: Iterable[str] | None = None,
) -> list[DeclinationContact]:
    names = list(body_names) if body_names is not None else sorted(set(decl_a) & set(decl_b))
    out: list[DeclinationContact] = []
    for a in names:
        for b in names:
            if a == b:
                continue
            d1, d2 = float(decl_a[a]), float(decl_b[b])
            par_delta = abs(d1 - d2)
            cpar_delta = abs(d1 + d2)
            out.append(DeclinationContact(a, b, "par", par_delta))
            out.append(DeclinationContact(a, b, "cpar", cpar_delta))
    return out


def orb_bucket(orb_deg: float) -> str:
    for limit in ORB_THRESHOLDS:
        if orb_deg <= limit + 1e-12:
            return f"<={limit:.2f}"
    return ">2.00"


def format_dms(degrees: float) -> str:
    x = float(degrees) % 360.0
    d = int(x)
    m_float = (x - d) * 60.0
    m = int(m_float)
    s = (m_float - m) * 60.0
    return f"{d}°{m:02d}'{s:05.2f}\""
