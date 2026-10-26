"""Mine recurring converse configurations (exploratory)."""

from __future__ import annotations

from collections import Counter, defaultdict

import pandas as pd

from aspect_signatures import aspect_signature as _signature


def mine_configurations(
    aspects_df: pd.DataFrame,
    extreme_report_dates: set[str],
    *,
    orb_max: float = 1.0,
) -> pd.DataFrame:
    """Frequency of tight directed aspects in extreme vs all events."""
    tight = aspects_df[aspects_df["best_orb"] <= orb_max].copy()
    tight["signature"] = tight.apply(_signature, axis=1)
    tight["is_extreme"] = tight["report_date"].astype(str).isin(extreme_report_dates)

    rows = []
    for sig, grp in tight.groupby("signature"):
        total = len(grp)
        ext = int(grp["is_extreme"].sum())
        pos_dates = grp[grp["is_extreme"]]["report_date"].astype(str).tolist()
        rows.append(
            {
                "signature": sig,
                "count_all": total,
                "count_extreme": ext,
                "extreme_report_dates": ";".join(sorted(set(pos_dates))),
                "mean_orb": float(grp["best_orb"].mean()),
            }
        )
    out = pd.DataFrame(rows).sort_values(["count_extreme", "count_all"], ascending=False)
    return out


def compare_extreme_groups(
    aspects_df: pd.DataFrame,
    neg_dates: set[str],
    pos_dates: set[str],
    *,
    orb_max: float = 1.0,
) -> pd.DataFrame:
    tight = aspects_df[aspects_df["best_orb"] <= orb_max].copy()
    tight["signature"] = tight.apply(_signature, axis=1)
    tight["group"] = tight["report_date"].astype(str).map(
        lambda d: "neg" if d in neg_dates else ("pos" if d in pos_dates else "other")
    )
    rows = []
    for sig, grp in tight.groupby("signature"):
        c_neg = int((grp["group"] == "neg").sum())
        c_pos = int((grp["group"] == "pos").sum())
        c_other = int((grp["group"] == "other").sum())
        rows.append(
            {
                "signature": sig,
                "count_neg_extreme": c_neg,
                "count_pos_extreme": c_pos,
                "count_other_events": c_other,
                "neg_only": c_neg > 0 and c_pos == 0,
                "pos_only": c_pos > 0 and c_neg == 0,
            }
        )
    return pd.DataFrame(rows).sort_values(
        ["count_neg_extreme", "count_pos_extreme"], ascending=False
    )
