"""BR-3 unit tests (parsing, indexing, aggregation; no full Astrolog run)."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

STUDY = Path(__file__).resolve().parents[1]
if str(STUDY) not in sys.path:
    sys.path.insert(0, str(STUDY))

from br3_parse import merge_duplicate_cells, normalize_planet, parse_aspect_lines  # noqa: E402
from br3_schema import c2c_pair_index, c2c_pair_planets  # noqa: E402


def test_normalize_node_aliases():
    assert normalize_planet("NNMean") == "Node"
    assert normalize_planet("Mars") == "Mars"


def test_c2c_pair_index_symmetric():
    assert c2c_pair_index("Pluto", "Mars") == c2c_pair_index("Mars", "Pluto")
    a, b = c2c_pair_planets(c2c_pair_index("Mars", "Pluto"))
    assert {a, b} == {"Mars", "Pluto"}


def test_parse_pags_mars_pluto_from_fixture():
    raw = (STUDY / "output" / "astrolog_debug" / "PAGS_2026-10-26_c2c.txt").read_text(encoding="utf-8")
    cells = merge_duplicate_cells(parse_aspect_lines(raw, mode="c2c"), mode="c2c")
    pk = c2c_pair_index("Mars", "Pluto")
    squ = 2
    asp = cells[(pk, squ)]
    assert abs(asp.power - 7.1102) < 0.02


def test_aggregation_identity_synthetic():
    eligible = np.array([[True, True], [False, True]])
    c2c_active = np.zeros((2, 2, 55, 5), dtype=bool)
    c2c_power = np.zeros((2, 2, 55, 5), dtype=np.float64)
    c2c_active[0, 0, 0, 0] = True
    c2c_power[0, 0, 0, 0] = 3.0
    c2c_active[0, 1, 0, 0] = True
    c2c_power[0, 1, 0, 0] = 4.0
    eix = [0, 1]
    ti = 0
    ind_n = c2c_active[ti, eix].sum(axis=0).astype(np.int32)
    ind_s = c2c_power[ti, eix].sum(axis=0)
    assert ind_n[0, 0] == 2
    assert ind_s[0, 0] == 7.0
