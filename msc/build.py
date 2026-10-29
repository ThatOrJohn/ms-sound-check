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
from . import store
from .config import SITE_OUT, VARIABLES, Region
from .indicators import SEVERITY, evaluate, is_suspect
from .units import convert, fmt, season_phrase, unit_label

SPARK_DAYS = 30
HISTORY_DAYS = 365
NOW_MAX_AGE = pd.Timedelta(hours=4)   # a "now" reading older than this is hidden, not shown


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


def _now(region, recent, site, var, now):
    """Newest observation plus today's low and high, or None if there isn't a fresh one."""
    r = recent[(recent.site == site["id"]) & (recent["var"] == var) & (recent.time <= now)]
    if r.empty or now - r.time.max() > NOW_MAX_AGE:
        return None
    last = r.loc[r.time.idxmax()]
    local = r.time.dt.tz_convert(region.timezone)
    today = r[local.dt.date == now.tz_convert(region.timezone).date()].value
    out = {"value": _r(convert(var, last.value, region.units)), "display": fmt(var, last.value, region.units),
           "time": last.time.isoformat(), "lo": _r(convert(var, today.min(), region.units)),
           "hi": _r(convert(var, today.max(), region.units))}
    if site["source"] == "nws":
        from .adapters import nws
        out["url"] = nws.latest_url(site["station"])
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


def _river_list(names: list[str]) -> str:
    """['Pearl River', 'Pascagoula River'] -> 'The Pearl and Pascagoula rivers'."""
    if len(names) == 1:
        return f"The {names[0]}"
    bare = [n.removesuffix(" River") for n in names]
    return f"The {', '.join(bare[:-1])} and {bare[-1]} rivers"


def _conditions(cards, season) -> str:
    """One plain sentence: rivers, then what that means for the Sound.

    The big rivers decide the direction; minor rivers are named only when they run the same way.
    """
    flows = [(c["short"], bool(c.get("minor")), r["band"]) for c in cards if c["kind"] == "river"
             for r in _live([c], ("river",), "flow")]
    river = _majority([b for _, minor, b in flows if not minor])
    sal = _majority([r["band"] for r in _live(cards, ("sound",), "salinity")])
    rivers_txt = None
    if river:
        names = [n for n, minor, b in sorted(flows, key=lambda f: f[1]) if _majority([b]) == river]
        verb = "is" if len(names) == 1 else "are"
        rivers_txt = f"{_river_list(names)} {verb} running {'low' if river == 'down' else 'high'}"
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


def _beaches(region, asof):
    """Beach section for the page, plus segment geometry for the map. None if no beach source."""
    if not region.extras.get("beaches"):
        return None, None
    from .adapters import beaches as src
    snap, geo = src.load(region)
    if not snap:
        return None, None
    fetched = pd.Timestamp(snap["fetched_at"]) if snap.get("fetched_at") else None
    if fetched is None or pd.Timestamp.now(tz="UTC") - fetched > pd.Timedelta(days=2):
        return None, None   # hide rather than show advisories that may have changed
    stations = snap["stations"]
    hist = region.data_dir / "beach_history.parquet"
    days_flagged = {}
    if hist.exists():   # how long each current advisory has been showing in our snapshots
        h = pd.read_parquet(hist)
        for s in stations:
            if s["status"] != "clear":
                hs = h[h.id == s["id"]].sort_values("date")
                run = 0
                for st in hs.status.iloc[::-1]:
                    if st == "clear":
                        break
                    run += 1
                days_flagged[s["id"]] = run
    counts = {k: sum(s["status"] == k for s in stations) for k in ("clear", "advisory", "closure")}
    samples = sorted(s["last_sample"] for s in stations if s.get("last_sample"))
    stations = [{**s, "days_flagged": days_flagged.get(s["id"]), "reason": _beach_reason(s)} for s in stations]
    section = {
        "source": snap.get("source"), "link": region.extras["beaches"].get("link"),
        "fetched_at": snap.get("fetched_at"), "total": len(stations), "counts": counts,
        "latest_sample": samples[-1] if samples else None,
        "stations": stations,
    }
    if geo:   # the map's beach popups say what the section says, so carry the same details on each segment
        by_id = {s["id"]: s for s in stations}
        keep = ("location", "reason", "since", "days_flagged", "last_sample")
        geo = {**geo, "features": [{**f, "properties": {**f["properties"], **{k: by_id[f["properties"]["id"]].get(k) for k in keep}}}
                                   if f["properties"].get("id") in by_id else f for f in geo["features"]]}
    return section, geo


def _beach_reason(s: dict) -> str | None:
    if s["status"] == "clear":
        return None
    e = (s.get("event") or "").lower()
    return "algal bloom" if "hab" in e or "algal" in e else "debris" if "debris" in e else "high bacteria"


def _tide_strip(region) -> dict | None:
    """Highs and lows at the middle tide station (the one the Fishing card leads with), with UTC offsets so the
    browser can place "now" on the curve without guessing the time zone."""
    from .adapters import tides as tide_src
    stations = region.extras.get("tides", [])
    rows = tide_src.load(region)
    if not stations or not rows:
        return None
    st = stations[len(stations) // 2]
    # NOAA gives local clock times; in the repeated hour when daylight time ends, take the first (daylight) one.
    local = lambda s: pd.Timestamp(s).tz_localize(region.timezone, ambiguous=True, nonexistent="shift_forward")
    events = [{"time": local(t["time"]).isoformat(), "type": t["type"], "ft": t["ft"]}
              for t in sorted(rows, key=lambda t: t["time"]) if t["station"] == st["id"]]
    return {"station": st["id"], "name": st["name"], "events": events} if len(events) >= 2 else None


REPLAY_DAYS = 30


def _replay(region, daily, normals, asof) -> dict:
    """Daily salinity at the map's stations and flow percentile for each river, for the map's replay slider."""
    days = pd.date_range(asof - pd.Timedelta(days=REPLAY_DAYS - 1), asof)
    recent = daily[(daily.date >= days[0]) & (daily.date <= asof)]
    out = {"days": [d.strftime("%Y-%m-%d") for d in days], "salinity": {}, "flow_pct": {}}
    for site in region.sites:
        if site.get("retired"):
            continue
        if site["kind"] in ("sound", "estuary") and "salinity" in site["vars"]:
            s = recent[(recent.site == site["id"]) & (recent["var"] == "salinity")].drop_duplicates("date").set_index("date").value
            out["salinity"][site["id"]] = [None if d not in s.index or is_suspect("salinity", s[d]) else _r(s[d], 1) for d in days]
        elif site["kind"] == "river" and not normals.empty:
            s = recent[(recent.site == site["id"]) & (recent["var"] == "flow")].drop_duplicates("date").set_index("date").value
            n = normals[(normals.site == site["id"]) & (normals["var"] == "flow")].set_index("doy")
            out["flow_pct"][site["id"]] = [
                round(nm.percentile_of(s[d], n.loc[min(d.dayofyear, 365)])) if d in s.index and min(d.dayofyear, 365) in n.index else None
                for d in days]
    return out


def _headline(region, findings, persona, asof, cards, beaches=None, oyster_watch=None, fishing=None, shrimp=None):
    """Lead with anything serious; otherwise describe the overall picture in plain words."""
    focus = persona["focus"]
    season = season_phrase(asof)
    rel = [f for f in findings if set(f["topics"]) & set(focus)]
    # Ties on severity go to whatever this persona cares about most (its focus order).
    focus_rank = lambda f: min((focus.index(t) for t in f["topics"] if t in focus), default=99)
    serious = sorted([f for f in rel if SEVERITY.get(f["severity"], 0) >= SEVERITY["watch"] or focus[0] in f.get("lead", [])],
                     key=lambda f: (-SEVERITY.get(f["severity"], 0), focus_rank(f)))
    own_model = [f for f in rel if f.get("site") is None and "lead" not in f
                 and focus[0] in f["topics"] and focus[0] != "general"]
    parts: list[str] = []
    if focus[0] == "fish":               # anglers' question is "should I go?": the outlook leads
        from .models import fishing as fishing_model
        fh = fishing_model.headline(fishing)
        if fh:
            parts.append(fh)
    if focus[0] == "shrimp":             # a fresh MDMR notice (opening, closure, area change) beats everything
        from .models import shrimp as shrimp_model
        sh = shrimp_model.headline(shrimp, asof)
        if sh:
            parts.append(sh)
    if serious:
        top = serious[0]
        if focus[0] in top.get("lead", []):      # a wide event leads, in its short form
            parts.insert(0, top["short"])
        else:
            parts.append(top["text"])
    if own_model:
        parts.append(own_model[0].get("short", own_model[0]["text"]))
    if not parts:
        parts.append(_conditions(cards, season))
        if focus[0] in ("shrimp", "fish"):
            wt = _water_temp(cards, region.units)
            if wt:
                parts.append(wt)
        if focus[0] == "general" and beaches and beaches["total"] and not (beaches["counts"]["advisory"] or beaches["counts"]["closure"]):
            parts.append(f"All {beaches['total']} monitored beaches are clear for swimming.")
        if focus[0] == "oyster" and oyster_watch and oyster_watch.get("available") and not oyster_watch.get("stale"):
            g = oyster_watch["gauge"]
            lowest = min(x["stage_ft"] for x in oyster_watch["groups"])
            if all(x["status"] == "clear" for x in oyster_watch["groups"]):
                parts.append(f"The Pearl River is at {g['stage']:.1f} ft, well below the {lowest:.0f}-ft level "
                             f"where MDMR closes western reefs.")
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
    generated_at = generated_at or pd.Timestamp.now(tz="UTC")
    recent = store.read_recent(region)
    cards = []
    for site in region.sites:
        cards.append({
            **{k: site.get(k) for k in ("id", "name", "short", "kind", "note", "lat", "lon", "drains_from", "osm_names")},
            **({"minor": True} if site.get("minor") else {}),
            "slug": site.get("slug") or slugify(site["short"]),
            "retired": bool(site.get("retired")),
            "vars": {v: _with_virtual(region, _card_var(region, daily, normals, site, v, asof), qcs.get(site["id"]), v, site)
                     for v in site["vars"]},
            "findings": [i for i, f in enumerate(findings)
                         if f.get("site") == site["id"] or site["id"] in f.get("sites", [])],
        })
        for v, out in cards[-1]["vars"].items():
            if VARIABLES[v].get("now") and (n := _now(region, recent, site, v, generated_at)):
                out["now"] = n
    fc = {}
    if forecast is not None and not forecast.empty:
        for sid, g in forecast.groupby("site"):
            fc[sid] = {"days": [[d.strftime("%Y-%m-%d"), _r(convert("rain", v, region.units))]
                                for d, v in zip(pd.to_datetime(g.date), g.value)],
                       "total": fmt("rain", g.value.sum(), region.units)}
    beach_section, beach_geo = _beaches(region, asof)
    from .models import fishing, oyster, shrimp
    oyster_section = oyster.section(region, daily, asof)
    fishing_section = fishing.section(region, daily, asof, cards, forecast)
    shrimp_section = shrimp.section(region, asof)
    from .models import satellite, spillway, vibrio
    spillway_section = spillway.section(region, daily, asof)
    vibrio_section = vibrio.section(region, daily, asof, suspect)
    out = SITE_OUT / region.id
    (out / "sites").mkdir(parents=True, exist_ok=True)
    for old in out.glob("sat-*.png"):     # a layer that went stale must disappear, not linger
        old.unlink()
    satellite_layers = satellite.build(region, out)
    latest = {
        "region": {"id": region.id, "name": region.name, "units": region.units, "map": region.map},
        "beaches": beach_section,
        "oyster_watch": oyster_section,
        "fishing_outlook": fishing_section,
        "tide_strip": _tide_strip(region),
        "shrimp_season": shrimp_section,
        "spillway": spillway_section,
        "vibrio": vibrio_section,
        "satellite": satellite_layers,
        "replay": _replay(region, daily, normals, asof),
        "generated_at": generated_at.isoformat(),
        "asof": asof.strftime("%Y-%m-%d"),
        "season": season_phrase(asof),
        "personas": region.personas,
        "headlines": {p["id"]: _headline(region, findings, p, asof, cards, beach_section, oyster_section, fishing_section, shrimp_section) for p in region.personas},
        "findings": findings,
        "cards": cards,
        "ungauged_rivers": region.extras.get("ungauged_rivers", []),
        "rain_forecast": fc,
        "variables": {k: {"label": v["label"]} for k, v in VARIABLES.items()},
    }
    if beach_geo:
        (out / "beaches.geojson").write_text(json.dumps(beach_geo, separators=(",", ":")))
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
