"""Cache DK declination counts for daily panel (ordinary-day specificity)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from daily_market import build_daily_panel, session_open_utc_fixed
from earnings_converse import event_jd_from_datetime
from earnings_paths import DAILY_OUTPUT, resolve_ohlc_csv
from market_reactions import load_ohlc_csv
from phase_i_paths import DECL_ORB_PRIMARY
from phase_i_placebos import dk_decl_features_for_birth_jd
from radix import RADIX_COHORT


def build_daily_dk_decl_cache(path: Path, *, progress_every: int = 300) -> pd.DataFrame:
    ohlc = load_ohlc_csv(resolve_ohlc_csv())
    panel = build_daily_panel(ohlc)
    bjd = RADIX_COHORT["DK"].birth_jd
    rows = []
    for i, rec in panel.iterrows():
        sess = date.fromisoformat(str(rec["session"])[:10])
        ejd = event_jd_from_datetime(session_open_utc_fixed(sess))
        c = dk_decl_features_for_birth_jd(bjd, ejd, orb=DECL_ORB_PRIMARY)
        rows.append({"session": rec["session"], "DK_par": c["par"], "DK_cpar": c["cpar"], "DK_decl_total": c["total"]})
        if progress_every and len(rows) % progress_every == 0:
            print(f"daily dk decl cache: {len(rows)}/{len(panel)}", flush=True)
    df = pd.DataFrame(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    return df
