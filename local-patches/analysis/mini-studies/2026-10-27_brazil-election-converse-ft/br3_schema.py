"""BR-3 frozen dimensions, indices, and metadata for aspect-power matrices."""

from __future__ import annotations

import itertools
import json
from pathlib import Path

from brazil_paths import STUDY_ROOT

BR3_TICKERS: tuple[str, ...] = (
    "ABEV",
    "BBD",
    "ERJ",
    "ITUB",
    "NU",
    "PAGS",
    "PBR",
    "STNE",
    "VALE",
    "XP",
)

PLANETS: tuple[str, ...] = (
    "Sun",
    "Moon",
    "Mercury",
    "Venus",
    "Mars",
    "Jupiter",
    "Saturn",
    "Uranus",
    "Neptune",
    "Pluto",
    "Node",
)

ASPECTS: tuple[str, ...] = ("con", "opp", "squ", "tri", "sex")

ASPECT_ASTROLOG: dict[str, str] = {
    "con": "Con",
    "opp": "Opp",
    "squ": "Squ",
    "tri": "Tri",
    "sex": "Sex",
}

LABELS: tuple[str, ...] = ("NEG", "POS")

OUTPUT_BR3 = STUDY_ROOT / "output" / "br3"
CACHE_BR3 = STUDY_ROOT / "cache" / "br3"

# Spot-check reference powers (Astrolog 7.70 -a output, existing debug files).
SPOT_CHECKS = (
    {
        "ticker": "PAGS",
        "session": "2026-10-26",
        "mode": "c2c",
        "planet_a": "Mars",
        "planet_b": "Pluto",
        "aspect": "squ",
        "power": 7.1102,
        "tolerance": 0.02,
    },
    {
        "ticker": "XP",
        "session": "2026-10-26",
        "mode": "c2c",
        "planet_a": "Mars",
        "planet_b": "Node",
        "aspect": "squ",
        "power": 4.0670,
        "tolerance": 0.02,
    },
    {
        "ticker": "NU",
        "session": "2026-10-26",
        "mode": "c2r",
        "converse": "Mercury",
        "radix": "Saturn",
        "aspect": "con",
        "power": 9.9211,
        "tolerance": 0.02,
    },
    {
        "ticker": "STNE",
        "session": "2026-10-26",
        "mode": "c2c",
        "planet_a": "Mars",
        "planet_b": "Uranus",
        "aspect": "tri",
        "power": 5.3515,
        "tolerance": 0.02,
    },
)


def c2c_pair_index(a: str, b: str) -> int:
    ia, ib = PLANETS.index(a), PLANETS.index(b)
    lo, hi = (ia, ib) if ia < ib else (ib, ia)
    pairs = list(itertools.combinations(range(len(PLANETS)), 2))
    return pairs.index((lo, hi))


def c2c_pair_planets(k: int) -> tuple[str, str]:
    pairs = list(itertools.combinations(PLANETS, 2))
    return pairs[k]


def aspect_index(asp: str) -> int:
    return ASPECTS.index(asp)


def build_matrix_metadata(*, extremes: int) -> dict:
    c2c_pairs = [{"index": i, "planet_1": p[0], "planet_2": p[1]} for i, p in enumerate(itertools.combinations(PLANETS, 2))]
    return {
        "phase": "BR-3",
        "extremes_per_tail": extremes,
        "n_events": extremes * 2,
        "n_tickers": len(BR3_TICKERS),
        "tickers": list(BR3_TICKERS),
        "planets": list(PLANETS),
        "aspects": list(ASPECTS),
        "labels": list(LABELS),
        "event_index_order": "NEG rank 1..N then POS rank 1..N",
        "c2c_pairs": c2c_pairs,
        "c2c_shape": [len(BR3_TICKERS), extremes * 2, len(c2c_pairs), len(ASPECTS)],
        "c2r_shape": [len(BR3_TICKERS), extremes * 2, len(PLANETS), len(PLANETS), len(ASPECTS)],
        "aggregate_c2c_shape": [2, len(BR3_TICKERS), len(c2c_pairs), len(ASPECTS)],
        "aggregate_c2r_shape": [2, len(BR3_TICKERS), len(PLANETS), len(PLANETS), len(ASPECTS)],
        "pooled_c2c_shape": [2, len(c2c_pairs), len(ASPECTS)],
        "pooled_c2r_shape": [2, len(PLANETS), len(PLANETS), len(ASPECTS)],
        "power_engine": {
            "name": "Astrolog",
            "version": "7.70",
            "invocation": "reverse_chart.sh --key -1.0 + internal -a (c2c) + cross -rp0 -pd -1.0 -a (c2r)",
            "power_source": "Astrolog -a aspect listing power field (unchanged from BR-1 debug)",
            "orbs": "Engine default max orbs per aspect type; no BR-3 retuning",
            "weights": "Astrolog default aspect power weighting",
            "retrograde": "As reported in aspect line positions",
            "precision": "float64 in npz; raw power as printed",
            "inactive_cells": {"active": False, "power": 0.0, "orb_deg": "NaN"},
        },
        "event_session_local": "09:30 America/New_York",
    }


def write_matrix_metadata(path: Path, *, extremes: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(build_matrix_metadata(extremes=extremes), indent=2), encoding="utf-8")
