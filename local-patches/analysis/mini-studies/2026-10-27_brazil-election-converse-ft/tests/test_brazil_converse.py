"""Unit tests for Brazil converse study."""

from __future__ import annotations

import os
import sys
from datetime import date, datetime, time, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

STUDY = Path(__file__).resolve().parents[1]
UBER = STUDY.parent / "2026-10-26_uber-converse-cohort"
ROOT = STUDY.parents[3]
for p in (str(ROOT), str(ROOT / "SWEP" / "src"), str(UBER), str(STUDY)):
    if p not in sys.path:
        sys.path.insert(0, p)

from converse import mirrored_jd, utc_to_jd  # noqa: E402
from converse_features import event_jd_from_local  # noqa: E402
from brazil_paths import EVENT_LOCAL  # noqa: E402


def test_mirrored_jd_symmetric():
    ft = utc_to_jd(2018, 1, 25, 14, 32, 0)
    ev = event_jd_from_local(EVENT_LOCAL)
    c = mirrored_jd(ft, ev)
    assert abs(mirrored_jd(ft, c) - ev) < 1e-9


def test_pags_ft_jd_reproducible():
    if not os.environ.get("MUNKASEY_AVAILABLE", "1") == "1":
        return
    from ft_registry import build_registry, ft_birth_jd

    reg = build_registry()
    row = reg[reg["ticker"] == "PAGS"].iloc[0]
    jd, ok = ft_birth_jd(row)
    assert ok and jd is not None
    jd2, ok2 = ft_birth_jd(row)
    assert ok2 and abs(jd - jd2) < 1e-12


def test_c2c_no_self_aspects():
    from converse_features import converse_to_converse_aspects
    from ft_registry import build_registry, ft_birth_jd

    reg = build_registry()
    row = reg[reg["ticker"] == "PAGS"].iloc[0]
    jd, ok = ft_birth_jd(row)
    if not ok:
        return
    ev = event_jd_from_local(EVENT_LOCAL)
    df = converse_to_converse_aspects("PAGS", jd, ev)
    assert (df["body_a"] != df["body_b"]).all()
    assert df["family"].eq("converse_to_converse").all()


if __name__ == "__main__":
    test_mirrored_jd_symmetric()
    test_pags_ft_jd_reproducible()
    test_c2c_no_self_aspects()
    print("OK: brazil converse tests")
