"""Indicators: rules over the daily table that produce plain-language findings.

Rule types (configured per region in regions/<id>.yaml):
  vs_normal   latest value outside the p<low>/p<high> band for this time of year
  run_below   consecutive days under a threshold (e.g. oyster freshwater stress)
  record      the last two weeks ranked against the same dates in every year on record (top or bottom 3)
  custom      a Python function "module:function" for anything model-like

A finding is a dict: indicator, site, severity, topics, text, plus details.
Severity ladder: notice < watch < warning < alert.
"""
from __future__ import annotations

import importlib
import logging

import pandas as pd

from . import normals as nm
from .config import VARIABLES, Region
from .units import fmt, season_phrase

log = logging.getLogger(__name__)
SEVERITY = {"notice": 1, "watch": 2, "warning": 3, "alert": 4}
STALE_DAYS = 3


def _latest(daily: pd.DataFrame, site: str, var: str, asof: pd.Timestamp):
    s = daily[(daily.site == site) & (daily["var"] == var) & (daily.date <= asof)]
    if s.empty:
        return None
    row = s.loc[s.date.idxmax()]
    if (asof - row.date).days > STALE_DAYS or is_suspect(var, row.value):
        return None
    return row


def is_suspect(var: str, value: float) -> bool:
    """Readings beyond what the water can plausibly do (e.g. Sound saltier than the open Gulf).
    Usually a fouled or drifting sensor; USGS data is provisional until reviewed."""
    ceiling = VARIABLES.get(var, {}).get("suspect_above")
    return ceiling is not None and value > ceiling


def _normal_row(normals: pd.DataFrame, site: str, var: str, date: pd.Timestamp):
    n = normals[(normals.site == site) & (normals["var"] == var)
                & (normals.doy == min(date.dayofyear, 365))]
    return None if n.empty else n.iloc[0]


def _sites_for(region: Region, cfg: dict) -> list[dict]:
    if "sites" in cfg:
        return [region.site(s) for s in cfg["sites"]]
    return [s for s in region.sites
            if s["kind"] in cfg.get("kinds", [s["kind"]]) and cfg.get("var") in s["vars"]]


def vs_normal(region, cfg, daily, normals, asof):
    out = []
    for site in _sites_for(region, cfg):
        row = _latest(daily, site["id"], cfg["var"], asof)
        if row is None:
            continue
        n = _normal_row(normals, site["id"], cfg["var"], row.date)
        if n is None:
            continue
        pct = nm.percentile_of(row.value, n)
        side = "low" if row.value < n.p10 and pct <= cfg["low_pct"] else (
               "high" if row.value > n.p90 and pct >= cfg["high_pct"] else None)
        if side is None:
            continue
        text = cfg[f"{side}_text"].format(
            site=site["name"], value=fmt(cfg["var"], row.value, region.units),
            p50=fmt(cfg["var"], n.p50, region.units), season=season_phrase(row.date))
        out.append({"indicator": cfg["id"], "site": site["id"], "severity": "notice",
                    "topics": cfg.get("topics", []), "text": text, "side": side,
                    "var": cfg["var"], "date": row.date.strftime("%Y-%m-%d")})
    return out


def run_below(region, cfg, daily, normals, asof):
    out = []
    for site in _sites_for(region, cfg):
        s = daily[(daily.site == site["id"]) & (daily["var"] == cfg["var"]) & (daily.date <= asof)]
        if s.empty or (asof - s.date.max()).days > STALE_DAYS:
            continue
        s = s.set_index("date")["value"].sort_index()
        days = 0
        for v in s.iloc[::-1]:
            if v < cfg["threshold"]:
                days += 1
            else:
                break
        sev = ("alert" if days >= cfg["alert_days"] else "warning" if days >= cfg["warn_days"]
               else "watch" if days >= cfg["watch_days"] else None)
        if sev is None:
            continue
        out.append({"indicator": cfg["id"], "site": site["id"], "severity": sev,
                    "topics": cfg.get("topics", []), "days": days, "var": cfg["var"],
                    "text": cfg["text"].format(site=site["name"], days=days,
                                               threshold=cfg["threshold"])})
    return out


ORDINAL = {1: "", 2: "second-", 3: "third-", 4: "fourth-", 5: "fifth-"}


def _years(ys: list[int]) -> str:
    ys = [str(y) for y in ys]
    return ys[0] if len(ys) == 1 else f"{', '.join(ys[:-1])} and {ys[-1]}"


def record_means(cfg, daily, site_id, asof) -> tuple[dict[int, float], str] | None:
    """Each year's `window`-day mean for a `record` indicator, and the newest reading's date; None when the station
    is stale or too few years count. The year dots (build.py) use this too, so they always agree with the text."""
    from . import history
    s = history.series(daily, site_id, cfg["var"], asof)
    if s.empty or (asof - s.index[-1]).days > STALE_DAYS:
        return None
    means = history.window_means(s, asof, cfg.get("window", 14), cfg.get("min_days", 10))
    if asof.year not in means or len(means) < cfg.get("min_years", 10):
        return None
    return means, s.index[-1].strftime("%Y-%m-%d")


def record(region, cfg, daily, normals, asof):
    """Today's mean over the last `window` days, ranked against the same calendar days in every year on record
    (decision 0028). Only a top or bottom `top` rank becomes a finding."""
    out = []
    top = cfg.get("top", 3)
    for site in _sites_for(region, cfg):
        got = record_means(cfg, daily, site["id"], asof)
        if got is None:
            continue
        means, last = got
        ranked = sorted(means, key=means.get)
        for side, order in (("low", ranked), ("high", ranked[::-1])):
            rank = order.index(asof.year) + 1
            if rank > top:
                continue
            others = order[:rank - 1]
            text = cfg[f"{side}_text"].format(
                site=site["name"], rank=ORDINAL[rank] + cfg[f"{side}_word"], since=min(means),
                season=season_phrase(asof).replace(" ", "-"))
            if others:
                text += f" Only {_years(others)} {'was' if len(others) == 1 else 'were'} {cfg[f'{side}_cmp']}."
            out.append({"indicator": cfg["id"], "site": site["id"], "severity": "notice",
                        "topics": cfg.get("topics", []), "text": text, "side": side, "rank": rank,
                        "years": len(means), "var": cfg["var"], "date": last})
    return out


def _in_season(cfg: dict, asof: pd.Timestamp) -> bool:
    if "active" not in cfg:
        return True
    lo, hi = cfg["active"]
    md = asof.strftime("%m-%d")
    return lo <= md <= hi if lo <= hi else (md >= lo or md <= hi)


def custom(region, cfg, daily, normals, asof):
    mod, fn = cfg["fn"].split(":")
    return getattr(importlib.import_module(mod), fn)(region, cfg, daily, normals, asof)


RULES = {"vs_normal": vs_normal, "run_below": run_below, "record": record, "custom": custom}


def evaluate(region: Region, daily: pd.DataFrame, normals: pd.DataFrame,
             asof: pd.Timestamp, suspect: set | None = None) -> list[dict]:
    """suspect: {(site, var)} whose latest readings failed QC; they never produce findings."""
    findings = []
    plain = set()   # ids of vs_normal indicators
    for cfg in region.indicators:
        if not _in_season(cfg, asof):
            continue
        if cfg["type"] == "vs_normal":
            plain.add(cfg["id"])
        try:
            findings += RULES[cfg["type"]](region, cfg, daily, normals, asof)
        except Exception:  # one broken indicator must not take down the page
            log.exception("indicator %s failed", cfg.get("id"))
    # A record line says what "running low" would, more precisely: keep only the record.
    records = {(f["site"], f["var"]) for f in findings if f.get("rank")}
    findings = [f for f in findings if not (f["indicator"] in plain and (f.get("site"), f.get("var")) in records)]
    if suspect:
        findings = [f for f in findings if (f.get("site"), f.get("var")) not in suspect]
    findings.sort(key=lambda f: -SEVERITY.get(f["severity"], 0))
    # Drop a plain "unusual vs normal" notice when a stronger finding already
    # covers the same site and variable (e.g. the oyster stress alert).
    strong = {(f.get("site"), f.get("var")) for f in findings
              if SEVERITY.get(f["severity"], 0) > SEVERITY["notice"]}
    return [f for f in findings
            if not (f["severity"] == "notice" and (f.get("site"), f.get("var")) in strong)]
