"""Build the JSON the static site reads.

site/data/<region>/latest.json        overview: cards, findings, headlines, rain forecast
site/data/<region>/sites/<id>.json    one year of daily values + normal bands, for drill-down
"""
from __future__ import annotations

import json
import re

import numpy as np
import pandas as pd

from . import normals as nm
from .config import SITE_OUT, VARIABLES, Region
from .indicators import SEVERITY, evaluate, is_suspect
from .units import convert, fmt, season_phrase, unit_label

SPARK_DAYS = 30
HISTORY_DAYS = 365


def _r(v, nd=2):
    return None if v is None or (isinstance(v, float) and not np.isfinite(v)) else round(float(v), nd)


def _virtual(region, daily, asof):
    """Virtual-sensor expectations and QC. Missing models or a model error never break the build."""
    try:
        from .models import virtual
        expected = virtual.predict(region, daily, asof - pd.Timedelta(days=HISTORY_DAYS), asof)
        return expected, virtual.qc(region, daily, expected, asof)
    except Exception as e:  # noqa: BLE001
        import logging
        logging.getLogger(__name__).warning("virtual sensors skipped: %s", e)
        return pd.DataFrame(), {}


def _with_virtual(region, card: dict, q: dict | None, var: str, site: dict) -> dict:
    """Attach neighbor-based expectation, QC verdict, and (where earned) an estimate."""
    if var != "salinity" or not q:
        return card
    exp = {"value": _r(q["q50"], 1), "lo": _r(q["lo90"], 1), "hi": _r(q["hi90"], 1),
           "display": fmt("salinity", q["q50"], region.units), "mae": _r(q.get("mae"), 1),
           "published": q["publish"]}
    card["expected"] = exp
    live = card.get("status") != "no_data" and not card.get("stale")
    if live and card.get("value") is not None:
        v = card["value"]
        if v > q["hi90"] or v < q["lo90"]:
            card["vs_neighbors"] = "high" if v > q["hi90"] else "low"
        if q["suspect"]:
            card["suspect"] = True
            card["suspect_reason"] = "neighbors"
    elif q["publish"]:
        card["estimate"] = exp
    return card


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _card_var(region, daily, normals, site, var, asof):
    s = daily[(daily.site == site["id"]) & (daily["var"] == var) & (daily.date <= asof)].sort_values("date")
    if s.empty:
        return {"status": "no_data"}
    last = s.iloc[-1]
    age = (asof - last.date).days
    out = {
        "value": _r(convert(var, last.value, region.units)),
        "display": fmt(var, last.value, region.units),
        "unit": unit_label(var, region.units),
        "date": last.date.strftime("%Y-%m-%d"),
        "stale": age > 3,
        "suspect": bool(is_suspect(var, last.value)),
        "suspect_reason": "ceiling" if is_suspect(var, last.value) else None,
        "age_days": int(age),
    }
    spark = s[s.date > asof - pd.Timedelta(days=SPARK_DAYS)]
    out["spark"] = [[d.strftime("%Y-%m-%d"), _r(convert(var, v, region.units))]
                    for d, v in zip(spark.date, spark.value)]
    wk = s[s.date > last.date - pd.Timedelta(days=7)]
    if len(wk) >= 4:
        out["change_7d"] = _r(convert(var, wk.value.iloc[-1], region.units)
                              - convert(var, wk.value.iloc[0], region.units))
    nvar = var if var != "rain" else "rain_7d"
    if var == "rain":  # rain cards show the 7-day total vs normal
        r7 = s.set_index("date")["value"].asfreq("D").fillna(0).iloc[-7:].sum()
        out["total_7d"] = _r(convert("rain", r7, region.units))
        out["display"] = fmt("rain", r7, region.units) + " past 7 days"
        cmp_val = r7
    else:
        cmp_val = last.value
    n = normals[(normals.site == site["id"]) & (normals["var"] == nvar)
                & (normals.doy == min(last.date.dayofyear, 365))] if not normals.empty else normals
    if not n.empty:
        n = n.iloc[0]
        pct = nm.percentile_of(cmp_val, n)
        out["normal"] = {f"p{p}": _r(convert(nvar, n[f'p{p}'], region.units)) for p in nm.PCTS}
        out["percentile"] = round(pct)
        out["band"] = "low" if pct <= 10 else "high" if pct >= 90 else (
            "below" if pct < 25 else "above" if pct > 75 else "normal")
    return out


def _majority(bands: list[str]) -> str | None:
    """'up', 'down' or None from a set of normal-bands."""
    if not bands:
        return None
    up = sum(b in ("above", "high") for b in bands)
    down = sum(b in ("below", "low") for b in bands)
    if up > len(bands) / 2:
        return "up"
    if down > len(bands) / 2:
        return "down"
    return None


def _live(cards, kinds, var):
    out = []
    for c in cards:
        r = c["vars"].get(var, {})
        if c["kind"] in kinds and r.get("band") and not r.get("stale") and not r.get("suspect"):
            out.append(r)
    return out


def _conditions(cards, season) -> str:
    """One plain sentence: rivers, then what that means for the Sound."""
    rivers = _live(cards, ("river",), "flow")
    river = _majority([r["band"] for r in rivers])
    sal = _majority([r["band"] for r in _live(cards, ("sound",), "salinity")])
    n = len(rivers)
    rivers_txt = {"down": "Both rivers are running low" if n == 2 else "The rivers are running low",
                  "up": "Both rivers are running high" if n == 2 else "The rivers are running high"}.get(river)
    sound_txt = {"up": "the Sound is saltier than usual", "down": "the Sound is fresher than usual"}.get(sal, "the Sound is close to normal")
    if rivers_txt and ((river == "down" and sal == "up") or (river == "up" and sal == "down")):
        return f"{rivers_txt}, so {sound_txt} for {season}."
    if rivers_txt:
        return f"{rivers_txt}, and {sound_txt} for {season}."
    return f"{sound_txt[0].upper()}{sound_txt[1:]} for {season}."


def _water_temp(cards, units) -> str | None:
    temps = _live(cards, ("sound",), "water_temp")
    if not temps:
        return None
    avg = sum(r["value"] for r in temps) / len(temps)
    trend = {"up": "warmer than usual", "down": "cooler than usual"}.get(_majority([r["band"] for r in temps]), "about normal")
    unit = "°F" if units.get("temp") == "F" else "°C"
    return f"Water temperatures are {trend}, around {avg:.0f}{unit}."


def _headline(region, findings, persona, asof, cards):
    """Lead with anything serious; otherwise describe the overall picture in plain words."""
    focus = persona["focus"]
    season = season_phrase(asof)
    rel = [f for f in findings if set(f["topics"]) & set(focus)]
    serious = sorted([f for f in rel if SEVERITY.get(f["severity"], 0) >= SEVERITY["watch"]],
                     key=lambda f: -SEVERITY.get(f["severity"], 0))
    own_model = [f for f in rel if f.get("site") is None and focus[0] in f["topics"] and focus[0] != "general"]
    parts: list[str] = []
    if serious:
        parts.append(serious[0]["text"])
    if own_model:
        parts.append(own_model[0].get("short", own_model[0]["text"]))
    if not parts:
        parts.append(_conditions(cards, season))
        if focus[0] in ("shrimp", "fish"):
            wt = _water_temp(cards, region.units)
            if wt:
                parts.append(wt)
        if focus[0] == "oyster":
            sal = [r["value"] for r in _live(cards, ("sound",), "salinity")]
            if sal and min(sal) > 5:
                parts.append("No freshwater stress on the reefs: every station is well above 2 ppt.")
    text = " ".join(parts)
    return text if len(text) <= 240 else parts[0]


def build(region: Region, daily: pd.DataFrame, normals: pd.DataFrame, asof: pd.Timestamp,
          forecast: pd.DataFrame | None = None, generated_at: pd.Timestamp | None = None) -> dict:
    expected, qcs = _virtual(region, daily, asof)
    suspect = {(sid, "salinity") for sid, q in qcs.items() if q["suspect"]}
    findings = evaluate(region, daily, normals, asof, suspect=suspect)
    cards = []
    for site in region.sites:
        cards.append({
            **{k: site.get(k) for k in ("id", "name", "short", "kind", "note", "lat", "lon", "drains_from", "osm_names")},
            "slug": site.get("slug") or slugify(site["short"]),
            "retired": bool(site.get("retired")),
            "vars": {v: _with_virtual(region, _card_var(region, daily, normals, site, v, asof), qcs.get(site["id"]), v, site)
                     for v in site["vars"]},
            "findings": [i for i, f in enumerate(findings) if f.get("site") == site["id"]],
        })
    fc = {}
    if forecast is not None and not forecast.empty:
        for sid, g in forecast.groupby("site"):
            fc[sid] = {"days": [[d.strftime("%Y-%m-%d"), _r(convert("rain", v, region.units))]
                                for d, v in zip(pd.to_datetime(g.date), g.value)],
                       "total": fmt("rain", g.value.sum(), region.units)}
    latest = {
        "region": {"id": region.id, "name": region.name, "units": region.units, "map": region.map},
        "generated_at": (generated_at or pd.Timestamp.now(tz="UTC")).isoformat(),
        "asof": asof.strftime("%Y-%m-%d"),
        "season": season_phrase(asof),
        "personas": region.personas,
        "headlines": {p["id"]: _headline(region, findings, p, asof, cards) for p in region.personas},
        "findings": findings,
        "cards": cards,
        "rain_forecast": fc,
        "variables": {k: {"label": v["label"]} for k, v in VARIABLES.items()},
    }
    out = SITE_OUT / region.id
    (out / "sites").mkdir(parents=True, exist_ok=True)
    (out / "latest.json").write_text(json.dumps(latest, default=str, separators=(",", ":")))

    start = asof - pd.Timedelta(days=HISTORY_DAYS)
    for site in region.sites:
        series = {}
        for var in site["vars"]:
            s = daily[(daily.site == site["id"]) & (daily["var"] == var)
                      & (daily.date > start) & (daily.date <= asof)].sort_values("date")
            nvar = var if var != "rain" else None
            nrm = normals[(normals.site == site["id"]) & (normals["var"] == nvar)].set_index("doy") \
                if nvar and not normals.empty else None
            rows = []
            for d in pd.date_range(start + pd.Timedelta(days=1), asof):
                rows.append(d)
            vals = s.set_index("date")["value"]
            series[var] = {
                "unit": unit_label(var, region.units),
                "label": VARIABLES[var]["label"],
                "points": [[d.strftime("%Y-%m-%d"),
                            _r(convert(var, vals.get(d), region.units)) if d in vals.index else None,
                            *([_r(convert(var, nrm.loc[min(d.dayofyear, 365), c], region.units))
                               for c in ("p10", "p50", "p90")]
                              if nrm is not None and min(d.dayofyear, 365) in nrm.index else [None] * 3)]
                           for d in rows],
            }
        if "salinity" in series and not expected.empty:
            e = expected[(expected.site == site["id"]) & (expected.date > start)].sort_values("date")
            if len(e):
                series["salinity"]["expected"] = [[d.strftime("%Y-%m-%d"), _r(q50), _r(lo), _r(hi)]
                                                  for d, q50, lo, hi in zip(e.date, e.q50, e.lo90, e.hi90)]
                series["salinity"]["expected_mae"] = _r(e.mae.iloc[-1], 1)
        (out / "sites" / f"{site['id']}.json").write_text(json.dumps(
            {"id": site["id"], "slug": site.get("slug") or slugify(site["short"]), "name": site["name"], "drains_from": site.get("drains_from", []),
             "note": site.get("note"), "series": series}, separators=(",", ":")))
    return latest
