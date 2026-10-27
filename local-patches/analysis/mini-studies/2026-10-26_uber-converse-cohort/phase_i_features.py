"""Aggregate Par/Cpar event features (Phase I-B)."""

from __future__ import annotations

import pandas as pd

from phase_i_paths import DECL_ORB_EXACT, DECL_ORB_PRIMARY, DECL_ORB_SECONDARY


def aggregate_declination_features(decl_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (rd, rk), grp in decl_df.groupby(["report_date", "radix_key"]):
        row = {"report_date": rd, "radix_key": rk}
        for orb, tag in (
            (DECL_ORB_PRIMARY, "orb05"),
            (DECL_ORB_SECONDARY, "orb10"),
        ):
            sub = grp[grp["decl_orb_deg"] <= orb + 1e-12]
            par = sub[sub["decl_aspect"] == "par"]
            cpar = sub[sub["decl_aspect"] == "cpar"]
            row[f"{rk}_par_count_{tag}"] = len(par)
            row[f"{rk}_cpar_count_{tag}"] = len(cpar)
            row[f"{rk}_decl_total_{tag}"] = len(sub)
            row[f"{rk}_decl_min_orb_{tag}"] = float(sub["decl_orb_deg"].min()) if len(sub) else None
        exact = grp[grp["decl_orb_deg"] <= DECL_ORB_EXACT + 1e-12]
        row[f"{rk}_decl_exact_15arcmin_count"] = len(exact)
        rows.append(row)
    wide = pd.DataFrame(rows)
    # Pivot cohort columns to one row per report_date
    out = None
    for rk in ("FT", "INC", "DK"):
        sub = wide[wide["radix_key"] == rk].drop(columns=["radix_key"])
        cols = [c for c in sub.columns if c.startswith(f"{rk}_")]
        sub = sub[["report_date"] + cols]
        out = sub if out is None else out.merge(sub, on="report_date", how="outer")
    return out.sort_values("report_date")


def merge_feature_matrix(decl_feat: pd.DataFrame, panel: pd.DataFrame) -> pd.DataFrame:
    return panel.merge(decl_feat, on="report_date", how="inner")
