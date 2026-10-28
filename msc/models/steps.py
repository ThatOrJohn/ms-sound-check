"""Step detection: a sudden, lasting shift in a station's daily level.

One station stepping is suspect (a fouled or recalibrated sensor looks the same). Two or more stations
stepping the same way within a few days is a real event: Gulf water pushed into the Sound, or fresh water
pushed out over it. Only the matching steps become a finding.

A station "steps" on day t when its last `AFTER` days all sit well beyond the median of the `BEFORE` days
before them, and the median shift is at least `min_step`. Readings that fail QC are ignored, so a sensor
reading past the plausible ceiling can't stand in for a second station.

Stateless: every build recomputes from the daily table, so no event history is stored.
"""
from __future__ import annotations

import pandas as pd

from ..config import VARIABLES, Region

BEFORE, AFTER = 7, 3
HELD = 0.5            # every "after" day must be at least this share of the shift beyond the "before" median
MATCH_DAYS = 3        # steps at different stations match when their onsets are this close
RECENT_DAYS = 7       # an event shows for a week after its onset
MIN_BEFORE = 5


def steps(s: pd.Series, min_step: float) -> pd.DataFrame:
    """Days on which `s` (daily values, any gaps) has just stepped. Columns: dir (+1/-1), size, onset."""
    s = s.reindex(pd.date_range(s.index.min(), s.index.max()))
    before = s.shift(AFTER).rolling(BEFORE, min_periods=MIN_BEFORE).median()
    after = s.rolling(AFTER, min_periods=AFTER)
    size = after.median() - before
    held_up = after.min() - before >= HELD * size
    held_dn = before - after.max() >= HELD * -size
    up, dn = (size >= min_step) & held_up, (size <= -min_step) & held_dn
    out = pd.DataFrame({"dir": up.astype(int) - dn.astype(int), "size": size})
    out = out[out.dir != 0]
    out["onset"] = out.index - pd.Timedelta(days=AFTER - 1)
    return out


def _first_of_each(st: pd.DataFrame) -> pd.DataFrame:
    """A step stays flagged for a few days; keep the first day of each run in one direction."""
    new = (st.index.to_series().diff().dt.days.fillna(99) > MATCH_DAYS) | (st.dir != st.dir.shift())
    return st[new]


def events(per_site: dict[str, pd.DataFrame], lead: float = 0) -> list[dict]:
    """Group the first steps of each station into events: >= 2 stations, same direction, onsets within MATCH_DAYS,
    and at least one step of `lead` or more (the rest only need to clear the detection threshold)."""
    flat = [(site, row.dir, row.onset, row.size) for site, st in per_site.items()
            for row in _first_of_each(st).itertuples()]
    out = []
    for direction in (1, -1):
        flat_d = sorted((f for f in flat if f[1] == direction), key=lambda f: f[2])
        group: list[tuple] = []
        for f in flat_d + [None]:
            if f is not None and (not group or (f[2] - group[-1][2]).days <= MATCH_DAYS):
                group.append(f)
                continue
            if len({g[0] for g in group}) >= 2 and max(abs(g[3]) for g in group) >= lead:
                out.append({"dir": direction, "onset": group[0][2],
                            "sites": {g[0]: round(float(g[3]), 1) for g in group}})
            group = [f] if f is not None else []
    return sorted(out, key=lambda e: e["onset"])


def step_events(region: Region, cfg: dict, daily: pd.DataFrame, normals: pd.DataFrame, asof: pd.Timestamp):
    var = cfg["var"]
    ceiling = VARIABLES.get(var, {}).get("suspect_above")
    sites = [s for s in region.sites if s["kind"] in cfg["kinds"] and var in s["vars"] and not s.get("retired")]
    per_site = {}
    for site in sites:
        s = daily[(daily.site == site["id"]) & (daily["var"] == var) & (daily.date <= asof)]
        if s.empty or (asof - s.date.max()).days > cfg.get("max_age_days", 3):
            continue
        s = s.drop_duplicates("date").set_index("date").value.sort_index()
        if ceiling is not None:
            s = s.where(s <= ceiling)
        s = s.dropna()
        if len(s) > BEFORE + AFTER:
            per_site[site["id"]] = steps(s, cfg["min_step"])
    out = []
    for e in events(per_site, cfg["lead_step"]):
        if (asof - e["onset"]).days > RECENT_DAYS:
            continue
        fill = {"places": _join([region.site(sid)["name"] for sid in e["sites"]]), "n": len(e["sites"]),
                "change": f"{max(abs(x) for x in e['sites'].values()):.0f}",
                "when": e["onset"].strftime("%B %-d"), "unit": VARIABLES[var]["unit"]}
        way = "up" if e["dir"] > 0 else "down"
        finding = {"indicator": cfg["id"], "site": None, "var": var, "severity": "notice",
                   "topics": cfg.get("topics", []), "date": e["onset"].strftime("%Y-%m-%d"),
                   "sites": list(e["sites"]), "text": cfg[f"{way}_text"].format(**fill),
                   "short": cfg[f"{way}_short"].format(**fill)}
        # "lead" marks a finding that reaches a headline only by being promoted here, never as a persona's own model
        finding["lead"] = cfg.get("lead_topics", []) if len(e["sites"]) >= cfg.get("lead_min_stations", 99) else []
        out.append(finding)
    return out


def _join(xs: list[str]) -> str:
    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " and " + xs[-1]
