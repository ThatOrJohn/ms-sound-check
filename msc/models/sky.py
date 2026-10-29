"""Sun and moon for a day on the coast: rise and set times, moon phase and how much of it is lit.

Computed locally with PyEphem (no network, nothing to go stale). Rise and set follow the US Naval Observatory's
convention (upper limb on the horizon, standard refraction), and agree with its tables to the minute (decision 0040).
"""
from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo

import ephem

# Principal phases named on the local day they fall, as almanacs do; other days get the in-between name.
PRINCIPAL = [(ephem.next_new_moon, "new moon"), (ephem.next_first_quarter_moon, "first quarter"),
             (ephem.next_full_moon, "full moon"), (ephem.next_last_quarter_moon, "last quarter")]


def _utc(d: ephem.Date) -> dt.datetime:
    return d.datetime().replace(tzinfo=dt.timezone.utc)


def _event(obs: ephem.Observer, body, fn: str, start: dt.datetime, end: dt.datetime, tz: ZoneInfo) -> str | None:
    """'YYYY-MM-DD HH:MM' local (same form as the tide times) if the event falls on this day, else None."""
    obs.date = start.replace(tzinfo=None)
    try:
        t = _utc(getattr(obs, fn)(body))
    except (ephem.AlwaysUpError, ephem.NeverUpError):
        return None
    if t >= end:
        return None
    t = (t + dt.timedelta(seconds=30)).replace(second=0, microsecond=0)  # nearest minute, as the USNO rounds
    return t.astimezone(tz).strftime("%Y-%m-%d %H:%M")


def phase_name(start: dt.datetime, end: dt.datetime) -> str:
    """'full moon' etc. on the day it happens; otherwise waxing/waning crescent/gibbous."""
    begin = ephem.Date(start.replace(tzinfo=None))
    for fn, name in PRINCIPAL:
        if _utc(fn(begin)) < end:
            return name
    noon = start + (end - start) / 2
    waxing = _utc(ephem.next_full_moon(begin)) < _utc(ephem.next_new_moon(begin))
    m = ephem.Moon(noon.replace(tzinfo=None))
    shape = "gibbous" if m.phase > 50 else "crescent"
    return f"{'waxing' if waxing else 'waning'} {shape}"


def day(lat: float, lon: float, tz_name: str, date: str) -> dict:
    """Sun and moon for one local date ('YYYY-MM-DD') at a point."""
    tz = ZoneInfo(tz_name)
    local = dt.datetime.fromisoformat(date).replace(tzinfo=tz)
    start = local.astimezone(dt.timezone.utc)
    end = (local + dt.timedelta(days=1)).astimezone(dt.timezone.utc)   # DST days are 23 or 25 hours
    obs = ephem.Observer()
    obs.lat, obs.lon = str(lat), str(lon)
    obs.pressure, obs.horizon = 0, "-0:34"
    sun, moon = ephem.Sun(), ephem.Moon()
    noon = start + (end - start) / 2
    return {
        "sunrise": _event(obs, sun, "next_rising", start, end, tz),
        "sunset": _event(obs, sun, "next_setting", start, end, tz),
        "moonrise": _event(obs, moon, "next_rising", start, end, tz),
        "moonset": _event(obs, moon, "next_setting", start, end, tz),
        "moon_phase": phase_name(start, end),
        "moon_lit_pct": round(ephem.Moon(noon.replace(tzinfo=None)).phase),
    }
