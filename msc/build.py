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
from .config import REFERENCE, SITE_OUT, VARIABLES, Region
from .indicators import SEVERITY, _sites_for, evaluate, is_suspect, record_means
from .units import convert, fmt, season_phrase, unit_label

SPARK_DAYS = 30
HISTORY_DAYS = 365
NOW_MAX_AGE = pd.Timedelta(hours=4)   # a "now" reading older than this is hidden, not shown
REFERENCE_MAX_DAYS = 3                # a reference site's daily mean older than this is hidden


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


def _reference(region, daily, asof) -> list[dict]:
    """Reference salinity sites (decision 0019) for the map's edge: newest daily mean, and how far they sit from
    our nearest station. Shown for context only; they never feed flags, models or the salinity fill."""
    out = []
    ours = [x for x in region.sites if x["kind"] == "sound" and not x.get("retired") and x.get("lat") is not None]
    for ref in region.extras.get("reference", []):
        if ref.get("lat") is None:
            continue
        s = daily[(daily.site == ref["id"]) & (daily["var"] == "salinity") & (daily.date <= asof)].sort_values("date")
        fresh = len(s) and (asof - s.date.iloc[-1]).days <= REFERENCE_MAX_DAYS
        near = min(ours, key=lambda x: _km(ref, x), default=None)
        out.append({
            **{k: ref.get(k) for k in ("id", "name", "place", "lat", "lon", "link")},
            "salinity": _r(s.value.iloc[-1], 1) if fresh else None,
            "date": s.date.iloc[-1].strftime("%Y-%m-%d") if fresh else None,
            "nearest": near["short"] if near else None, "km": round(_km(ref, near) / 5) * 5 if near else None,
            "east": bool(near and ref["lon"] > near["lon"]),
        })
    return out


def _km(a, b) -> float:
    lat1, lon1, lat2, lon2 = map(np.radians, (a["lat"], a["lon"], b["lat"], b["lon"]))
    h = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return float(2 * 6371 * np.arcsin(np.sqrt(h)))


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


def _cell(dates: pd.DatetimeIndex) -> np.ndarray:
    """Column 0-365 in a 366-day row, so Mar 1 lines up in leap and common years (Feb 29 is empty in common ones)."""
    leap = dates.is_leap_year
    return np.asarray(dates.dayofyear - 1 + ((~leap) & (dates.month > 2)))


def _notable(region) -> dict[int, dict]:
    """Hand-kept context per year (data/notable_years.csv): its note, a short `tag` for the history picture's margin
    and a `day` the map replay can jump to. Spillway years are tagged "spillway" even without a row."""
    cfg = region.extras.get("similar_years") or {}
    p = REFERENCE / cfg.get("notes", "notable_years.csv")
    out = {}
    if p.exists():
        for r in pd.read_csv(p, comment="#", dtype=str).fillna("").itertuples():
            out[int(r.year)] = {"note": r.note or None, "tag": getattr(r, "tag", "") or None, "day": getattr(r, "day", "") or None}
    from .models import spillway
    for o in spillway.openings(region):
        n = out.setdefault(o["year"], {"note": None, "tag": None, "day": None})
        if "spillway" not in (n["tag"] or ""):
            n["tag"] = f"spillway, {n['tag']}" if n["tag"] else "spillway"
    return out


def _year_dots(region, daily, asof) -> dict[tuple[str, str], dict]:
    """For each station a `record` indicator ranks: every year's mean over the same window ending on today's date
    (decision 0032). Built by the same function as the record text, so a dot's rank and the sentence always agree."""
    out = {}
    for cfg in region.indicators:
        if cfg["type"] != "record":
            continue
        for site in _sites_for(region, cfg):
            got = record_means(cfg, daily, site["id"], asof)
            if got is None:
                continue
            means = got[0]
            now = means[asof.year]
            out[(site["id"], cfg["var"])] = {
                "window": cfg.get("window", 14), "season": season_phrase(asof).replace(" ", "-"),
                "points": [[y, _r(convert(cfg["var"], means[y], region.units), 2)] for y in sorted(means)],
                "rank_high": 1 + sum(v > now for v in means.values()),
                "rank_low": 1 + sum(v < now for v in means.values()),
                "of": len(means), "record": cfg["id"]}
    return out


def _history(region, daily, asof, qcs, out) -> dict | None:
    """Every salinity station's whole record, one row per year (decision 0028), to history/<slug>.json, and a
    summary for latest.json: which stations the home section shows, and its one-line takeaway."""
    cfg = region.extras.get("history")
    if not cfg:
        return None
    from . import history
    lo, hi = cfg["fresh_below"], cfg["salty_above"]
    (out / "history").mkdir(exist_ok=True)
    notable = _notable(region)
    stations = {}
    for site in region.sites:
        if site["kind"] not in ("sound", "estuary") or "salinity" not in site["vars"]:
            continue
        s = history.series(daily, site["id"], "salinity", asof)
        if qcs.get(site["id"], {}).get("suspect"):   # QC looks at the last 3 days
            s = s[s.index <= asof - pd.Timedelta(days=3)]
        if s.empty:
            continue
        counted, cov = set(history.good_years(s, asof)), history.coverage(s)
        years = []
        for y, g in s.groupby(s.index.year):
            vals = [None] * 366
            for i, v in zip(_cell(g.index), g.values):
                vals[i] = _r(v, 1)
            years.append({"year": int(y), "counted": int(y) in counted, "coverage": _r(cov[y]),
                          "mean": _r(g.mean(), 1), "under": int((g < lo).sum()), "over": int((g > hi).sum()),
                          "values": vals})
        slug = site.get("slug") or slugify(site["short"])
        (out / "history" / f"{slug}.json").write_text(json.dumps(
            {"id": site["id"], "slug": slug, "short": site["short"], "name": site["name"], "asof": asof.strftime("%Y-%m-%d"),
             "fresh_below": lo, "salty_above": hi, "years": years,
             "tags": {str(y): n["tag"] for y, n in notable.items() if n["tag"] and y in {r["year"] for r in years}}},
            separators=(",", ":")))
        stations[site["id"]] = {"slug": slug, "short": site["short"], "first": years[0]["year"],
                                "years": [y for y in years if y["counted"]]}
    home = [sid for sid in cfg.get("home", []) if sid in stations]
    if not home:
        return None
    return {"since": min(st["first"] for st in stations.values()), "fresh_below": lo, "salty_above": hi,
            "home": [{"id": sid, "slug": stations[sid]["slug"], "short": stations[sid]["short"]} for sid in home],
            "stations": {sid: st["slug"] for sid, st in stations.items()},
            "takeaway": _history_takeaway(region, stations.get(cfg.get("takeaway_site", home[0])), lo, hi)}


def _history_takeaway(region, st, lo, hi) -> str | None:
    """'At Biloxi Back Bay, 2021 was fresher than the spillway year 2019: ...'. Counts only; never a forecast."""
    if not st or len(st["years"]) < 10:
        return None
    from .models import spillway
    ys = {y["year"]: y for y in st["years"]}
    fresh = max(ys.values(), key=lambda y: y["under"])
    salt = max(ys.values(), key=lambda y: y["over"])
    spill = [ys[y] for y in sorted({o["year"] for o in spillway.openings(region)}) if y in ys]
    big = max(spill, key=lambda y: y["under"], default=None)
    if big and big["year"] != fresh["year"] and big["under"] < fresh["under"]:
        first = (f"At {st['short']}, {fresh['year']} was fresher than the spillway year {big['year']}: "
                 f"{fresh['under']} days under {lo} ppt, vs. {big['under']}.")
    else:
        first = f"At {st['short']}, {fresh['year']} was the freshest year: {fresh['under']} days under {lo} ppt."
    # "Most years have fewer than N": the smallest multiple of 5 that more than half the years stay under.
    n = next(n for n in range(5, 370, 5) if sum(y["over"] < n for y in ys.values()) > len(ys) / 2)
    return f"{first} {salt['year']} was the saltiest, with {salt['over']} days over {hi} ppt; most years have fewer than {n}."


def _similar_years(region, daily, asof) -> dict | None:
    """Past years whose rivers over the last N days looked most like this year's (decision 0028). Background only:
    the output never says what came next in those years (0008)."""
    cfg = region.extras.get("similar_years")
    if not cfg:
        return None
    from . import history
    days, need = cfg["days"], cfg["min_days"]

    def window(s, year):   # log10 flow on the same calendar days, keyed by month-day so leap years line up
        end = history.same_day(asof, year)
        w = s[(s.index > end - pd.Timedelta(days=days)) & (s.index <= end)]
        w = w[w > 0]
        return pd.Series(np.log10(w.values), index=w.index.strftime("%m-%d"))

    series = {sid: history.series(daily, sid, "flow", asof) for sid in cfg["rivers"]}
    now = {sid: window(s, asof.year) for sid, s in series.items()}
    if any(len(w) < need for w in now.values()):
        return None
    years = set.intersection(*(set(history.good_years(s, asof)) for s in series.values())) - {asof.year}
    rms = {}
    for y in years:
        sq = []
        for sid, s in series.items():
            j = pd.concat([now[sid], window(s, y)], axis=1, join="inner").dropna()
            if len(j) < need:
                break
            sq.append(((j.iloc[:, 0] - j.iloc[:, 1]) ** 2).values)
        else:
            rms[y] = float(np.sqrt(np.concatenate(sq).mean()))
    if len(rms) < cfg.get("min_years", 10):
        return None
    best = [y for y in sorted(rms, key=rms.get)[:cfg.get("top", 3)] if rms[y] <= cfg.get("max_rms", 0.5)]
    if not best:
        return None
    notes = {y: n["note"] for y, n in _notable(region).items() if n["note"]}
    link = region.site(cfg["link_site"]) if cfg.get("link_site") else None
    return {"days": days, "label": cfg["label"], "compared": len(rms),
            "link_slug": (link.get("slug") or slugify(link["short"])) if link else None,
            "link_short": link["short"] if link else None,
            "years": [{"year": int(y), "rms": _r(rms[y]), "note": notes.get(y)} for y in best]}


REPLAY_DAYS = 30


def _normal_table(normals, site_id, var) -> np.ndarray | None:
    """Normals for one site as a (366, 5) array indexed by day of year, NaN where missing."""
    if normals.empty:
        return None
    n = normals[(normals.site == site_id) & (normals["var"] == var)]
    if n.empty:
        return None
    arr = np.full((366, len(nm.PCTS)), np.nan)
    arr[n.doy.values] = n[[f"p{p}" for p in nm.PCTS]].values
    return arr


def _pct(v: float, row: np.ndarray) -> int | None:
    """nm.percentile_of on a normals array row."""
    if np.isnan(v) or np.isnan(row).any():
        return None
    if v <= row[0]:
        return 5 if v < row[0] else 10
    if v >= row[-1]:
        return 95 if v > row[-1] else 90
    return round(float(np.interp(v, row, nm.PCTS)))


def _replay_days(region, daily, normals, days: pd.DatetimeIndex) -> dict:
    """For each day: measured salinity at every Sound and river-mouth station (retired ones too, while they ran; never
    an estimate), each river's flow percentile against its normals, and the day's mean wind over the Sound."""
    span = daily[(daily.date >= days[0]) & (daily.date <= days[-1])]
    out = {"salinity": {}, "flow_pct": {}, "wind": None}
    for site in region.sites:
        if site["kind"] in ("sound", "estuary") and "salinity" in site["vars"]:
            s = span[(span.site == site["id"]) & (span["var"] == "salinity")].drop_duplicates("date").set_index("date").value
            vals = [None if d not in s.index or is_suspect("salinity", s[d]) else _r(s[d], 1) for d in days]
            if any(v is not None for v in vals):
                out["salinity"][site["id"]] = vals
        elif site["kind"] == "river" and not site.get("retired"):
            arr = _normal_table(normals, site["id"], "flow")
            if arr is None:
                continue
            s = span[(span.site == site["id"]) & (span["var"] == "flow")].drop_duplicates("date").set_index("date").value
            vals = [_pct(s[d], arr[min(d.dayofyear, 365)]) if d in s.index else None for d in days]
            if any(v is not None for v in vals):
                out["flow_pct"][site["id"]] = vals
    wind = next((x for x in region.sites if x["kind"] == "wind"), None)
    if wind:
        w = span[span.site == wind["id"]].pivot_table(index="date", columns="var", values="value")
        if {"wind_u", "wind_v"} <= set(w.columns) and len(w):
            col = lambda c: [_r(w[c].get(d), 1) if c in w and d in w.index and pd.notna(w[c].get(d)) else None for d in days]
            out["wind"] = {"u": col("wind_u"), "v": col("wind_v"), "max": col("wind_max")}
    return out


def _replay(region, daily, normals, asof) -> dict:
    """The last 30 days, for the map's replay slider (in latest.json, so the default replay needs no extra fetch)."""
    days = pd.date_range(asof - pd.Timedelta(days=REPLAY_DAYS - 1), asof)
    return {"days": [d.strftime("%Y-%m-%d") for d in days], **_replay_days(region, daily, normals, days)}


def _replay_years(region, daily, normals, asof, out) -> dict | None:
    """replay/<year>.json for every year with salinity on record (decision 0033), fetched only when someone picks
    that year, plus the index latest.json carries: the years, every station's position (retired ones too) and the
    notable days the picker offers as shortcuts."""
    ids = [s["id"] for s in region.sites if s["kind"] in ("sound", "estuary") and "salinity" in s["vars"]]
    sal = daily[daily.site.isin(ids) & (daily["var"] == "salinity") & (daily.date <= asof)]
    if sal.empty:
        return None
    (out / "replay").mkdir(exist_ok=True)
    years = list(range(int(sal.date.dt.year.min()), asof.year + 1))
    for y in years:
        days = pd.date_range(f"{y}-01-01", min(pd.Timestamp(f"{y}-12-31"), asof))
        body = {"year": y, "start": days[0].strftime("%Y-%m-%d"), "n": len(days), **_replay_days(region, daily, normals, days)}
        (out / "replay" / f"{y}.json").write_text(json.dumps(body, separators=(",", ":")))
    notable = _notable(region)
    from .models import spillway
    shortcuts = [{"date": n["day"], "label": n["tag"].split(", ")[-1] if n["tag"] else str(y)}
                 for y, n in notable.items() if n["day"]]
    shortcuts += [{"date": o["opened"], "label": "Spillway opens"} for o in spillway.openings(region)]
    shortcuts = sorted((x for x in shortcuts if str(years[0]) <= x["date"][:4] and x["date"] <= asof.strftime("%Y-%m-%d")),
                       key=lambda x: x["date"])
    return {"years": years,
            "sites": [{k: s.get(k) for k in ("id", "short", "lat", "lon")} | {"retired": bool(s.get("retired"))}
                      for s in region.sites if s["id"] in ids and s.get("lat") is not None],
            "shortcuts": shortcuts}


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
    if focus[0] == "oyster":             # likewise MDMR's own oyster season notice
        from .models import oyster as oyster_model
        oh = oyster_model.headline(oyster_watch, asof)
        if oh:
            parts.append(oh)
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
    dots = {k: v for k, v in _year_dots(region, daily, asof).items() if k not in suspect}
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
            if (site["id"], v) in dots and not out.get("stale") and not out.get("suspect"):
                out["years"] = dots[(site["id"], v)]
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
    spillway_section = spillway.section(region, daily, asof, normals)
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
        "reference": _reference(region, daily, asof),
        "replay": _replay(region, daily, normals, asof),
        "replay_index": _replay_years(region, daily, normals, asof, out),
        "history": _history(region, daily, asof, qcs, out),
        "similar_years": _similar_years(region, daily, asof),
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
