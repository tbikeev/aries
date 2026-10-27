"""Load frozen 26-event earnings panel for Phase H."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from earnings_paths import EARNINGS_OUTPUT
from feature_reduction import build_event_feature_matrix
from market_reactions import report_date_key


def load_earnings_panel(
    reactions_csv: Path | None = None,
    aspects_csv: Path | None = None,
) -> pd.DataFrame:
    react_path = reactions_csv or (EARNINGS_OUTPUT / "earnings_reactions_all.csv")
    asp_path = aspects_csv or (EARNINGS_OUTPUT / "converse_radix_aspects_all_events.csv")
    react = pd.read_csv(react_path)
    react = react[~react["excluded"].astype(bool)].copy()
    react["report_date"] = react["report_date"].map(report_date_key)
    aspects = pd.read_csv(asp_path)
    feat05 = build_event_feature_matrix(aspects, orb_max=0.5)
    feat10 = build_event_feature_matrix(aspects, orb_max=1.0)
    for rk in ("FT", "INC", "DK"):
        feat05 = feat05.rename(
            columns={
                f"{rk}_sq_count": f"{rk}_sq_count_orb05",
                f"{rk}_tight_count": f"{rk}_tight_count_orb05",
            }
        )
        feat10 = feat10.rename(
            columns={
                f"{rk}_sq_count": f"{rk}_sq_count_orb10",
                f"{rk}_tight_count": f"{rk}_tight_count_orb10",
            }
        )
    feat05 = feat05.rename(columns={"tight_aspect_count": "tight_aspect_count_orb05"})
    feat10 = feat10.rename(columns={"tight_aspect_count": "tight_aspect_count_orb10"})
    cols05 = [c for c in feat05.columns if c.endswith("_orb05")]
    cols10 = [c for c in feat10.columns if c.endswith("_orb10")]
    feat = feat05[["report_date"] + cols05].merge(
        feat10[["report_date"] + cols10], on="report_date", how="inner"
    )
    df = react.merge(feat, on="report_date", how="inner")
    df["abs_r_gap_pct"] = df["r_gap_pct"].abs()
    df["abs_r_intra_pct"] = df["r_intra_pct"].abs()
    df["abs_r_cc_pct"] = df["r_cc_pct"].abs()
    # Decomposition check (compound return identity).
    compound = (1 + df["r_gap_pct"] / 100) * (1 + df["r_intra_pct"] / 100) - 1
    df["r_cc_reconstructed_pct"] = compound * 100
    df["cc_identity_err_bps"] = (df["r_cc_pct"] - df["r_cc_reconstructed_pct"]).abs()
    return df.sort_values("report_date")


def event_jd_series(df: pd.DataFrame) -> list[tuple[str, float]]:
    from earnings_converse import event_jd_from_datetime

    out: list[tuple[str, float]] = []
    for _, row in df.iterrows():
        dt = datetime.fromisoformat(str(row["event_datetime_utc"]).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        out.append((str(row["report_date"]), event_jd_from_datetime(dt)))
    return out
