"""PAGS Zet reproduction report for 2026-10-26 09:30 EDT."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from brazil_paths import EVENT_LOCAL, FIXTURES, ORB_PRIMARY, ORB_SECONDARY, STUDY_ROOT
from converse_features import (
    converse_positions_table,
    converse_to_converse_aspects,
    converse_to_radix_aspects,
    event_jd_from_local,
)
from ft_registry import build_registry, ft_birth_jd


def _format_pos(lon: float, dec: float, retro: bool) -> str:
    from aspects import format_dms

    r = "R" if retro else "D"
    return f"{format_dms(lon)} ({r}), dec {dec:+.4f}°"


def write_pags_report(out_md: Path, *, ft_jd: float, event_jd: float) -> dict:
    FIXTURES.mkdir(parents=True, exist_ok=True)
    ref_path = FIXTURES / "pags_zet_reference.json"
    ref = {}
    if ref_path.exists():
        ref = json.loads(ref_path.read_text(encoding="utf-8"))

    pos = converse_positions_table("PAGS", ft_jd, event_jd)
    c2r = converse_to_radix_aspects("PAGS", ft_jd, event_jd)
    c2c = converse_to_converse_aspects("PAGS", ft_jd, event_jd)

    import sys
    from brazil_paths import UBER_STUDY

    sys.path.insert(0, str(UBER_STUDY))
    from converse import converse_utc, jd_to_utc_tuple, mirrored_jd

    cjd = mirrored_jd(ft_jd, event_jd)
    conv_utc = jd_to_utc_tuple(cjd)

    lines = [
        "# PAGS converse reproduction — 2026-10-26 09:30 America/New_York",
        "",
        "## Inputs",
        f"- Event local: `{EVENT_LOCAL.isoformat()}`",
        f"- FT radix JD (UT): `{ft_jd:.8f}`",
        f"- Event JD (UT): `{event_jd:.8f}`",
        f"- Converse JD (UT): `{cjd:.8f}`",
        f"- Converse UTC (rounded): `{conv_utc}`",
        "",
        "## Planetary positions (radix | converse)",
        "",
        "| Body | Radix | Converse |",
        "|------|-------|----------|",
    ]
    tol_lon = 0.02  # ~1.2′ default check tolerance
    tol_dec = 0.02
    discrepancies = []
    for _, row in pos.iterrows():
        body = row["body"]
        lines.append(
            f"| {body} | {_format_pos(row['radix_longitude_deg'], row['radix_declination_deg'], row['radix_retrograde'])} "
            f"| {_format_pos(row['converse_longitude_deg'], row['converse_declination_deg'], row['converse_retrograde'])} |"
        )
        if body in ref.get("bodies", {}):
            exp = ref["bodies"][body]
            dlon = abs(row["converse_longitude_deg"] - float(exp.get("converse_longitude_deg", 0)))
            dlon = min(dlon, 360 - dlon)
            ddec = abs(row["converse_declination_deg"] - float(exp.get("converse_declination_deg", 0)))
            if dlon > tol_lon or ddec > tol_dec:
                discrepancies.append(
                    {"body": body, "delta_lon_deg": dlon, "delta_dec_deg": ddec, "tolerance_lon": tol_lon}
                )

    tight_c2r = c2r[
        (c2r["orb_sq"] <= ORB_PRIMARY)
        | (c2r["orb_opp"] <= ORB_PRIMARY)
        | (c2r["orb_conj"] <= ORB_PRIMARY)
    ].sort_values("orb_sq")
    lines.extend(["", f"## Tight converse→radix hard aspects (≤{ORB_PRIMARY}°)", ""])
    for _, r in tight_c2r.head(25).iterrows():
        asp = min(
            ("conj", "sq", "opp"),
            key=lambda a: r[f"orb_{a}"],
        )
        lines.append(
            f"- {r['from_body']} → {r['to_body']}: {asp} orb {r[f'orb_{asp}']:.4f}° "
            f"(sep {r['separation_deg']:.4f}°)"
        )

    tight_c2c = c2c[(c2c["aspect"].isin(["conj", "sq", "opp"])) & (c2c["orb_deg"] <= ORB_PRIMARY)]
    lines.extend(["", f"## Tight internal converse hard aspects (≤{ORB_PRIMARY}°)", ""])
    for _, r in tight_c2c.sort_values("orb_deg").head(20).iterrows():
        lines.append(f"- {r['body_a']}–{r['body_b']}: {r['aspect']} orb {r['orb_deg']:.4f}°")

    lines.extend(
        [
            "",
            "## Zet screenshot validation",
            "",
        ]
    )
    if ref:
        lines.append(
            f"- Reference fixture present: `{ref_path.name}` — bodies compared at ±{tol_lon}° longitude / ±{tol_dec}° declination."
        )
        if discrepancies:
            lines.append(f"- **{len(discrepancies)} body(ies) outside tolerance** (see JSON in report metadata).")
        else:
            lines.append("- All fixture bodies within tolerance (or fixture partial).")
    else:
        lines.append(
            f"- No `{ref_path.name}` yet — paste Zet converse/radix longitudes into that file to auto-validate."
        )
        lines.append("- Engine output above is the Aries/Swiss Ephemeris baseline for manual screenshot comparison.")

    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {
        "converse_utc": conv_utc,
        "n_discrepancies": len(discrepancies),
        "discrepancies": discrepancies,
        "positions": pos,
    }


def main_pags() -> None:
    reg = build_registry()
    row = reg[reg["ticker"] == "PAGS"].iloc[0]
    jd, ok = ft_birth_jd(row)
    if not ok or jd is None:
        raise SystemExit("PAGS requires strict FT timestamp from Munkasey")
    ej = event_jd_from_local(EVENT_LOCAL)
    write_pags_report(STUDY_ROOT / "output" / "pags_zet_reproduction.md", ft_jd=jd, event_jd=ej)
