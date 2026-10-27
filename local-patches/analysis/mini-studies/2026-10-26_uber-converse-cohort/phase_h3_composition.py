"""H3: decompose DK square count by converse source and radix target."""

from __future__ import annotations

import pandas as pd

from earnings_paths import EARNINGS_OUTPUT

BODIES = (
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

CLASS_MAP = {
    "Sun": "luminary",
    "Moon": "luminary",
    "Mercury": "personal",
    "Venus": "personal",
    "Mars": "personal",
    "Jupiter": "social",
    "Saturn": "social",
    "Uranus": "outer",
    "Neptune": "outer",
    "Pluto": "outer",
    "Node": "node",
}


def _plain_conv(name: str) -> str:
    return name.removeprefix("conv:")


def _plain_radix(name: str) -> str:
    return name.removeprefix("radix:")


def run_h3(aspects_csv=None, *, orb_max: float = 1.0) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    path = aspects_csv or (EARNINGS_OUTPUT / "converse_radix_aspects_all_events.csv")
    asp = pd.read_csv(path)
    dk = asp[(asp["radix_key"] == "DK") & (asp["best_aspect"] == "sq") & (asp["best_orb"] <= orb_max)].copy()
    dk["conv_planet"] = dk["from_body"].map(_plain_conv)
    dk["radix_planet"] = dk["to_body"].map(_plain_radix)
    dk["conv_class"] = dk["conv_planet"].map(CLASS_MAP)
    dk["radix_class"] = dk["radix_planet"].map(CLASS_MAP)

    by_event_src = (
        dk.groupby(["report_date", "conv_planet"])
        .size()
        .reset_index(name="sq_contacts")
    )
    by_event_tgt = (
        dk.groupby(["report_date", "radix_planet"])
        .size()
        .reset_index(name="sq_contacts")
    )

    src_totals = dk.groupby("conv_planet").size().reindex(BODIES, fill_value=0).reset_index(name="total_sq_hits")
    tgt_totals = dk.groupby("radix_planet").size().reindex(BODIES, fill_value=0).reset_index(name="total_sq_hits")

    class_src = dk.groupby("conv_class").size().reset_index(name="total_sq_hits")
    class_tgt = dk.groupby("radix_class").size().reset_index(name="total_sq_hits")

    pairs = (
        dk.groupby(["conv_planet", "radix_planet"])
        .agg(n=("best_orb", "count"), mean_orb=("best_orb", "mean"))
        .reset_index()
        .sort_values("n", ascending=False)
    )
    return (
        dk[
            [
                "report_date",
                "conv_planet",
                "radix_planet",
                "best_orb",
                "conv_class",
                "radix_class",
            ]
        ],
        pairs,
        pd.concat(
            [
                src_totals.assign(role="converse_source"),
                tgt_totals.assign(role="radix_target"),
                class_src.assign(role="converse_class"),
                class_tgt.assign(role="radix_class"),
            ],
            ignore_index=True,
        ),
    )
