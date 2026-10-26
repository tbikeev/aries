"""Activation episodes for slow-body converse signatures on the daily calendar."""

from __future__ import annotations

import pandas as pd


def build_activation_episodes(
    slow_active: pd.DataFrame,
    session_order: list[str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Group consecutive trading sessions with the same signature active.

    Returns episode table and session-level episode count / min-orb summary.
    """
    if slow_active.empty:
        return pd.DataFrame(), pd.DataFrame()
    order_idx = {s: i for i, s in enumerate(session_order)}
    slow_active = slow_active.copy()
    slow_active["ord"] = slow_active["session"].map(order_idx)
    slow_active = slow_active.dropna(subset=["ord"]).sort_values(["signature", "ord"])

    ep_rows: list[dict] = []
    ep_id = 0
    for sig, grp in slow_active.groupby("signature"):
        dates = grp.sort_values("ord")["session"].tolist()
        ords = grp.sort_values("ord")["ord"].tolist()
        orbs = grp.sort_values("ord")["best_orb"].tolist()
        start_i = 0
        for j in range(1, len(ords) + 1):
            if j == len(ords) or ords[j] != ords[j - 1] + 1:
                run_dates = dates[start_i:j]
                run_orbs = orbs[start_i:j]
                ep_id += 1
                ep_rows.append(
                    {
                        "episode_id": ep_id,
                        "signature": sig,
                        "start_session": run_dates[0],
                        "end_session": run_dates[-1],
                        "duration_sessions": len(run_dates),
                        "min_orb_deg": float(min(run_orbs)),
                        "mean_orb_deg": float(sum(run_orbs) / len(run_orbs)),
                    }
                )
                start_i = j

    ep_df = pd.DataFrame(ep_rows)
    sess_rows = []
    for _, ep in ep_df.iterrows():
        # expand not needed for summary; count episodes touching session via merge
        pass
    # Per session: how many slow episodes active, best (min) orb
    per = slow_active.groupby("session").agg(
        slow_sig_active_count=("signature", "nunique"),
        slow_min_orb=("best_orb", "min"),
    )
    per = per.reset_index()
    n_episodes = len(ep_df)
    return ep_df, per
