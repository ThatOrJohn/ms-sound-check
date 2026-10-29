"""Fishing outlook: the next weekend (or the next three days, midweek) at a glance.

Facts only, plus plain verdicts with stated thresholds: wind and waves from the NWS forecasts, tides from NOAA, sun
and moon computed locally, muddy-water risk from recent rain and river flow, and water temperature/salinity from our
stations.
"""
from __future__ import annotations

import pandas as pd

from ..adapters import nws, tides as tide_src
from ..config import Region
from . import sky

# Wind verdicts (sustained mph, the NWS forecast's upper bound; each band includes its top value).
WIND = [(10, "light", "Light wind, a good day to be out."),
        (15, "moderate", "Moderate wind, some chop in open water."),
        (20, "breezy", "Breezy, rough in the open Sound; stick to protected water."),
        (999, "windy", "Windy, small boats should stay in.")]


def _days(asof: pd.Timestamp) -> list[pd.Timestamp]:
    """This coming Saturday and Sunday; on Fri-Sun, the rest of this weekend; otherwise next 3 days if the
    weekend is more than 4 days off."""
    wd = asof.weekday()  # Mon=0
    if wd == 4:          # Friday: Fri-Sun
        return [asof + pd.Timedelta(days=i) for i in range(3)]
    if wd == 5:          # Saturday: Sat-Sun
        return [asof, asof + pd.Timedelta(days=1)]
    if wd == 6:          # Sunday: the weekend's nearly over, show the next three days
        return [asof + pd.Timedelta(days=i) for i in range(3)]
    sat = asof + pd.Timedelta(days=5 - wd)
    if (sat - asof).days > 4:
        return [asof + pd.Timedelta(days=i) for i in range(3)]
    return [sat, sat + pd.Timedelta(days=1)]


def _verdict(mph: int | None):
    if mph is None:
        return None, None
    for top, key, text in WIND:
        if mph <= top:
            return key, text
    return None, None


def wind_text(p: dict | None) -> str | None:
    """'SE 10–15 mph' from one NWS forecast period."""
    if not p or p.get("wind_mph_hi") is None:
        return None
    if p.get("wind_mph_lo") is not None and p["wind_mph_lo"] != p["wind_mph_hi"]:
        return f"{p['wind_dir']} {p['wind_mph_lo']}–{p['wind_mph_hi']} mph"
    return f"{p['wind_dir']} {p['wind_mph_hi']} mph"


def _muddy(region: Region, daily: pd.DataFrame, asof: pd.Timestamp, rain_fc_in: float | None) -> dict:
    """Heuristic runoff risk: local rain in the last 3 days, rivers vs. normal, and rain in the forecast."""
    def rain_in(site, days):
        r = daily[(daily.site == site) & (daily["var"] == "rain") & (daily.date < asof) &
                  (daily.date >= asof - pd.Timedelta(days=days))]
        return float(r.value.sum()) / 25.4 if len(r) else None
    local = rain_in("local-biloxi", 3)
    reasons, score = [], 0
    if local is not None and local >= 1.0:
        score += 2; reasons.append(f"{local:.1f} in of rain on the coast in the last 3 days")
    elif local is not None and local >= 0.5:
        score += 1; reasons.append(f"{local:.1f} in of rain on the coast in the last 3 days")
    return {"score": score, "reasons": reasons, "local_rain_3d_in": round(local, 2) if local is not None else None,
            "forecast_rain_in": rain_fc_in}


def section(region: Region, daily: pd.DataFrame, asof: pd.Timestamp, cards: list[dict],
            rain_forecast: pd.DataFrame | None) -> dict | None:
    periods = nws.load_forecast(region)
    tide_rows = tide_src.load(region)
    marine = nws.load_marine(region)
    if not periods and not tide_rows:
        return None
    days = _days(asof)
    lat, lon = region.map.get("center", [30.30, -88.95])
    out_days = []
    for d in days:
        key = d.strftime("%Y-%m-%d")
        ps = [p for p in periods if p["start"][:10] == key]
        day = next((p for p in ps if p["is_day"]), None)
        night = next((p for p in ps if not p["is_day"]), None)
        mph = max([p["wind_mph_hi"] for p in ps if p.get("wind_mph_hi") is not None], default=None)
        vkey, vtext = _verdict(day["wind_mph_hi"] if day and day.get("wind_mph_hi") is not None else mph)
        tl = [t for t in tide_rows if t["time"][:10] == key]
        out_days.append({
            "date": key, "label": d.strftime("%A"),
            "wind": wind_text(day),
            "wind_mph_hi": day["wind_mph_hi"] if day else mph,
            "sky": day["short"] if day else (night["short"] if night else None),
            "rain_pct": max([p["rain_pct"] or 0 for p in ps], default=None) if ps else None,
            "high_f": day["temp_f"] if day else None,
            "verdict": vkey, "verdict_text": vtext,
            "tides": tl,
            "waves": next((m["waves"] for m in marine if m["date"] == key and m["is_day"]), None),
            "sky_times": sky.day(lat, lon, region.timezone, key),
        })
    # Water now: average across live open-Sound stations.
    def live(var):
        vals = [c["vars"][var] for c in cards if c["kind"] == "sound" and var in c["vars"]
                and c["vars"][var].get("value") is not None and not c["vars"][var].get("stale")
                and not c["vars"][var].get("suspect")]
        return vals
    temps = live("water_temp")
    sal = [(c["short"], c["vars"]["salinity"]["value"]) for c in cards if c["kind"] == "sound"
           and c["vars"].get("salinity", {}).get("value") is not None and not c["vars"]["salinity"].get("stale")
           and not c["vars"]["salinity"].get("suspect") and not c.get("retired")]
    temp = round(sum(v["value"] for v in temps) / len(temps)) if temps else None
    t_change = [v.get("change_7d") for v in temps if v.get("change_7d") is not None]
    rain_fc = None
    if rain_forecast is not None and len(rain_forecast):
        f = rain_forecast[(rain_forecast.site == "local-biloxi")]
        if len(f):
            f = f[pd.to_datetime(f.date).dt.strftime("%Y-%m-%d").isin([d["date"] for d in out_days])]
            rain_fc = round(float(f.value.sum()) / 25.4, 2) if len(f) else None
    muddy = _muddy(region, daily, asof, rain_fc)
    rivers = [c for c in cards if c["kind"] == "river"]
    high_rivers = [c["short"] for c in rivers if c["vars"].get("flow", {}).get("band") in ("above", "high")]
    if high_rivers:
        muddy["score"] += 2 if any(c["vars"]["flow"].get("band") == "high" for c in rivers) else 1
        muddy["reasons"].append(f"{' and '.join(high_rivers)} running above normal")
    if rain_fc is not None and rain_fc >= 1.0:
        muddy["reasons"].append(f"about {rain_fc:.1f} in of rain forecast on the coast")
        muddy["score"] += 1
    muddy["level"] = "muddy" if muddy["score"] >= 3 else "some runoff" if muddy["score"] >= 1 else "clean"
    return {
        "days": out_days, "weekend": all(pd.Timestamp(d["date"]).weekday() >= 5 for d in out_days),
        "water": {"temp_f": temp, "temp_change_7d": round(sum(t_change) / len(t_change), 1) if t_change else None,
                  "saltiest": max(sal, key=lambda x: x[1]) if sal else None,
                  "freshest": min(sal, key=lambda x: x[1]) if sal else None},
        "muddy": muddy,
        "tide_stations": region.extras.get("tides", []),
        "marine_zone": region.extras.get("marine_zone"),
        "wind_bands": [{"below_mph": top, "label": key} for top, key, _ in WIND],
    }


def headline(sec: dict) -> str | None:
    if not sec or not sec.get("days"):
        return None
    usable = [d for d in sec["days"] if d.get("verdict")]
    if not usable:
        return None
    best = min(usable, key=lambda d: (d["wind_mph_hi"] or 99, d["rain_pct"] or 0))
    calm = [d for d in usable if d["verdict"] == "light"]
    span = "this weekend" if sec.get("weekend") else "the next few days"
    if len(calm) == len(usable):
        return f"Light wind {span}. {best['label']} looks best ({best['wind']}, {best['sky'].lower() if best['sky'] else 'no sky forecast'})."
    if not calm:
        return f"No calm day {span}; {best['label']} is the least windy ({best['wind']})."
    return f"{best['label']} looks best {span}: {best['wind']}, {best['sky'].lower() if best['sky'] else 'no sky forecast'}."
