"""Virtual sensors: what each salinity station *should* read, from its neighbors and the rivers.

One set of LightGBM quantile models (5th, 50th, 95th percentile) per salinity station, using
same-day salinity at the other live stations, river flow (today, 7- and 30-day means), basin rain
and season. Missing inputs are fine: LightGBM learns what to do when a neighbor is offline.

Used three ways:
  - QC: a live reading outside the expected range on 2 of the last 3 days is flagged suspect
    ("doesn't match nearby stations") and can't trigger alerts.
  - Gap fill: retired or quiet stations show a labeled estimate with a likely range.
  - Charts: an "expected from neighbors" line shows when a sensor drifted.

Evidence (Gulfport Light test, 2021-2024): ~2.9 ppt typical error vs 6.7 for averaging neighbors.
Each training run re-measures this on the most recent two years and records it in virtual.json.
"""
from __future__ import annotations

import json
import logging
import re

import numpy as np
import pandas as pd

from ..config import Region
from ..indicators import is_suspect

log = logging.getLogger(__name__)
QUANTILES = {"q05": 0.05, "q50": 0.5, "q95": 0.95}
HOLDOUT_DAYS = 730
MIN_TRAIN = 800
MARGIN = 0.5           # ppt of slack beyond the 98% range before calling a reading suspect
MAX_MAE_FOR_ESTIMATE = 3.5   # don't publish an estimate for a station the model can't predict well
PARAMS = dict(learning_rate=0.03, num_leaves=15, min_data_in_leaf=40, feature_fraction=0.8,
              bagging_fraction=0.8, bagging_freq=1, verbose=-1, seed=7)
ROUNDS = 500


def _dir(region: Region):
    d = region.data_dir / "models"
    d.mkdir(parents=True, exist_ok=True)
    return d


def salinity_sites(region: Region) -> list[dict]:
    return [s for s in region.sites if "salinity" in s["vars"] and s["kind"] in ("sound", "estuary")]


def _wide(daily: pd.DataFrame) -> pd.DataFrame:
    d = daily[daily["var"].isin(["salinity", "flow", "rain", "wind_u", "wind_v", "wind_max"])]
    w = d.pivot_table(index="date", columns=["site", "var"], values="value").sort_index()
    return w.asfreq("D") if len(w) else w


def _k(prefix: str, site_id: str) -> str:
    """LightGBM-safe feature name."""
    return f"{prefix}_{re.sub(r'[^A-Za-z0-9]', '_', site_id)}"


def features(region: Region, wide: pd.DataFrame, target: str) -> pd.DataFrame:
    X = pd.DataFrame(index=wide.index)
    for s in salinity_sites(region):
        if s["id"] == target or s.get("retired"):       # retired stations are never inputs (they're gone)
            continue
        col = (s["id"], "salinity")
        if col in wide:
            v = wide[col]
            X[_k("sal", s["id"])] = v.where(~v.apply(lambda x: is_suspect("salinity", x) if pd.notna(x) else False))
    for s in region.sites_by(kind="river"):
        col = (s["id"], "flow")
        if col in wide:
            q = np.log10(wide[col].clip(lower=1))
            X[_k("q", s["id"])] = q
            X[_k("q7", s["id"])] = q.rolling(7, min_periods=4).mean()
            X[_k("q30", s["id"])] = q.rolling(30, min_periods=15).mean()
    for s in region.sites_by(kind="rain"):
        col = (s["id"], "rain")
        if col in wide:
            r = wide[col]
            X[_k("r7", s["id"])] = r.rolling(7, min_periods=7).sum()
            X[_k("r30", s["id"])] = r.rolling(30, min_periods=30).sum()
    # Wind moves the Sound (see docs/feasibility.md, "ML experiments"): today's and recent days' wind.
    for s in region.sites_by(kind="wind"):
        if (s["id"], "wind_u") in wide and (s["id"], "wind_v") in wide:
            u, v = wide[(s["id"], "wind_u")], wide[(s["id"], "wind_v")]
            X[_k("wu", s["id"])], X[_k("wv", s["id"])] = u, v
            X[_k("wu3", s["id"])] = u.rolling(3, min_periods=2).mean()
            X[_k("wv3", s["id"])] = v.rolling(3, min_periods=2).mean()
            X[_k("wv7", s["id"])] = v.rolling(7, min_periods=5).mean()
        if (s["id"], "wind_max") in wide:
            X[_k("wmax", s["id"])] = wide[(s["id"], "wind_max")]
    doy = X.index.dayofyear
    X["doy_sin"] = np.sin(2 * np.pi * doy / 365.25)
    X["doy_cos"] = np.cos(2 * np.pi * doy / 365.25)
    return X


def _fit(X, y, q):
    import lightgbm as lgb
    return lgb.train({**PARAMS, "objective": "quantile", "alpha": q}, lgb.Dataset(X, y), ROUNDS)


def train(region: Region, daily: pd.DataFrame) -> dict:
    wide = _wide(daily)
    out, meta = _dir(region), {}
    for site in salinity_sites(region):
        sid = site["id"]
        if (sid, "salinity") not in wide:
            continue
        X = features(region, wide, sid)
        y = wide[(sid, "salinity")]
        ok = y.notna() & ~y.apply(lambda v: is_suspect("salinity", v) if pd.notna(v) else False)
        ok &= X.drop(columns=["doy_sin", "doy_cos"]).notna().sum(axis=1) >= 2   # need some real inputs
        X, y = X[ok], y[ok]
        if len(y) < MIN_TRAIN:
            log.warning("virtual %s: only %d training days, skipped", sid, len(y))
            continue
        # Honest score first: train on everything before the last two years of this station's data.
        cut = y.index.max() - pd.Timedelta(days=HOLDOUT_DAYS)
        tr, te = y.index <= cut, y.index > cut
        metrics = {}
        if te.sum() >= 60 and tr.sum() >= MIN_TRAIN:
            preds = {k: _fit(X[tr], y[tr], q).predict(X[te]) for k, q in QUANTILES.items()}
            yt = y[te].values
            nb = X[te].filter(like="sal_").mean(axis=1).values          # naive: average of neighbors
            # Conformalized quantile regression: how far outside its raw range reality fell on the
            # held-out years. Widening by these amounts gives ranges that actually cover 90% / 98%.
            score = np.maximum(preds["q05"] - yt, yt - preds["q95"])
            c90, c98 = (float(np.quantile(score, q)) for q in (0.90, 0.98))
            metrics = {
                "test_from": str(y.index[te].min().date()), "test_to": str(y.index[te].max().date()),
                "n_test": int(te.sum()),
                "mae": round(float(np.mean(np.abs(preds["q50"] - yt))), 2),
                "mae_neighbors_avg": round(float(np.nanmean(np.abs(nb - yt))), 2),
                "raw_coverage_90": round(float(np.mean((yt >= preds["q05"]) & (yt <= preds["q95"]))), 2),
                "widen_90": round(max(c90, 0.0), 2),
                "widen_98": round(max(c98, 0.0), 2),
            }
        for k, q in QUANTILES.items():                                    # then refit on everything
            _fit(X, y, q).save_model(str(out / f"virtual-{sid}-{k}.txt"))
        meta[sid] = {"features": list(X.columns), "n_train": int(len(y)),
                     "publish_estimate": bool(metrics) and metrics["mae"] <= MAX_MAE_FOR_ESTIMATE,
                     "trained_through": str(y.index.max().date()), "metrics": metrics}
        log.info("virtual %s: %s", sid, metrics or "trained (too little recent data to score)")
    (out / "virtual.json").write_text(json.dumps(meta, indent=2))
    return meta


def predict(region: Region, daily: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    """Expected salinity (q05/q50/q95) per station per day in [start, end]. Empty if no models."""
    import lightgbm as lgb
    d = region.data_dir / "models"
    if not (d / "virtual.json").exists():
        return pd.DataFrame()
    meta = json.loads((d / "virtual.json").read_text())
    wide = _wide(daily[daily.date >= start - pd.Timedelta(days=40)])
    wide = wide.reindex(pd.date_range(min(wide.index.min(), start), end, freq="D"))
    rows = []
    for sid, m in meta.items():
        X = features(region, wide, sid).reindex(columns=m["features"])
        X = X.loc[start:end]
        has = X.drop(columns=["doy_sin", "doy_cos"], errors="ignore").notna().sum(axis=1) >= 2
        X = X[has]
        if X.empty:
            continue
        p = {k: lgb.Booster(model_file=str(d / f"virtual-{sid}-{k}.txt")).predict(X) for k in QUANTILES}
        lo = np.minimum.reduce([p["q05"], p["q50"], p["q95"]])
        hi = np.maximum.reduce([p["q05"], p["q50"], p["q95"]])
        met = m.get("metrics") or {}
        w90, w98 = met.get("widen_90", 2.0), met.get("widen_98", 4.0)   # unscored models: generous defaults
        rows.append(pd.DataFrame({"site": sid, "date": X.index, "q50": np.clip(p["q50"], 0, None),
                                  "lo90": np.clip(lo - w90, 0, None), "hi90": hi + w90,
                                  "lo98": np.clip(lo - w98, 0, None), "hi98": hi + w98,
                                  "publish": bool(m.get("publish_estimate")), "mae": met.get("mae")}))
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def qc(region: Region, daily: pd.DataFrame, expected: pd.DataFrame, asof: pd.Timestamp) -> dict:
    """Per station: latest expected range, and whether the live reading is suspect."""
    out = {}
    if expected.empty:
        return out
    for site in salinity_sites(region):
        sid = site["id"]
        e = expected[expected.site == sid].set_index("date").sort_index()
        e = e[e.index <= asof]
        if e.empty:
            continue
        last = e.iloc[-1]
        info = {"date": e.index[-1].strftime("%Y-%m-%d"), "q50": float(last.q50),
                "lo90": float(last.lo90), "hi90": float(last.hi90), "publish": bool(last.publish),
                "mae": last.mae, "suspect": False}
        obs = daily[(daily.site == sid) & (daily["var"] == "salinity")].set_index("date")["value"]
        recent = obs[obs.index > asof - pd.Timedelta(days=3)].sort_index()
        if len(recent):
            joined = pd.concat([recent, e], axis=1, join="inner")
            outside = (joined["value"] < joined.lo98 - MARGIN) | (joined["value"] > joined.hi98 + MARGIN)
            if len(joined) >= 2 and outside.sum() >= 2:
                info["suspect"] = True
                info["direction"] = "high" if joined["value"].iloc[-1] > joined.q50.iloc[-1] else "low"
        out[sid] = info
    return out
