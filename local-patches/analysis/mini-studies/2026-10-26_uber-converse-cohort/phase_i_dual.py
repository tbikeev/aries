"""Two-coordinate reinforcement (Phase I-C)."""

from __future__ import annotations

import pandas as pd

from phase_i_paths import DUAL_DECL_ORB, LON_ORB_PRIMARY, LON_ORB_TIGHT


def _plain(name: str) -> str:
    return name.replace("conv:", "").replace("radix:", "")


def build_dual_contacts(
    aspects_df: pd.DataFrame,
    decl_df: pd.DataFrame,
    *,
    lon_orb: float = LON_ORB_PRIMARY,
    decl_orb: float = DUAL_DECL_ORB,
) -> pd.DataFrame:
    asp = aspects_df[aspects_df["best_orb"] <= lon_orb].copy()
    asp["conv_p"] = asp["from_body"].map(_plain)
    asp["radix_p"] = asp["to_body"].map(_plain)
    dcl = decl_df[decl_df["decl_orb_deg"] <= decl_orb].copy()
    asp_keys = asp.assign(
        conv_p=asp["from_body"].map(_plain),
        radix_p=asp["to_body"].map(_plain),
    )
    dcl_keys = dcl.rename(columns={"conv_body": "conv_p", "radix_body": "radix_p"})
    merged = asp_keys.merge(
        dcl_keys,
        on=["report_date", "radix_key", "conv_p", "radix_p"],
        how="inner",
        suffixes=("_lon", "_decl"),
    )
    rows = []
    for _, r in merged.iterrows():
        rows.append(
            {
                "report_date": r["report_date"],
                "radix_key": r["radix_key"],
                "conv_body": r["conv_p"],
                "radix_body": r["radix_p"],
                "lon_aspect": r["best_aspect"],
                "lon_orb_deg": r["best_orb"],
                "decl_aspect": r["decl_aspect"],
                "decl_orb_deg": r["decl_orb_deg"],
            }
        )
    return pd.DataFrame(rows)


def dual_event_features(dual_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (rd, rk), grp in dual_df.groupby(["report_date", "radix_key"]):
        rows.append(
            {
                "report_date": rd,
                "radix_key": rk,
                f"{rk}_double_activation_count": len(grp),
                f"{rk}_double_par_count": int((grp["decl_aspect"] == "par").sum()),
                f"{rk}_double_cpar_count": int((grp["decl_aspect"] == "cpar").sum()),
                f"{rk}_double_lon_sq_count": int((grp["lon_aspect"] == "sq").sum()),
                f"{rk}_double_lon_soft_count": int(grp["lon_aspect"].isin(["tri", "sext"]).sum()),
                f"{rk}_has_double_activation": int(len(grp) > 0),
            }
        )
    if not rows:
        return pd.DataFrame()
    wide = pd.DataFrame(rows)
    out = None
    for rk in ("FT", "INC", "DK"):
        sub = wide[wide["radix_key"] == rk]
        cols = [c for c in sub.columns if c.startswith(f"{rk}_")]
        sub = sub[["report_date"] + cols]
        out = sub if out is None else out.merge(sub, on="report_date", how="outer")
    return out.fillna(0)
