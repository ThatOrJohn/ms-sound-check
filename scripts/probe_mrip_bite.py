#!/usr/bin/env python3
"""
Probe: do water conditions in the Sound say anything about whether anglers catch fish?

What it does
  1. Downloads NOAA's MRIP public-use survey files (dockside angler interviews, 2000-2025)
     and keeps the Mississippi intercepts. Every one is in Hancock, Harrison or Jackson County.
  2. For each angler who said they were fishing FOR a species (primary or secondary target),
     records whether they caught at least one ("success").
  3. Joins each interview day to conditions from our own daily store (data/ms/daily/):
     salinity and water temperature at the county's USGS station, their anomalies and
     3-day changes, river flow anomalies, wind, rain, Dauphin Island water level, moon.
  4. Asks, per species and condition: does adding that condition to a "season only" model
     (month + county + mode + area + year trend) predict success better, scored by
     leave-one-YEAR-out log loss? Also reports the success-rate gap between the top and
     bottom third of the condition *within the same month and county*, with a site-day bootstrap CI.

Honest framing
  - MRIP intercepts are a sample of people who came back to a dock and agreed to talk.
    The county is where they landed, not where they fished, and the conditions are daily
    means at one station. Expect small effects even if fish really respond.
  - Season dominates. A condition only "counts" if it improves on the season baseline out
    of sample, in most years, not just in-sample.
  - Estimates are unweighted (no MRIP sample weights). Fine for "do conditions matter",
    wrong for "how many fish were caught".

Usage (run from the repo root after `python -m msc backfill` so data/ms/daily/ is filled)
    python scripts/probe_mrip_bite.py

Data source: https://www.st.nmfs.noaa.gov/st1/recreational/MRIP_Survey_Data/CSV/
"""
from __future__ import annotations

import glob
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "mrip"
DAILY = ROOT / "data" / "ms" / "daily"
OUT = ROOT / "data" / "probe"

MRIP_URL = "https://www.st.nmfs.noaa.gov/st1/recreational/MRIP_Survey_Data/CSV/"
MRIP_FILES = ["ps_2000_2004", "ps_2005_2009", "ps_2010_2014", "ps_2015_2019",
              "ps_2020", "ps_2021", "ps_2022", "ps_2023", "ps_2024", "ps_2025"]
MS_FIPS = 28
COUNTIES = {45: "Hancock", 47: "Harrison", 59: "Jackson"}

# Nearest long-running USGS sonde to each county's landing sites.
COUNTY_STATION = {
    "Hancock": "USGS-301429089145600",   # Merrill Shell Bank
    "Harrison": "USGS-302318088512600",  # Point Cadet (Biloxi Bay mouth)
    "Jackson": "USGS-301849088350000",   # Round Island (Pascagoula)
}
SPECIES = ["SPOTTED SEATROUT", "RED DRUM", "SOUTHERN FLOUNDER", "SAND SEATROUT",
           "SHEEPSHEAD", "RED SNAPPER"]
CONDITIONS = {
    "sal": "Salinity (ppt)",
    "sal_anom": "Salinity vs normal for the date",
    "sal_chg3": "Salinity change over 3 days",
    "temp": "Water temp (C)",
    "temp_anom": "Water temp vs normal for the date",
    "temp_chg3": "Water temp change over 3 days",
    "pearl_anom": "Pearl River flow vs normal (log)",
    "pasc_anom": "Pascagoula River flow vs normal (log)",
    "wind": "Mean wind speed (m/s)",
    "wind_max": "Peak wind (m/s)",
    "wind_v": "Wind from the south (m/s)",
    "rain3": "Rain, past 3 days (mm)",
    "level_anom": "Water level vs 31-day mean (m)",
    "moon": "Moon illumination (0-1)",
}
NEW_MOON = pd.Timestamp("2000-01-06 18:14")
SYNODIC = 29.530588853


# ---------------------------------------------------------------- MRIP
def fetch_mrip() -> None:
    import urllib.request

    RAW.mkdir(parents=True, exist_ok=True)
    for f in MRIP_FILES:
        dest = RAW / f"{f}_csv.zip"
        if not dest.exists():
            print(f"downloading {f} ...", file=sys.stderr)
            urllib.request.urlretrieve(f"{MRIP_URL}{f}_csv.zip", dest)


def load_mrip() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Mississippi trip and catch rows, cached as parquet after the first pass over the zips."""
    tcache, ccache = RAW / "ms_trips.parquet", RAW / "ms_catch.parquet"
    if not (tcache.exists() and ccache.exists()):
        fetch_mrip()
        tcols = {"ST", "CNTY", "ID_CODE", "PSU_ID", "YEAR", "WAVE", "MODE_FX", "AREA_X", "HRSF",
                 "PRIM1_COMMON", "PRIM2_COMMON", "CNTRBTRS", "WP_INT", "INTSITE"}
        ccols = {"ST", "ID_CODE", "COMMON", "SP_CODE", "CLAIM", "HARVEST", "RELEASE", "TOT_CAT"}
        trips, catch = [], []
        for z in sorted(glob.glob(str(RAW / "ps_*_csv.zip"))):
            with zipfile.ZipFile(z) as zf:
                for n in zf.namelist():
                    keep = tcols if n.startswith("trip_") else ccols if n.startswith("catch_") else None
                    if keep is None:
                        continue
                    d = pd.read_csv(zf.open(n), dtype=str, usecols=lambda c: c.upper() in keep)
                    d.columns = d.columns.str.upper()
                    d = d[pd.to_numeric(d.ST, errors="coerce") == MS_FIPS]
                    (trips if n.startswith("trip_") else catch).append(d)
        pd.concat(trips).to_parquet(tcache)
        pd.concat(catch).to_parquet(ccache)
    return pd.read_parquet(tcache), pd.read_parquet(ccache)


def tidy_trips(t: pd.DataFrame) -> pd.DataFrame:
    t = t.copy()
    t["ID_CODE"] = t.ID_CODE.str.strip()
    t["date"] = pd.to_datetime(t.ID_CODE.str[5:13], format="%Y%m%d", errors="coerce")
    t["county"] = pd.to_numeric(t.CNTY, errors="coerce").map(COUNTIES)
    t["mode"] = pd.to_numeric(t.MODE_FX, errors="coerce").map({3: "shore", 5: "charter", 7: "private"})
    t["area"] = pd.to_numeric(t.AREA_X, errors="coerce").map({1: "state", 2: "federal", 5: "inland"})
    t["hours"] = pd.to_numeric(t.HRSF, errors="coerce")
    t["year"] = t.date.dt.year
    t["month"] = t.date.dt.month
    return t.dropna(subset=["date", "county", "mode", "area"])


# ---------------------------------------------------------------- conditions
def doy_clim(s: pd.Series) -> pd.Series:
    """Day-of-year climatology, smoothed with a circular 31-day window, mapped back onto s's index."""
    doy = np.minimum(s.index.dayofyear, 365)
    raw = s.groupby(doy).mean().reindex(range(1, 366))
    wrapped = pd.concat([raw.iloc[-15:], raw, raw.iloc[:15]])
    smooth = wrapped.rolling(31, center=True, min_periods=10).mean().iloc[15:-15]
    smooth.index = range(1, 366)
    return pd.Series(smooth.reindex(doy).values, index=s.index)


def load_conditions() -> pd.DataFrame:
    """One row per (date, county) with every condition in CONDITIONS."""
    files = sorted(glob.glob(str(DAILY / "*.parquet")))
    if not files:
        sys.exit("data/ms/daily/ is empty; run `python -m msc backfill` first.")
    d = pd.concat(pd.read_parquet(f) for f in files)
    d["date"] = pd.to_datetime(d.date)
    wide = d.pivot_table(index="date", columns=["site", "var"], values="value", aggfunc="mean")
    wide = wide.asfreq("D")

    def col(site: str, var: str) -> pd.Series:
        return wide[(site, var)] if (site, var) in wide else pd.Series(np.nan, index=wide.index)

    # Sound-wide fallbacks: mean of every station reporting that day.
    sal_all = wide.xs("salinity", level="var", axis=1).filter(like="USGS-")
    temp_all = wide.xs("water_temp", level="var", axis=1).filter(like="USGS-")

    shared = pd.DataFrame(index=wide.index)
    for name, site in (("pearl", "USGS-02489500"), ("pasc", "USGS-02479000")):
        q = np.log10(col(site, "flow").where(lambda x: x > 0))
        shared[f"{name}_anom"] = q - doy_clim(q)
    u, v = col("wind-sound", "wind_u"), col("wind-sound", "wind_v")
    shared["wind"] = np.hypot(u, v)
    shared["wind_max"] = col("wind-sound", "wind_max")
    shared["wind_v"] = v
    shared["rain3"] = col("local-biloxi", "rain").rolling(3, min_periods=2).sum()
    lvl = col("NOAA-8735180", "water_level")
    shared["level_anom"] = lvl - lvl.rolling(31, center=True, min_periods=15).mean()
    age = ((shared.index - NEW_MOON).total_seconds() / 86400) % SYNODIC
    shared["moon"] = (1 - np.cos(2 * np.pi * age / SYNODIC)) / 2

    rows = []
    for county, site in COUNTY_STATION.items():
        sal = col(site, "salinity").fillna(sal_all.mean(axis=1))
        temp = col(site, "water_temp").fillna(temp_all.mean(axis=1))
        c = shared.copy()
        c["sal"], c["temp"] = sal, temp
        c["sal_anom"], c["temp_anom"] = sal - doy_clim(sal), temp - doy_clim(temp)
        c["sal_chg3"], c["temp_chg3"] = sal - sal.shift(3), temp - temp.shift(3)
        c["county"] = county
        rows.append(c.rename_axis("date").reset_index())
    return pd.concat(rows, ignore_index=True)


# ---------------------------------------------------------------- outcome
def targeted(trips: pd.DataFrame, catch: pd.DataFrame, species: str) -> pd.DataFrame:
    """Anglers who targeted `species`, with success = caught at least one (kept or released)."""
    t = trips[(trips.PRIM1_COMMON == species) | (trips.PRIM2_COMMON == species)].copy()
    c = catch[catch.COMMON == species].assign(n=lambda x: pd.to_numeric(x.TOT_CAT, errors="coerce"))
    t["caught"] = t.ID_CODE.map(c.groupby(c.ID_CODE.str.strip()).n.sum()).fillna(0)
    t["success"] = (t.caught > 0).astype(float)
    return t


# ---------------------------------------------------------------- scoring
def design(df: pd.DataFrame, extra: list[str], mu: pd.Series, sd: pd.Series) -> np.ndarray:
    base = pd.get_dummies(df[["month", "county", "mode", "area"]].astype(str), drop_first=True)
    yr = (df.year - 2012) / 8
    cols = [np.ones(len(df)), yr, yr ** 2, *base.values.T.astype(float)]
    for e in extra:
        z = ((df[e] - mu[e]) / sd[e]).values
        cols += [z, z ** 2]          # quadratic: fish often have a comfortable middle range
    return np.column_stack(cols)


def fit_logit(X: np.ndarray, y: np.ndarray, ridge: float = 1.0, iters: int = 25) -> np.ndarray:
    """Ridge-penalized logistic regression by IRLS (intercept unpenalized)."""
    b = np.zeros(X.shape[1])
    pen = np.full(X.shape[1], ridge)
    pen[0] = 0
    for _ in range(iters):
        p = 1 / (1 + np.exp(-np.clip(X @ b, -30, 30)))
        w = p * (1 - p) + 1e-9
        H = X.T @ (X * w[:, None]) + np.diag(pen)
        step = np.linalg.solve(H, X.T @ (y - p) - pen * b)
        b += step
        if np.abs(step).max() < 1e-6:
            break
    return b


def loyo_logloss(df: pd.DataFrame, extra: list[str]) -> pd.Series:
    """Leave-one-year-out log loss per held-out year."""
    out = {}
    for yr in sorted(df.year.unique()):
        tr, te = df[df.year != yr], df[df.year == yr]
        mu, sd = tr[extra].mean(), tr[extra].std()
        # Dummies must line up between train and test, so build them on the full frame.
        X = design(df, extra, mu, sd)
        trm = (df.year != yr).values
        b = fit_logit(X[trm], tr.success.values)
        p = np.clip(1 / (1 + np.exp(-(X[~trm] @ b))), 1e-6, 1 - 1e-6)
        y = te.success.values
        out[yr] = -np.sum(y * np.log(p) + (1 - y) * np.log(1 - p))
    return pd.Series(out)


def tercile_gap(df: pd.DataFrame, cond: str, reps: int = 1000, seed: int = 0) -> tuple[float, float, float]:
    """Success rate in the top third minus bottom third of `cond`, ranked within month and county.
    95% CI by resampling site-days (PSU_ID), since anglers interviewed together share a day."""
    pct = df.groupby(["month", "county"])[cond].rank(pct=True)
    g = df.assign(lo=(pct <= 1 / 3).astype(float), hi=(pct > 2 / 3).astype(float))
    g = g.assign(slo=g.lo * g.success, shi=g.hi * g.success)
    psu = g.groupby("PSU_ID")[["lo", "hi", "slo", "shi"]].sum().values
    gap = psu[:, 3].sum() / psu[:, 1].sum() - psu[:, 2].sum() / psu[:, 0].sum()
    rng = np.random.default_rng(seed)
    w = rng.multinomial(len(psu), np.full(len(psu), 1 / len(psu)), size=reps)
    s = w @ psu
    boot = s[:, 3] / s[:, 1] - s[:, 2] / s[:, 0]
    lo, hi = np.nanpercentile(boot, [2.5, 97.5])
    return float(gap), float(lo), float(hi)


def score(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for cond, label in CONDITIONS.items():
        d = df.dropna(subset=[cond])
        if len(d) < 300 or d.year.nunique() < 8:
            continue
        base, full = loyo_logloss(d, []), loyo_logloss(d, [cond])
        gap, lo, hi = tercile_gap(d, cond)
        rows.append({
            "condition": cond,
            "label": label,
            "n_trips": len(d),
            "years": d.year.nunique(),
            "logloss_gain_pct": round(100 * (1 - full.sum() / base.sum()), 2),
            "years_better": f"{int((full < base).sum())}/{len(base)}",
            "top_minus_bottom_third_pts": round(100 * gap, 1),
            "ci_low": round(100 * lo, 1),
            "ci_high": round(100 * hi, 1),
        })
    return pd.DataFrame(rows).sort_values("logloss_gain_pct", ascending=False)


# ---------------------------------------------------------------- plots
INK, MUTED, GRID, BAR = "#1f1f1e", "#6b6a63", "#e4e3dd", "#2a78d6"


def _style(ax) -> None:
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=MUTED, labelsize=8)
    ax.yaxis.grid(True, color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)


def plot_season(season: pd.DataFrame, path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(2, 3, figsize=(10, 5.6), sharey=True)
    for ax, sp in zip(axes.flat, SPECIES):
        s = season[season.species == sp].set_index("month").reindex(range(1, 13))
        ax.bar(s.index, 100 * s.success_rate, color=BAR, width=0.7)
        thin = s.trips < 30
        ax.bar(s.index[thin], 100 * s.success_rate[thin], color="white", width=0.7,
               edgecolor=BAR, hatch="////", linewidth=0)
        ax.set_title(f"{sp.title()}  (n={int(s.trips.sum()):,})", fontsize=9, color=INK, loc="left")
        ax.set_xticks(range(1, 13), list("JFMAMJJASOND"))
        ax.set_ylim(0, 100)
        _style(ax)
    for ax in axes[:, 0]:
        ax.set_ylabel("% of targeted trips with a catch", fontsize=8, color=MUTED)
    fig.suptitle("Mississippi anglers who caught what they were fishing for, by month (MRIP, 2000-2025)",
                 fontsize=10, color=INK, x=0.01, ha="left")
    fig.text(0.01, 0.005, "Hatched: fewer than 30 trips that month.", fontsize=7, color=MUTED)
    fig.tight_layout(rect=(0, 0.02, 1, 0.97))
    fig.savefig(path, dpi=150, facecolor="white")
    plt.close(fig)


def plot_conditions(df: pd.DataFrame, scores: pd.DataFrame, species: str, path: Path) -> None:
    """Success by within-month decile of the four best conditions for one species."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    top = scores.head(4)
    fig, axes = plt.subplots(1, len(top), figsize=(3 * len(top), 3.2), sharey=True)
    for ax, (_, r) in zip(np.atleast_1d(axes), top.iterrows()):
        d = df.dropna(subset=[r.condition])
        dec = np.ceil(d.groupby(["month", "county"])[r.condition].rank(pct=True) * 10).clip(1, 10)
        rate = d.groupby(dec).success.mean() * 100
        ax.axhline(d.success.mean() * 100, color=MUTED, linewidth=1, linestyle=(0, (3, 3)))
        ax.plot(rate.index, rate.values, color=BAR, linewidth=2, marker="o", markersize=5)
        ax.set_title(r.label, fontsize=8.5, color=INK, loc="left")
        ax.set_xlabel("Decile within month & county (1 = lowest)", fontsize=7.5, color=MUTED)
        ax.set_xticks([1, 5, 10])
        _style(ax)
    np.atleast_1d(axes)[0].set_ylabel("% of trips with a catch", fontsize=8, color=MUTED)
    fig.suptitle(f"{species.title()}: success vs conditions, season and county removed (dashed = overall rate)",
                 fontsize=9.5, color=INK, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(path, dpi=150, facecolor="white")
    plt.close(fig)


# ---------------------------------------------------------------- main
def main() -> int:
    trips, catch = load_mrip()
    trips = tidy_trips(trips)
    cond = load_conditions()
    print(f"Mississippi interviews: {len(trips):,}  ({trips.date.min():%Y-%m-%d} to {trips.date.max():%Y-%m-%d})")
    print(trips.groupby("county").size().to_string(), "\n")

    OUT.mkdir(parents=True, exist_ok=True)
    season_rows, all_scores, joined = [], [], []
    for sp in SPECIES:
        t = targeted(trips, catch, sp).merge(cond, on=["date", "county"], how="left")
        joined.append(t.assign(species=sp))
        season_rows.append(t.groupby("month").agg(trips=("success", "size"),
                                                  success_rate=("success", "mean"),
                                                  mean_caught=("caught", "mean")).reset_index().assign(species=sp))
        print(f"== {sp}: {len(t):,} targeted trips, {t.success.mean():.0%} caught one, "
              f"mean {t.caught.mean():.1f} fish/trip")
        s = score(t).assign(species=sp)
        all_scores.append(s)
        print(s.drop(columns=["species", "label"]).head(8).to_string(index=False), "\n")
        if sp == "SPOTTED SEATROUT":
            plot_conditions(t, s, sp, OUT / "mrip_trout_conditions.png")

    season = pd.concat(season_rows)
    scores = pd.concat(all_scores)
    season.to_csv(OUT / "mrip_season.csv", index=False)
    scores.to_csv(OUT / "mrip_scores.csv", index=False)
    keep = ["species", "ID_CODE", "PSU_ID", "date", "county", "mode", "area", "hours", "caught", "success",
            *CONDITIONS]
    pd.concat(joined)[keep].to_csv(OUT / "mrip_trips_joined.csv", index=False)
    plot_season(season, OUT / "mrip_season.png")

    print("Read this as: logloss_gain_pct is how much the condition improves on month + county + mode + area"
          " + year trend, out of sample by year. Under ~0.5% is noise-level. With 6 species x 14"
          " conditions, a few CIs will exclude zero by luck alone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
