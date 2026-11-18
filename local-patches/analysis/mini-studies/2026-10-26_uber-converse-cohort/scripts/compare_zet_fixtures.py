#!/usr/bin/env python3
"""Compare radix + mirror columns to Swiss Ephemeris (Aries adapter)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

STUDY = Path(__file__).resolve().parents[1]
ROOT = STUDY.parents[3]
sys.path[:0] = [str(STUDY), str(ROOT), str(ROOT / "SWEP" / "src")]

from analysis import converse_jd_for  # noqa: E402
from ephemeris import positions_at_jd  # noqa: E402
from radix import RADIX_COHORT  # noqa: E402

SIGNS = {
    "Aries": 0,
    "Taurus": 1,
    "Gemini": 2,
    "Cancer": 3,
    "Leo": 4,
    "Virgo": 5,
    "Libra": 6,
    "Scorpio": 7,
    "Sagittarius": 8,
    "Capricorn": 9,
    "Aquarius": 10,
    "Pisces": 11,
}


def lon_from_spec(spec: dict) -> float:
    return (SIGNS[spec["sign"]] * 30.0) + spec["d"] + spec["m"] / 60.0 + spec["s"] / 3600.0


def main() -> None:
    fixture_dir = STUDY / "fixtures" / "zet_transcribed"
    rows = []
    for path in sorted(fixture_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        rk = data["radix_key"]
        ek = data["event_key"]
        rjd = RADIX_COHORT[rk].birth_jd
        cjd = converse_jd_for(rk, ek)
        nat = positions_at_jd(rjd)
        mir = positions_at_jd(cjd)
        max_lon = 0.0
        for column, posmap, block in (
            ("natal", nat, data.get("natal", {})),
            ("mirror", mir, data.get("mirror", {})),
        ):
            for body, spec in block.items():
                if body not in posmap or "sign" not in spec:
                    continue
                exp = lon_from_spec(spec)
                got = posmap[body].longitude_deg
                delta = abs(got - exp)
                max_lon = max(max_lon, delta)
                rows.append(
                    {
                        "fixture": path.name,
                        "column": column,
                        "body": body,
                        "delta_lon_deg": delta,
                        "retro_match": spec.get("retrograde") == posmap[body].retrograde
                        if "retrograde" in spec
                        else "",
                    }
                )
        print(f"{path.name}: max longitude delta {max_lon:.6f}°")
    out = STUDY / "output" / "zet_fixture_comparison.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    import csv

    with out.open("w", newline="", encoding="utf-8") as fh:
        if rows:
            writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
