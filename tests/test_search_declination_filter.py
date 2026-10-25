# Copyright (C) 2026 Max Lange
# SPDX-License-Identifier: AGPL-3.0-or-later

import searchbackend


def test_declination_par_cpar_orb():
    par, cpar = searchbackend.declination_par_cpar(10.0, 10.2, 0.5)
    assert par is True
    assert cpar is False
    par, cpar = searchbackend.declination_par_cpar(10.0, -10.1, 0.5)
    assert par is False
    assert cpar is True


def test_row_passes_declination_filter_requires_supported_state():
    class Row:
        event_jd = 2451545.0
        promittor_id = "planet:moon"
        significator_id = "planet:saturn"

    class Catalog:
        def get(self, _oid):
            return None

    assert searchbackend.row_passes_declination_filter(
        Row(), Catalog(), None, True, False, 1.0
    ) is False
