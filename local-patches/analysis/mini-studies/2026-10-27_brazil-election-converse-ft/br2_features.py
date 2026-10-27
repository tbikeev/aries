"""Frozen BR-2 converse feature counts (C2C primary, C2R comparator) with cache."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from brazil_paths import BR2_ORB_DEG, CACHE_BR2, UBER_STUDY

import sys

sys.path.insert(0, str(UBER_STUDY))

from aspects import MAJOR_ASPECTS, full_directed_aspect_matrix, orb_for_named_aspect  # noqa: E402
from ephemeris import BENCHMARK_IDS, iter_benchmark_names, positions_at_jd  # noqa: E402

from converse_features import converse_to_converse_aspects, positions_at_event  # noqa: E402

PRIMARY_PLANET_SET: tuple[str, ...] = tuple(name for name, _ in BENCHMARK_IDS)


def planet_set_documentation() -> str:
    return (
        "Primary BR-2 longitude set (same as BR-1 / UBER benchmark): "
        + ", ".join(PRIMARY_PLANET_SET)
        + ". Optional bodies (Chiron, Lilith) excluded from primary counts."
    )


def _cache_path(ft_jd: float, event_jd: float) -> Path:
    h = hashlib.sha256(f"{ft_jd:.10f}|{event_jd:.10f}|{BR2_ORB_DEG}".encode()).hexdigest()[:24]
    return CACHE_BR2 / "features" / f"{h}.json"


def _count_aspect_rows(df, aspect: str, orb: float) -> int:
    if df.empty:
        return 0
    return int(((df["aspect"] == aspect) & (df["orb_deg"] <= orb + 1e-12)).sum())


def _c2r_counts(ft_jd: float, event_jd: float, orb: float) -> dict[str, int]:
    conv, rad, _ = positions_at_event(ft_jd, event_jd)
    clon = {k: v.longitude_deg for k, v in conv.items()}
    rlon = {k: v.longitude_deg for k, v in rad.items()}
    matrix = full_directed_aspect_matrix(clon, rlon, body_names=list(iter_benchmark_names()))
    out = {"c2r_sq_count": 0, "c2r_opp_count": 0, "c2r_conj_count": 0, "c2r_hard_count": 0}
    mars_hard = 0
    for row in matrix:
        hit = False
        for asp in ("conj", "sq", "opp"):
            if row[f"orb_{asp}"] <= orb + 1e-12:
                out[f"c2r_{asp}_count"] += 1
                hit = True
        if hit:
            out["c2r_hard_count"] += 1
            body_from = row["from_body"].replace("conv:", "")
            body_to = row["to_body"].replace("radix:", "")
            if body_from == "Mars" or body_to == "Mars":
                mars_hard += 1
    out["c2r_sq_opp_count"] = out["c2r_sq_count"] + out["c2r_opp_count"]
    out["c2r_mars_hard_count"] = mars_hard
    return out


def _c2c_counts_from_jd(ft_jd: float, event_jd: float, orb: float) -> dict[str, int]:
    import itertools

    from aspects import shortest_arc

    conv, _, _ = positions_at_event(ft_jd, event_jd)
    clon = {k: v.longitude_deg for k, v in conv.items()}
    bodies = sorted(clon.keys())
    counts = {f"c2c_{k}_count": 0 for k in ("sq", "opp", "conj", "tri", "sext", "sq_opp", "hard")}
    mars = {f"c2c_mars_{k}_count": 0 for k in ("sq", "opp", "conj", "tri", "sext")}
    min_sq_orb = 999.0
    min_hard_orb = 999.0
    for a, b in itertools.combinations(bodies, 2):
        for asp in MAJOR_ASPECTS:
            o = orb_for_named_aspect(clon[a], clon[b], asp)
            if o <= orb + 1e-12:
                key = f"c2c_{asp}_count" if asp in ("sq", "opp", "conj", "tri", "sext") else None
                if key and key in counts:
                    counts[key] += 1
                if asp in ("conj", "sq", "opp"):
                    counts["c2c_hard_count"] += 1
                    min_hard_orb = min(min_hard_orb, o)
                if asp == "sq":
                    min_sq_orb = min(min_sq_orb, o)
            if "Mars" in (a, b):
                mk = f"c2c_mars_{asp}_count"
                if mk in mars and o <= orb + 1e-12:
                    mars[mk] += 1
    counts["c2c_sq_opp_count"] = counts["c2c_sq_count"] + counts["c2c_opp_count"]
    counts["min_c2c_sq_orb_deg"] = float(min_sq_orb if min_sq_orb < 900 else float("nan"))
    counts["min_c2c_hard_orb_deg"] = float(min_hard_orb if min_hard_orb < 900 else float("nan"))
    counts.update(mars)
    return counts


def frozen_feature_bundle(ft_jd: float, event_jd: float, *, use_cache: bool = True) -> dict:
    path = _cache_path(ft_jd, event_jd)
    if use_cache and path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    orb = BR2_ORB_DEG
    out = {
        "ft_jd_ut": ft_jd,
        "event_jd_ut": event_jd,
        "orb_deg": orb,
        "planet_set": list(PRIMARY_PLANET_SET),
    }
    out.update(_c2c_counts_from_jd(ft_jd, event_jd, orb))
    out.update(_c2r_counts(ft_jd, event_jd, orb))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out), encoding="utf-8")
    return out
