"""Active-window analysis for slow-moving converse aspects across earnings events."""

from __future__ import annotations

import pandas as pd

from aspect_signatures import add_signature_column, plain_converse_body
from market_reactions import report_date_key

SLOW_CONVERS_BODIES = frozenset({"Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"})


def earnings_chronology(aspects_df: pd.DataFrame) -> list[str]:
    dates = sorted({report_date_key(d) for d in aspects_df["report_date"].unique()})
    return dates


def aspect_active_at_events(
    aspects_df: pd.DataFrame,
    *,
    orb_max: float = 1.0,
) -> pd.DataFrame:
    """One row per (signature, report_date) when aspect is within orb at converse time."""
    tight = aspects_df[aspects_df["best_orb"] <= orb_max].copy()
    tight = add_signature_column(tight)
    tight["report_date"] = tight["report_date"].map(report_date_key)
    return tight[
        [
            "signature",
            "report_date",
            "radix_key",
            "from_body",
            "to_body",
            "best_aspect",
            "best_orb",
        ]
    ].drop_duplicates(subset=["signature", "report_date"])


def consecutive_earnings_runs(
    chronology: list[str],
    active_dates: set[str],
) -> list[tuple[str, str, int, list[str]]]:
    """Runs of consecutive earnings quarters where signature is active."""
    runs: list[tuple[str, str, int, list[str]]] = []
    buf: list[str] = []
    for d in chronology:
        if d in active_dates:
            buf.append(d)
        else:
            if buf:
                runs.append((buf[0], buf[-1], len(buf), list(buf)))
                buf = []
    if buf:
        runs.append((buf[0], buf[-1], len(buf), list(buf)))
    return runs


def persistence_summary(
    aspects_df: pd.DataFrame,
    *,
    orb_max: float = 1.0,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Returns:
      - run_table: one row per active run on the earnings calendar
      - signature_summary: counts events vs independent runs; slow-body flag
    """
    chron = earnings_chronology(aspects_df)
    active = aspect_active_at_events(aspects_df, orb_max=orb_max)
    run_rows: list[dict] = []
    summary_rows: list[dict] = []

    for sig, grp in active.groupby("signature"):
        dates = set(grp["report_date"])
        runs = consecutive_earnings_runs(chron, dates)
        sample = grp.iloc[0]
        slow = plain_converse_body(str(sample["from_body"])) in SLOW_CONVERS_BODIES
        for start, end, length, members in runs:
            run_rows.append(
                {
                    "signature": sig,
                    "run_start": start,
                    "run_end": end,
                    "quarters_in_run": length,
                    "report_dates": ";".join(members),
                    "slow_converse_body": slow,
                    "mean_orb_in_run": float(
                        grp[grp["report_date"].isin(members)]["best_orb"].mean()
                    ),
                }
            )
        summary_rows.append(
            {
                "signature": sig,
                "radix_key": sample["radix_key"],
                "converse_body": plain_converse_body(str(sample["from_body"])),
                "radix_body": str(sample["to_body"]).removeprefix("radix:"),
                "aspect": sample["best_aspect"],
                "slow_converse_body": slow,
                "event_hits": len(dates),
                "independent_runs": len(runs),
                "max_run_length_quarters": max((r[2] for r in runs), default=0),
                "all_report_dates": ";".join(sorted(dates)),
            }
        )

    run_df = pd.DataFrame(run_rows).sort_values(
        ["quarters_in_run", "signature"], ascending=[False, True]
    )
    sum_df = pd.DataFrame(summary_rows).sort_values(
        ["event_hits", "max_run_length_quarters"], ascending=False
    )
    return run_df, sum_df


def flagged_outer_planet_signatures(summary_df: pd.DataFrame, min_hits: int = 3) -> pd.DataFrame:
    """Signatures where multiple hits likely reflect one prolonged window (runs < hits)."""
    if summary_df.empty:
        return summary_df
    out = summary_df[
        (summary_df["slow_converse_body"])
        & (summary_df["event_hits"] >= min_hits)
        & (summary_df["independent_runs"] < summary_df["event_hits"])
    ].copy()
    out["persistence_ratio"] = out["independent_runs"] / out["event_hits"]
    return out.sort_values("event_hits", ascending=False)
