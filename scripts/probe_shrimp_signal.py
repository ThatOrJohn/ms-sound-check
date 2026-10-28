#!/usr/bin/env python3
"""
Weekend probe: does spring water in the Mississippi Sound say anything about
when MDMR opens brown shrimp season?

What it does
  1. Downloads daily USGS values (specific conductance, water temperature,
     river discharge) for the Sound stations and the two big rivers.
  2. Converts specific conductance to practical salinity (PSS-78, via gsw),
     which gives a salinity record back to 1998-2009 depending on station,
     not just the 2011+ USGS salinity series.
  3. Builds one row per season of "what you could have known by May 1":
     Mar 1 - Apr 30 means per station and per river.
  4. Scores each feature against opening day (days after May 1) with
     Spearman correlation, a permutation p-value, and leave-one-out
     prediction error versus a "just guess the average" baseline.

Honest framing: ~15 seasons. Treat anything here as a hint, not a model.
A feature only "counts" if it beats the climatology baseline out of sample.

Usage
  pip install pandas numpy requests gsw matplotlib
  python scripts/probe_shrimp_signal.py            # real data
  python scripts/probe_shrimp_signal.py --synthetic # offline smoke test

Data source note: this uses the legacy waterservices.usgs.gov "dv" service,
which USGS plans to retire in Q1 2027. Fine for a one-off probe; the live
pipeline should use api.waterdata.usgs.gov (OGC API) instead.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "probe"

SOUND_SITES = {
    "301429089145600": "merrill_shell",   # conductance since 1998, still reporting
    "302318088512600": "point_cadet",     # conductance since 2000, still reporting
    "301849088350000": "round_island",    # conductance since 2009, still reporting
    "301912088583300": "gulfport_light",  # conductance 2009 - Aug 2024
    "301527088521500": "east_ship",       # conductance 2008 - Dec 2024
    "301141089320300": "east_pearl",      # river-mouth conductance since 2001
}
RIVER_SITES = {
    "02489500": "pearl_bogalusa",
    "02479000": "pascagoula_merrill",
}
START, END = "1998-01-01", "2026-06-30"
WINDOW = ("03-01", "04-30")  # what you know by May 1
NODATA = -999999.0


# ---------------------------------------------------------------- download
def fetch_dv(site: str) -> dict:
    """Daily values JSON for one site, cached under data/raw/."""
    RAW.mkdir(parents=True, exist_ok=True)
    cache = RAW / f"dv_{site}.json"
    if cache.exists():
        return json.loads(cache.read_text())
    import requests

    url = "https://waterservices.usgs.gov/nwis/dv/"
    params = {
        "format": "json",
        "sites": site,
        "parameterCd": "00095,00010,00060",
        "startDT": START,
        "endDT": END,
        "siteStatus": "all",
    }
    r = requests.get(url, params=params, timeout=120)
    r.raise_for_status()
    cache.write_text(r.text)
    return r.json()


def dv_to_frame(payload: dict) -> pd.DataFrame:
    """Flatten NWIS dv JSON into date x '<param>_<stat>' columns.

    Stations with top/bottom sondes return several value blocks per series;
    those are averaged together, which is the right call for a coarse probe.
    """
    cols: dict[str, list[pd.Series]] = {}
    for ts in payload.get("value", {}).get("timeSeries", []):
        param = ts["variable"]["variableCode"][0]["value"]
        stat = "x"
        for opt in ts["variable"].get("options", {}).get("option", []):
            if opt.get("name") == "Statistic":
                stat = opt.get("optionCode", "x")
        for block in ts.get("values", []):
            vals = block.get("value", [])
            if not vals:
                continue
            s = pd.Series(
                [float(v["value"]) for v in vals],
                index=pd.to_datetime([v["dateTime"][:10] for v in vals]),
            )
            s = s.where(s != NODATA)
            cols.setdefault(f"{param}_{stat}", []).append(s)
    if not cols:
        return pd.DataFrame()
    return pd.DataFrame(
        {k: pd.concat(v, axis=1).mean(axis=1) for k, v in cols.items()}
    ).sort_index()


def pick(df: pd.DataFrame, param: str) -> pd.Series:
    """Daily mean if present, else midpoint of daily max/min."""
    if f"{param}_00003" in df:
        return df[f"{param}_00003"]
    if f"{param}_00001" in df and f"{param}_00002" in df:
        return (df[f"{param}_00001"] + df[f"{param}_00002"]) / 2
    return pd.Series(dtype=float)


def sc_to_salinity(sc_uS: pd.Series) -> pd.Series:
    """Specific conductance (uS/cm at 25 C) -> practical salinity (PSS-78)."""
    import gsw

    return pd.Series(gsw.SP_from_C(sc_uS.values / 1000.0, 25.0, 0.0), index=sc_uS.index)


# ---------------------------------------------------------------- features
def window_mean(s: pd.Series, year: int, min_days: int = 30) -> float:
    lo, hi = pd.Timestamp(f"{year}-{WINDOW[0]}"), pd.Timestamp(f"{year}-{WINDOW[1]}")
    w = s.loc[lo:hi].dropna()
    return float(w.mean()) if len(w) >= min_days else np.nan


def build_features(frames: dict[str, pd.DataFrame], years: list[int]) -> pd.DataFrame:
    rows = []
    for y in years:
        row = {"season": y}
        for site, name in SOUND_SITES.items():
            df = frames.get(site, pd.DataFrame())
            sc, wt = pick(df, "00095"), pick(df, "00010")
            if not sc.empty:
                row[f"sal_{name}"] = window_mean(sc_to_salinity(sc.dropna()), y)
            if not wt.empty:
                row[f"temp_{name}"] = window_mean(wt, y)
        for site, name in RIVER_SITES.items():
            q = pick(frames.get(site, pd.DataFrame()), "00060")
            if not q.empty:
                m = window_mean(q, y)
                row[f"logq_{name}"] = np.log10(m) if m and m > 0 else np.nan
        rows.append(row)
    feats = pd.DataFrame(rows).set_index("season")
    # Composite "Sound salinity": average of whatever stations exist that year,
    # each standardized first so a station dropping out doesn't shift the level.
    sal = feats.filter(like="sal_")
    if not sal.empty:
        z = (sal - sal.mean()) / sal.std()
        feats["sal_composite_z"] = z.mean(axis=1, skipna=True)
    tmp = feats.filter(like="temp_")
    if not tmp.empty:
        z = (tmp - tmp.mean()) / tmp.std()
        feats["temp_composite_z"] = z.mean(axis=1, skipna=True)
    return feats


# ---------------------------------------------------------------- scoring
def spearman(x: np.ndarray, y: np.ndarray) -> float:
    rx, ry = pd.Series(x).rank().values, pd.Series(y).rank().values
    return float(np.corrcoef(rx, ry)[0, 1])


def perm_p(x: np.ndarray, y: np.ndarray, n: int = 5000, seed: int = 0) -> float:
    rng = np.random.default_rng(seed)
    obs = abs(spearman(x, y))
    hits = sum(abs(spearman(x, rng.permutation(y))) >= obs for _ in range(n))
    return (hits + 1) / (n + 1)


def loo_mae(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    """Leave-one-out MAE: 1-feature linear fit vs climatology (mean) baseline."""
    errs_model, errs_base = [], []
    for i in range(len(y)):
        m = np.ones(len(y), bool)
        m[i] = False
        slope, icpt = np.polyfit(x[m], y[m], 1)
        errs_model.append(abs(slope * x[i] + icpt - y[i]))
        errs_base.append(abs(y[m].mean() - y[i]))
    return float(np.mean(errs_model)), float(np.mean(errs_base))


def score(feats: pd.DataFrame, target: pd.Series) -> pd.DataFrame:
    out = []
    for col in feats.columns:
        d = pd.concat([feats[col], target], axis=1).dropna()
        n = len(d)
        if n < 8:
            out.append({"feature": col, "n": n, "note": "too few seasons"})
            continue
        x, y = d.iloc[:, 0].values, d.iloc[:, 1].values
        mae_m, mae_b = loo_mae(x, y)
        out.append({
            "feature": col,
            "n": n,
            "spearman": round(spearman(x, y), 2),
            "perm_p": round(perm_p(x, y), 3),
            "loo_mae_days": round(mae_m, 1),
            "baseline_mae_days": round(mae_b, 1),
            "beats_baseline": mae_m < mae_b,
            "note": "",
        })
    res = pd.DataFrame(out)
    if "perm_p" in res:
        res = res.sort_values("perm_p", na_position="last")
    return res


# ---------------------------------------------------------------- synthetic
def synthetic_frames(openings: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Fake daily data with a planted salinity -> opening-day link.

    Only exists to smoke-test the pipeline offline. Saltier springs -> earlier
    openings, plus noise; temperature and flow are pure noise except that flow
    drives salinity.
    """
    rng = np.random.default_rng(42)
    idx = pd.date_range(START, END, freq="D")
    days_after = (openings.set_index("season")["open_date"]
                  - pd.to_datetime(openings["season"].astype(str).values + "-05-01")).dt.days
    frames = {}
    year_sal = {y: 18 - 0.25 * (d - days_after.mean()) for y, d in days_after.items()}
    for site in SOUND_SITES:
        base = np.array([year_sal.get(t.year, 16.0) for t in idx]) + rng.normal(0, 2, len(idx))
        sal = np.clip(base, 0.5, 35)
        import gsw
        sc = gsw.C_from_SP(sal, 25.0, 0.0) * 1000
        temp = 22 + 7 * np.sin((idx.dayofyear - 110) / 365 * 2 * np.pi) + rng.normal(0, 1, len(idx))
        frames[site] = pd.DataFrame({"00095_00003": sc, "00010_00003": temp}, index=idx)
    for site in RIVER_SITES:
        q = np.array([10 ** (4.3 - 0.05 * (year_sal.get(t.year, 16) - 16)) for t in idx])
        frames[site] = pd.DataFrame({"00060_00003": q * rng.lognormal(0, 0.3, len(idx))}, index=idx)
    return frames


# ---------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--synthetic", action="store_true", help="offline smoke test with fake data")
    args = ap.parse_args()

    openings = pd.read_csv(ROOT / "data" / "shrimp_openings.csv", parse_dates=["open_date"])
    may1 = pd.to_datetime(openings["season"].astype(str) + "-05-01")
    target = pd.Series((openings["open_date"] - may1).dt.days.values,
                       index=openings["season"], name="days_after_may1")

    if args.synthetic:
        frames = synthetic_frames(openings)
    else:
        frames = {}
        for site in {**SOUND_SITES, **RIVER_SITES}:
            print(f"fetching {site} ...", file=sys.stderr)
            frames[site] = dv_to_frame(fetch_dv(site))

    feats = build_features(frames, list(target.index))
    results = score(feats, target)

    OUT.mkdir(parents=True, exist_ok=True)
    tag = "synthetic" if args.synthetic else "real"
    feats.join(target).to_csv(OUT / f"features_{tag}.csv")
    results.to_csv(OUT / f"scores_{tag}.csv", index=False)

    print(f"\nOpening day = days after May 1 (mean {target.mean():.1f}, sd {target.std():.1f}, n={len(target)})")
    print(results.to_string(index=False))

    best = results.dropna(subset=["perm_p"]).head(1)
    if not best.empty:
        col = best.iloc[0]["feature"]
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            d = pd.concat([feats[col], target], axis=1).dropna()
            fig, ax = plt.subplots(figsize=(6, 4.5))
            ax.scatter(d[col], d["days_after_may1"])
            for yr, r in d.iterrows():
                ax.annotate(str(yr), (r[col], r["days_after_may1"]), fontsize=8,
                            xytext=(3, 3), textcoords="offset points")
            ax.set_xlabel(f"{col} (Mar-Apr mean)")
            ax.set_ylabel("Shrimp season opens, days after May 1")
            ax.set_title(f"Best single feature ({tag} data)")
            fig.tight_layout()
            fig.savefig(OUT / f"best_feature_{tag}.png", dpi=150)
        except ImportError:
            pass

    print("\nRead this as: a feature is interesting only if beats_baseline is True"
          " AND perm_p is small. With ~15 seasons and ~20 features, expect one"
          " p<0.05 by luck alone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
