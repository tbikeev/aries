"""Rank extreme earnings reactions (close-to-close)."""

from __future__ import annotations

import pandas as pd

from market_reactions import EarningsReaction


def valid_reactions(reactions: list[EarningsReaction]) -> list[EarningsReaction]:
    return [
        r
        for r in reactions
        if not r.excluded and r.r_cc_pct is not None and r.reaction_session is not None
    ]


def top_extremes(
    reactions: list[EarningsReaction],
    *,
    top_negative: int = 10,
    top_positive: int = 10,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    valid = valid_reactions(reactions)
    df = pd.DataFrame([r.__dict__ for r in valid])
    df = df.sort_values("report_date")
    ranked = df.sort_values("r_cc_pct")
    neg = ranked.head(min(top_negative, len(ranked))).copy()
    neg["rank"] = range(1, len(neg) + 1)
    pos = ranked.tail(min(top_positive, len(ranked))).copy()
    pos = pos.sort_values("r_cc_pct", ascending=False).reset_index(drop=True)
    pos["rank"] = range(1, len(pos) + 1)
    return neg, pos, df
