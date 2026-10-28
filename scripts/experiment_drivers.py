#!/usr/bin/env python3
"""
Experiment: do the Mississippi River and wind give salinity forecasts an edge over persistence?

Earlier result (docs/feasibility.md, chat 2026-10-28): with only our two rivers, gradient-boosted
models never beat "salinity stays where it is today", even when handed the TRUE future river flow.
Hypothesis: the missing drivers are the Mississippi River (via Bonnet Carre / Lake Borgne) and wind.

This pulls (once, cached in data/raw/):
  - Mississippi River at Baton Rouge (USGS 07374000), daily flow, 1998-present
  - Daily wind at mid-Sound (30.25N, 89.0W) from the Open-Meteo ERA5 archive: mean east/north
    components and max speed
and re-runs the 1/3/7/14-day forecast test for Merrill Shell, Back Bay and Round Island:
  persistence | model with our rivers | + Mississippi | + wind | + both | + both with TRUE future
  wind (an oracle: the most a wind forecast could ever add).

Train through 2018, test 2019-2026. Scores are MAE in ppt; "event" columns are days below 8 ppt.

Run from the repo root after `python -m msc backfill`:
    pip install -r requirements-dev.txt
    python scripts/experiment_drivers.py
"""
from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
warnings.filterwarnings("ignore")

from msc import store                       # noqa: E402
from msc.config import REFERENCE, load_region  # noqa: E402

RAW = REFERENCE / "raw"
RAW.mkdir(parents=True, exist_ok=True)
MISS = "07374000"
WIND_PT = (30.25, -89.0)
SITES = {"Merrill Shell": "USGS-301429089145600", "Back Bay": "USGS-302318088512600", "Round Island": "USGS-301849088350000"}
RIVERS = {"pearl": "USGS-02489500", "pasc": "USGS-02479000"}


def mississippi() -> pd.Series:
    cache = RAW / f"miss_{MISS}.json"
    if not cache.exists():
        import requests
        r = requests.get("https://waterservices.usgs.gov/nwis/dv/", timeout=300, params={
            "format": "json", "sites": MISS, "parameterCd": "00060", "statCd": "00003",
            "startDT": "1998-01-01", "endDT": pd.Timestamp.today().strftime("%Y-%m-%d")})
        r.raise_for_status()
        cache.write_text(r.text)
    ts = json.loads(cache.read_text())["value"]["timeSeries"][0]["values"][0]["value"]
    s = pd.Series([float(v["value"]) for v in ts], index=pd.to_datetime([v["dateTime"][:10] for v in ts]))
    return s.where(s > 0)


def wind() -> pd.DataFrame:
    cache = RAW / "wind_era5_midsound.json"
    if not cache.exists():
        import requests
        r = requests.get("https://archive-api.open-meteo.com/v1/archive", timeout=300, params={
            "latitude": WIND_PT[0], "longitude": WIND_PT[1], "start_date": "1998-01-01",
            "end_date": (pd.Timestamp.today() - pd.Timedelta(days=7)).strftime("%Y-%m-%d"),
            "hourly": "wind_speed_10m,wind_direction_10m", "wind_speed_unit": "ms", "timezone": "America/Chicago"})
        r.raise_for_status()
        cache.write_text(r.text)
    h = json.loads(cache.read_text())["hourly"]
    df = pd.DataFrame({"spd": h["wind_speed_10m"], "dir": h["wind_direction_10m"]}, index=pd.to_datetime(h["time"]))
    rad = np.radians(df["dir"])
    df["u"] = -df.spd * np.sin(rad)   # wind blowing toward the east is +u
    df["v"] = -df.spd * np.cos(rad)   # toward the north (onshore here) is +v
    return df.resample("D").agg({"u": "mean", "v": "mean", "spd": "max"})


def main():
    import lightgbm as lgb
    r = load_region("ms")
    d = store.read_daily(r)
    W = d.pivot_table(index="date", columns=["site", "var"], values="value").asfreq("D")
    col = lambda s, v: W[(s, v)] if (s, v) in W else pd.Series(np.nan, index=W.index)
    lq = lambda s: np.log10(s.clip(lower=1))

    base = pd.DataFrame(index=W.index)
    for nm, sid in RIVERS.items():
        q = lq(col(sid, "flow"))
        base[f"{nm}_q"], base[f"{nm}_q7"], base[f"{nm}_q30"] = q, q.rolling(7).mean(), q.rolling(30).mean()
        base[f"{nm}_dq7"] = q - q.shift(7)
    doy = W.index.dayofyear
    base["doy_s"], base["doy_c"] = np.sin(2 * np.pi * doy / 365.25), np.cos(2 * np.pi * doy / 365.25)

    m = lq(mississippi()).reindex(W.index)
    miss = pd.DataFrame({"miss_q": m, "miss_q7": m.rolling(7).mean(), "miss_q30": m.rolling(30).mean(),
                         "miss_dq7": m - m.shift(7)}, index=W.index)
    w = wind().reindex(W.index)
    wnd = pd.DataFrame({"u": w.u, "v": w.v, "spd": w.spd, "u3": w.u.rolling(3).mean(), "v3": w.v.rolling(3).mean(),
                        "v7": w.v.rolling(7).mean()}, index=W.index)

    def fut_wind(H):  # oracle: true mean wind over the forecast window
        return pd.DataFrame({"fu": w.u.rolling(H).mean().shift(-H), "fv": w.v.rolling(H).mean().shift(-H),
                             "fspd": w.spd.rolling(H).max().shift(-H)}, index=W.index)

    rows = []
    for name, sid in SITES.items():
        s = col(sid, "salinity").where(lambda x: x <= 36)
        own = pd.DataFrame({"s0": s, "s7": s.rolling(7).mean(), "s_ds7": s - s.shift(7)}, index=W.index)
        for H in (1, 3, 7, 14):
            y = s.shift(-H)
            variants = {
                "rivers": [base],
                "+miss": [base, miss],
                "+wind": [base, wnd],
                "+both": [base, miss, wnd],
                "+both+fut_wind(oracle)": [base, miss, wnd, fut_wind(H)],
            }
            res = {"station": name, "H": H}
            for vn, parts in variants.items():
                X = pd.concat([own, *parts], axis=1)
                df = X.assign(y=y).dropna(subset=["y", "s0"])
                tr, te = df[df.index < "2019-01-01"], df[df.index >= "2019-01-01"]
                if len(tr) < 500 or len(te) < 100:
                    continue
                f = [c for c in X.columns]
                mdl = lgb.train(dict(objective="l1", learning_rate=0.03, num_leaves=15, min_data_in_leaf=40,
                                     feature_fraction=0.8, bagging_fraction=0.8, bagging_freq=1, verbose=-1, seed=7),
                                lgb.Dataset(tr[f], tr.y - tr.s0), 500)
                p = te.s0.values + mdl.predict(te[f])
                ev = (te.y < 8).values
                res.setdefault("persist", round(float(np.mean(np.abs(te.s0 - te.y))), 2))
                res.setdefault("persist_event", round(float(np.mean(np.abs(te.s0[ev] - te.y[ev]))), 2) if ev.any() else None)
                res[vn] = round(float(np.mean(np.abs(p - te.y))), 2)
                res[f"{vn}_event"] = round(float(np.mean(np.abs(p[ev] - te.y.values[ev]))), 2) if ev.any() else None
            rows.append(res)
    out = pd.DataFrame(rows)
    cols = ["station", "H", "persist", "rivers", "+miss", "+wind", "+both", "+both+fut_wind(oracle)"]
    print("\nMAE (ppt), test 2019-2026. Lower is better; compare each column to 'persist'.\n")
    print(out[[c for c in cols if c in out]].to_string(index=False))
    ecols = ["station", "H", "persist_event"] + [f"{c}_event" for c in cols[3:]]
    print("\nSame, only on freshwater-event days (salinity < 8 ppt):\n")
    print(out[[c for c in ecols if c in out]].to_string(index=False))
    (REFERENCE / "probe").mkdir(exist_ok=True)
    out.to_csv(REFERENCE / "probe" / "drivers_experiment.csv", index=False)
    print(f"\nSaved {REFERENCE / 'probe' / 'drivers_experiment.csv'}")


if __name__ == "__main__":
    main()
