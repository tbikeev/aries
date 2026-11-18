"""BR-4 per-cell crash/rally differentials from controlled individual matrices."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from br3_schema import ASPECTS, BR3_TICKERS, LABELS, PLANETS, c2c_pair_planets
from br4_constants import MIN_POOLED_N_PER_TAIL, MIN_TICKER_N_PER_TAIL


def _safe_ratio(num: float, den: float) -> float:
    return float(num / den) if den > 0 else float("nan")


@dataclass
class LoadedControlled:
    c2c_active: np.ndarray
    c2c_power: np.ndarray
    c2r_active: np.ndarray
    c2r_power: np.ndarray
    eligible: np.ndarray
    manifest: pd.DataFrame
    neg_ei: np.ndarray
    pos_ei: np.ndarray
    discovery_ei: np.ndarray


def load_controlled(ind_path, manifest_path) -> LoadedControlled:
    z = np.load(ind_path)
    manifest = pd.read_parquet(manifest_path).sort_values("event_id").reset_index(drop=True)
    neg_ei = manifest.index[manifest["label"] == "NEG"].to_numpy()
    pos_ei = manifest.index[manifest["label"] == "POS"].to_numpy()
    disc = manifest.index[manifest["discovery_flag"] == True].to_numpy()  # noqa: E712
    return LoadedControlled(
        c2c_active=z["c2c_active"],
        c2c_power=z["c2c_power"],
        c2r_active=z["c2r_active"],
        c2r_power=z["c2r_power"],
        eligible=z["eligible"],
        manifest=manifest,
        neg_ei=neg_ei,
        pos_ei=pos_ei,
        discovery_ei=disc,
    )


def _pooled_stats(active: np.ndarray, power: np.ndarray, eligible: np.ndarray, eix: np.ndarray) -> tuple[int, int, float]:
    """Sum over tickers × events in eix."""
    N = 0
    n = 0
    s = 0.0
    for ei in eix:
        for ti in range(active.shape[0]):
            if not eligible[ti, ei]:
                continue
            N += 1
            if active[ti, ei]:
                n += 1
                s += float(power[ti, ei])
    return N, n, s


def _ticker_stats_2d(act2d: np.ndarray, pwr2d: np.ndarray, eligible: np.ndarray, eix: np.ndarray, ti: int) -> tuple[int, int, float]:
    N = n = 0
    s = 0.0
    for ei in eix:
        if not eligible[ti, ei]:
            continue
        N += 1
        if act2d[ti, ei]:
            n += 1
            s += float(pwr2d[ti, ei])
    return N, n, s


def _metrics(Nn, nn, sn, Np, np_, sp) -> dict:
    Fn = _safe_ratio(nn, Nn)
    Fp = _safe_ratio(np_, Np)
    Pn = _safe_ratio(sn, Nn)
    Pp = _safe_ratio(sp, Np)
    An = _safe_ratio(sn, nn)
    Ap = _safe_ratio(sp, np_)
    return {
        "N_neg": Nn,
        "n_neg": nn,
        "sum_power_neg": sn,
        "N_pos": Np,
        "n_pos": np_,
        "sum_power_pos": sp,
        "F_neg": Fn,
        "F_pos": Fp,
        "delta_F": Fn - Fp if np.isfinite(Fn) and np.isfinite(Fp) else float("nan"),
        "P_neg": Pn,
        "P_pos": Pp,
        "delta_P": Pn - Pp if np.isfinite(Pn) and np.isfinite(Pp) else float("nan"),
        "A_neg": An,
        "A_pos": Ap,
        "delta_A": An - Ap if np.isfinite(An) and np.isfinite(Ap) else float("nan"),
    }


def build_c2c_tables(data: LoadedControlled, *, exclude_discovery: bool = False) -> tuple[pd.DataFrame, pd.DataFrame]:
    neg_ei = data.neg_ei
    pos_ei = data.pos_ei
    if exclude_discovery and len(data.discovery_ei):
        neg_ei = neg_ei[~np.isin(neg_ei, data.discovery_ei)]
        pos_ei = pos_ei[~np.isin(pos_ei, data.discovery_ei)]

    pooled_rows = []
    ticker_rows = []
    ticker_deltas: dict[tuple, list[float]] = {}
    ticker_deltas_p: dict[tuple, list[float]] = {}

    for pk in range(55):
        p1, p2 = c2c_pair_planets(pk)
        for ak, asp in enumerate(ASPECTS):
            act2 = data.c2c_active[:, :, pk, ak]
            pwr2 = data.c2c_power[:, :, pk, ak]
            Nn, nn, sn = _pooled_stats(act2, pwr2, data.eligible, neg_ei)
            Np, np_, sp = _pooled_stats(act2, pwr2, data.eligible, pos_ei)
            m = _metrics(Nn, nn, sn, Np, np_, sp)
            m.update({"mode": "C2C", "planet_1": p1, "planet_2": p2, "aspect": asp, "pair_index": pk, "aspect_index": ak})

            deltas_f = []
            deltas_p = []
            n_tickers_ok = 0
            n_pos_df = n_neg_df = 0
            for ti, ticker in enumerate(BR3_TICKERS):
                tNn, tnn, tsn = _ticker_stats_2d(act2, pwr2, data.eligible, neg_ei, ti)
                tNp, tnp, tsp = _ticker_stats_2d(act2, pwr2, data.eligible, pos_ei, ti)
                tm = _metrics(tNn, tnn, tsn, tNp, tnp, tsp)
                ticker_rows.append(
                    {
                        "mode": "C2C",
                        "ticker": ticker,
                        "planet_1": p1,
                        "planet_2": p2,
                        "aspect": asp,
                        **{k: tm[k] for k in tm if k.startswith(("N_", "n_", "sum_", "F_", "P_", "A_", "delta_"))},
                    }
                )
                if tNn >= MIN_TICKER_N_PER_TAIL and tNp >= MIN_TICKER_N_PER_TAIL:
                    n_tickers_ok += 1
                    if np.isfinite(tm["delta_F"]):
                        deltas_f.append(tm["delta_F"])
                        if tm["delta_F"] > 0:
                            n_pos_df += 1
                        elif tm["delta_F"] < 0:
                            n_neg_df += 1
                    if np.isfinite(tm["delta_P"]):
                        deltas_p.append(tm["delta_P"])

            m["equal_company_delta_F"] = float(np.nanmean(deltas_f)) if deltas_f else float("nan")
            m["equal_company_delta_P"] = float(np.nanmean(deltas_p)) if deltas_p else float("nan")
            m["n_tickers_sufficient_both_tails"] = n_tickers_ok
            m["n_tickers_delta_F_positive"] = n_pos_df
            m["n_tickers_delta_F_negative"] = n_neg_df
            m["median_ticker_delta_F"] = float(np.median(deltas_f)) if deltas_f else float("nan")
            m["median_ticker_delta_P"] = float(np.median(deltas_p)) if deltas_p else float("nan")
            m["ranking_eligible"] = Nn >= MIN_POOLED_N_PER_TAIL and Np >= MIN_POOLED_N_PER_TAIL
            pooled_rows.append(m)

    return pd.DataFrame(pooled_rows), pd.DataFrame(ticker_rows)


def build_c2r_tables(data: LoadedControlled, *, exclude_discovery: bool = False) -> tuple[pd.DataFrame, pd.DataFrame]:
    neg_ei = data.neg_ei
    pos_ei = data.pos_ei
    if exclude_discovery and len(data.discovery_ei):
        neg_ei = neg_ei[~np.isin(neg_ei, data.discovery_ei)]
        pos_ei = pos_ei[~np.isin(pos_ei, data.discovery_ei)]

    pooled_rows = []
    ticker_rows = []
    for ci, cp in enumerate(PLANETS):
        for ri, rp in enumerate(PLANETS):
            for ak, asp in enumerate(ASPECTS):
                act2 = data.c2r_active[:, :, ci, ri, ak]
                pwr2 = data.c2r_power[:, :, ci, ri, ak]
                Nn, nn, sn = _pooled_stats(act2, pwr2, data.eligible, neg_ei)
                Np, np_, sp = _pooled_stats(act2, pwr2, data.eligible, pos_ei)
                m = _metrics(Nn, nn, sn, Np, np_, sp)
                m.update(
                    {
                        "mode": "C2R",
                        "converse_planet": cp,
                        "radix_planet": rp,
                        "aspect": asp,
                        "converse_index": ci,
                        "radix_index": ri,
                        "aspect_index": ak,
                    }
                )
                deltas_f = []
                deltas_p = []
                n_tickers_ok = n_pos_df = n_neg_df = 0
                for ti, ticker in enumerate(BR3_TICKERS):
                    tNn, tnn, tsn = _ticker_stats_2d(act2, pwr2, data.eligible, neg_ei, ti)
                    tNp, tnp, tsp = _ticker_stats_2d(act2, pwr2, data.eligible, pos_ei, ti)
                    tm = _metrics(tNn, tnn, tsn, tNp, tnp, tsp)
                    ticker_rows.append(
                        {
                            "mode": "C2R",
                            "ticker": ticker,
                            "converse_planet": cp,
                            "radix_planet": rp,
                            "aspect": asp,
                            **{k: tm[k] for k in tm if k.startswith(("N_", "n_", "sum_", "F_", "P_", "A_", "delta_"))},
                        }
                    )
                    if tNn >= MIN_TICKER_N_PER_TAIL and tNp >= MIN_TICKER_N_PER_TAIL:
                        n_tickers_ok += 1
                        if np.isfinite(tm["delta_F"]):
                            deltas_f.append(tm["delta_F"])
                            if tm["delta_F"] > 0:
                                n_pos_df += 1
                            elif tm["delta_F"] < 0:
                                n_neg_df += 1
                        if np.isfinite(tm["delta_P"]):
                            deltas_p.append(tm["delta_P"])

                m["equal_company_delta_F"] = float(np.nanmean(deltas_f)) if deltas_f else float("nan")
                m["equal_company_delta_P"] = float(np.nanmean(deltas_p)) if deltas_p else float("nan")
                m["n_tickers_sufficient_both_tails"] = n_tickers_ok
                m["n_tickers_delta_F_positive"] = n_pos_df
                m["n_tickers_delta_F_negative"] = n_neg_df
                m["median_ticker_delta_F"] = float(np.median(deltas_f)) if deltas_f else float("nan")
                m["median_ticker_delta_P"] = float(np.median(deltas_p)) if deltas_p else float("nan")
                m["ranking_eligible"] = Nn >= MIN_POOLED_N_PER_TAIL and Np >= MIN_POOLED_N_PER_TAIL
                pooled_rows.append(m)

    return pd.DataFrame(pooled_rows), pd.DataFrame(ticker_rows)
