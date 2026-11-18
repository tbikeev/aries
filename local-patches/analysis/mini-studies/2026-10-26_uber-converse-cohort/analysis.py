"""Phases B–E pipeline and CSV/report writers."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict
from pathlib import Path

from aspects import (
    DeclinationContact,
    LongitudeAspect,
    cross_aspects,
    declination_contacts,
    full_directed_aspect_matrix,
    orb_bucket,
    orb_for_named_aspect,
)
from cohort import build_cohort_registry, verify_expected_registry
from converse import mirrored_jd
from ephemeris import iter_benchmark_names, positions_at_jd
from features import build_event_features, features_to_row
from radix import EVENTS, RADIX_COHORT

STUDY_ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = STUDY_ROOT / "output"
FIXTURE_DIR = STUDY_ROOT / "fixtures" / "zet_transcribed"

PHASE_C_EXPECTED = {
    ("FT", "NEG-01"): [
        ("Mars", "Pluto", "sq", 0.05),
        ("Sun", "Sun", "sq", 0.67),
        ("Uranus", "Mercury", "conj", 0.78),
    ],
    ("FT", "POS-01"): [
        ("Jupiter", "Uranus", "conj", 0.37),
        ("Mercury", "Venus", "sext", 0.43),
        ("Mars", "Saturn", "tri", 0.67),
    ],
    ("INC", "NEG-01"): [
        ("Saturn", "Node", "opp", 0.03),
        ("Node", "Moon", "sq", 0.22),
        ("Moon", "Mercury", "sq", 0.23),
    ],
    ("INC", "POS-01"): [
        ("Neptune", "Mars", "sext", 0.27),
        ("Venus", "Saturn", "sext", 0.28),
        ("Venus", "Pluto", "tri", 0.63),
    ],
    ("DK", "NEG-01"): [
        ("Jupiter", "Mercury", "opp", 0.27),
        ("Moon", "Pluto", "sq", 0.35),
        # Zet DK-neg screenshot: 7°58′43″ Pisces is **Chiron** (Mir), not Node; Node is 12°34′ Aries.
        ("Chiron", "Mercury", "sq", 0.45),
    ],
    ("DK", "POS-01"): [
        ("Sun", "Neptune", "tri", 0.5),
        ("Sun", "Node", "conj", 0.73),
        ("Pluto", "Jupiter", "sq", 0.82),
    ],
}

PHASE_C_COUNTS = {
    ("FT", "NEG-01"): 7,
    ("FT", "POS-01"): 5,
    ("INC", "NEG-01"): 4,
    ("INC", "POS-01"): 7,
    ("DK", "NEG-01"): 6,
    ("DK", "POS-01"): 5,
}


def converse_jd_for(radix_key: str, event_key: str) -> float:
    r = RADIX_COHORT[radix_key]
    e = EVENTS[event_key]
    return mirrored_jd(r.birth_jd, e.event_jd)


def directed_converse_radix_orb(
    radix_key: str,
    event_key: str,
    conv_body: str,
    rad_body: str,
    aspect: str,
) -> float:
    """Directed converse → radix orb for one named major aspect (verification primitive)."""
    r = RADIX_COHORT[radix_key]
    cjd = converse_jd_for(radix_key, event_key)
    conv = positions_at_jd(cjd, include_optional=True)
    rad = positions_at_jd(r.birth_jd, include_optional=True)
    return orb_for_named_aspect(
        conv[conv_body].longitude_deg,
        rad[rad_body].longitude_deg,
        aspect,
    )


def converse_to_radix_aspects(radix_key: str, event_key: str) -> list[LongitudeAspect]:
    r = RADIX_COHORT[radix_key]
    cjd = converse_jd_for(radix_key, event_key)
    conv = positions_at_jd(cjd)
    rad = positions_at_jd(r.birth_jd)
    conv_lon = {k: p.longitude_deg for k, p in conv.items()}
    rad_lon = {k: p.longitude_deg for k, p in rad.items()}
    bodies = list(iter_benchmark_names())
    return cross_aspects(
        conv_lon,
        rad_lon,
        left_prefix="conv",
        right_prefix="radix",
        body_names=bodies,
    )


def converse_to_radix_declination(radix_key: str, event_key: str) -> list[DeclinationContact]:
    r = RADIX_COHORT[radix_key]
    cjd = converse_jd_for(radix_key, event_key)
    conv = positions_at_jd(cjd)
    rad = positions_at_jd(r.birth_jd)
    conv_d = {k: p.declination_deg for k, p in conv.items()}
    rad_d = {k: p.declination_deg for k, p in rad.items()}
    bodies = list(iter_benchmark_names())
    return declination_contacts(conv_d, rad_d, body_names=bodies)


def count_aspects_le_1(aspects: list[LongitudeAspect]) -> int:
    bodies = list(iter_benchmark_names())
    n = len(bodies)
    hits = [a for a in aspects if a.orb_deg <= 1.0 + 1e-9]
    return len(hits)


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def run_full_analysis(extra_events: list[dict] | None = None) -> dict:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    bodies = list(iter_benchmark_names())

    # Radix positions
    radix_rows = []
    for key, spec in RADIX_COHORT.items():
        pos = positions_at_jd(spec.birth_jd)
        for name, p in pos.items():
            radix_rows.append(
                {
                    "radix_key": key,
                    "body": name,
                    "longitude_deg": p.longitude_deg,
                    "declination_deg": p.declination_deg,
                    "retrograde": p.retrograde,
                    "jd_ut": spec.birth_jd,
                }
            )
    write_csv(OUTPUT_DIR / "radix_positions.csv", radix_rows)

    # Cohort (phase A)
    cohort = build_cohort_registry()
    cohort_lon_rows = []
    cohort_decl_rows = []
    for block in cohort:
        for a in block.longitude_aspects:
            cohort_lon_rows.append(
                {
                    "pair": f"{block.left}-{block.right}",
                    "body_a": a.body_a,
                    "body_b": a.body_b,
                    "aspect": a.aspect,
                    "orb_deg": a.orb_deg,
                    "orb_bucket": orb_bucket(a.orb_deg),
                }
            )
        for d in block.declination:
            cohort_decl_rows.append(
                {
                    "pair": f"{block.left}-{block.right}",
                    "body_a": d.body_a,
                    "body_b": d.body_b,
                    "kind": d.kind,
                    "delta_deg": d.delta_deg,
                }
            )
    write_csv(OUTPUT_DIR / "cohort_longitude_aspects.csv", cohort_lon_rows)
    write_csv(OUTPUT_DIR / "cohort_declination_contacts.csv", cohort_decl_rows)
    phase_a_report = verify_expected_registry(cohort)
    write_csv(OUTPUT_DIR / "phase_a_registry_check.csv", phase_a_report)

    # Converse positions + phase B/C
    event_keys = list(EVENTS.keys())
    if extra_events:
        for idx, ev in enumerate(extra_events):
            event_keys.append(ev.get("label", f"EV-{idx}"))

    converse_rows = []
    aspect_rows = []
    decl_rows = []
    matrix_rows: list[dict] = []
    phase_c_checks = []
    phase_c_count_rows = []

    for radix_key in RADIX_COHORT:
        for event_key in EVENTS:
            cjd = converse_jd_for(radix_key, event_key)
            pos = positions_at_jd(cjd)
            for name, p in pos.items():
                converse_rows.append(
                    {
                        "radix_key": radix_key,
                        "event_key": event_key,
                        "body": name,
                        "converse_jd_ut": cjd,
                        "longitude_deg": p.longitude_deg,
                        "declination_deg": p.declination_deg,
                        "retrograde": p.retrograde,
                    }
                )
            aspects = converse_to_radix_aspects(radix_key, event_key)
            for a in aspects:
                aspect_rows.append(
                    {
                        "radix_key": radix_key,
                        "event_key": event_key,
                        "conv_body": a.body_a,
                        "radix_body": a.body_b,
                        "aspect": a.aspect,
                        "separation_deg": a.separation_deg,
                        "orb_deg": a.orb_deg,
                        "orb_bucket": orb_bucket(a.orb_deg),
                    }
                )
            decl = converse_to_radix_declination(radix_key, event_key)
            for d in decl:
                decl_rows.append(
                    {
                        "radix_key": radix_key,
                        "event_key": event_key,
                        "conv_body": d.body_a,
                        "radix_body": d.body_b,
                        "kind": d.kind,
                        "delta_deg": d.delta_deg,
                    }
                )

            expected = PHASE_C_EXPECTED.get((radix_key, event_key), [])
            for conv_b, rad_b, asp, max_orb in expected:
                found_orb = directed_converse_radix_orb(
                    radix_key, event_key, conv_b, rad_b, asp
                )
                phase_c_checks.append(
                    {
                        "radix_key": radix_key,
                        "event_key": event_key,
                        "conv_body": conv_b,
                        "radix_body": rad_b,
                        "direction": "converse→radix",
                        "aspect": asp,
                        "expected_max_orb": max_orb,
                        "found_orb": found_orb,
                        "ok": found_orb <= max_orb + 0.05,
                    }
                )
            # Full directed matrix (all five orbs per pair)
            cjd = converse_jd_for(radix_key, event_key)
            conv_lon = {k: p.longitude_deg for k, p in positions_at_jd(cjd).items()}
            rad_lon = {k: p.longitude_deg for k, p in positions_at_jd(RADIX_COHORT[radix_key].birth_jd).items()}
            matrix_rows.extend(
                {
                    "radix_key": radix_key,
                    "event_key": event_key,
                    **row,
                }
                for row in full_directed_aspect_matrix(conv_lon, rad_lon, body_names=bodies)
            )
            found = count_aspects_le_1(aspects)
            ref = PHASE_C_COUNTS.get((radix_key, event_key), -1)
            phase_c_count_rows.append(
                {
                    "radix_key": radix_key,
                    "event_key": event_key,
                    "found_le_1deg": found,
                    "reference_le_1deg": ref,
                    "delta": found - ref if ref >= 0 else "",
                }
            )

    write_csv(OUTPUT_DIR / "converse_positions.csv", converse_rows)
    write_csv(OUTPUT_DIR / "converse_radix_longitude_aspects.csv", aspect_rows)
    write_csv(OUTPUT_DIR / "converse_radix_directed_aspect_matrix.csv", matrix_rows)
    write_csv(OUTPUT_DIR / "converse_radix_declination_contacts.csv", decl_rows)
    write_csv(OUTPUT_DIR / "phase_c_contact_check.csv", phase_c_checks)
    write_csv(OUTPUT_DIR / "phase_c_counts_le_1deg.csv", phase_c_count_rows)

    # Phase D/E feature matrix (one row per event)
    feature_rows = []
    for event_key in EVENTS:
        pair_aspects = {
            rk: converse_to_radix_aspects(rk, event_key) for rk in RADIX_COHORT
        }
        decl_hits = []
        for rk in RADIX_COHORT:
            for d in converse_to_radix_declination(rk, event_key):
                decl_hits.append(
                    {
                        "conv_body": d.body_a,
                        "radix_body": d.body_b,
                        "kind": d.kind,
                        "delta_deg": d.delta_deg,
                    }
                )
        feats = build_event_features(event_key, pair_aspects, decl_hits, [])
        feature_rows.append(features_to_row(feats))
    write_csv(OUTPUT_DIR / "event_feature_matrix.csv", feature_rows)

    # Human-readable reports
    for event_key in EVENTS:
        lines = [f"# Event {event_key}", ""]
        for rk in RADIX_COHORT:
            aspects = sorted(
                converse_to_radix_aspects(rk, event_key),
                key=lambda a: a.orb_deg,
            )
            lines.append(f"## {rk} converse → {rk} radix")
            for a in aspects[:25]:
                if a.orb_deg <= 2.0:
                    lines.append(
                        f"- {a.body_a} {a.aspect} {a.body_b} orb {a.orb_deg:.4f}° ({orb_bucket(a.orb_deg)})"
                    )
            lines.append("")
        (OUTPUT_DIR / f"report_{event_key}.md").write_text("\n".join(lines), encoding="utf-8")

    summary = {
        "phase_a": phase_a_report,
        "phase_c_checks": phase_c_checks,
        "phase_c_counts": phase_c_count_rows,
        "output_dir": str(OUTPUT_DIR),
    }
    (OUTPUT_DIR / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


if __name__ == "__main__":
    run_full_analysis()
