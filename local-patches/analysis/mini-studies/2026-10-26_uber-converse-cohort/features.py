"""Phase D activation features (descriptive, no valence assumptions)."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass

from aspects import LongitudeAspect, ORB_THRESHOLDS


@dataclass
class EventFeatures:
    event_key: str
    counts: dict[str, float | int | str]


def build_event_features(
    event_key: str,
    pair_aspects: dict[str, list[LongitudeAspect]],
    decl_hits: list[dict],
    registry_hits: list[dict],
) -> EventFeatures:
    """One feature vector per event (3 radix comparisons aggregated)."""
    all_aspects: list[LongitudeAspect] = []
    for aspects in pair_aspects.values():
        all_aspects.extend(aspects)

    within_1 = [a for a in all_aspects if a.orb_deg <= 1.0]
    within_15 = [a for a in all_aspects if a.orb_deg <= 0.25]

    aspect_class = Counter(a.aspect for a in within_1)
    converse_body_hits = Counter(a.body_a.split(":")[-1] for a in within_1)
    radix_body_hits = Counter(a.body_b.split(":")[-1] for a in within_1)

    combined_lon_decl = sum(
        1
        for d in decl_hits
        if d.get("orb_deg", 99) <= 1.0
        and any(
            d.get("conv_body") in a.body_a and d.get("radix_body") in a.body_b
            for a in within_1
        )
    )

    registry_activation = sum(1 for r in registry_hits if r.get("activated"))

    return EventFeatures(
        event_key=event_key,
        counts={
            "aspects_le_1deg_total": len(within_1),
            "aspects_le_15arcmin_total": len(within_15),
            "aspects_conj_le_1": aspect_class.get("conj", 0),
            "aspects_sq_le_1": aspect_class.get("sq", 0),
            "aspects_tri_le_1": aspect_class.get("tri", 0),
            "aspects_opp_le_1": aspect_class.get("opp", 0),
            "aspects_sext_le_1": aspect_class.get("sext", 0),
            "unique_converse_bodies_le_1": len(converse_body_hits),
            "unique_radix_bodies_le_1": len(radix_body_hits),
            "top_converse_body": converse_body_hits.most_common(1)[0][0] if converse_body_hits else "",
            "top_radix_body": radix_body_hits.most_common(1)[0][0] if radix_body_hits else "",
            "decl_le_1deg": sum(1 for d in decl_hits if d.get("delta_deg", 99) <= 1.0),
            "combined_lon_decl_pairs": combined_lon_decl,
            "registry_structure_hits": registry_activation,
            "cluster_le_15arcmin": len(within_15),
            "consensus_pairs_all_three_radix": _consensus_pairs(pair_aspects, 1.0),
        },
    )


def _consensus_pairs(pair_aspects: dict[str, list[LongitudeAspect]], orb: float) -> int:
    """Aspect geometry repeated across FT/INC/DK for the same converse→radix pair class."""
    signatures: list[frozenset[str]] = []
    for aspects in pair_aspects.values():
        for a in aspects:
            if a.orb_deg <= orb:
                signatures.append(
                    frozenset({a.body_a, a.body_b, a.aspect}),
                )
    counts = Counter(signatures)
    return sum(1 for c in counts.values() if c >= 2)


def features_to_row(features: EventFeatures) -> dict[str, float | int | str]:
    row = {"event_key": features.event_key}
    row.update(features.counts)
    return row
