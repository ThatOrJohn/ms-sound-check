"""MDMR news releases from the agency's public WordPress REST API (dmr.ms.gov/wp-json; free, no key).

Each configured topic is a search within the News & Updates category plus a title filter, so only
season notices come through (openings, closures, area changes), not license sales or relief programs.
Legal notices (Public Notices category) repeat the same orders in statute language; the press
releases are the plain-language version.

The run keeps a snapshot (mdmr_notices.json). A snapshot older than MAX_AGE is ignored, so the page
drops the notices rather than show a list that may have missed a closure.
"""
from __future__ import annotations

import html
import json
import re

import pandas as pd

from ..config import Region

UA = {"User-Agent": "ms-sound-check (https://github.com/; hobby coastal conditions page)"}
MAX_AGE = pd.Timedelta(days=2)
SUMMARY_CHARS = 260
_PREFIX = re.compile(r"^\s*\d{2}-\d+-CWS\s*\|\s*[A-Z][a-z]+\.? \d{1,2}, \d{4}\s*(BILOXI, Miss\.\s*[–—-]\s*)?")


def _text(rendered: str) -> str:
    t = re.sub(r"<[^>]+>", " ", html.unescape(rendered or ""))
    t = re.sub(r"\[…\]|\[\.\.\.\]", "", t).replace("\xa0", " ")
    return re.sub(r"\s+", " ", t).strip()


def summary(excerpt: str) -> str:
    """Excerpt minus the release number and dateline, cut at a word boundary."""
    t = _PREFIX.sub("", _text(excerpt))
    if len(t) <= SUMMARY_CHARS:
        return t
    return t[:SUMMARY_CHARS].rsplit(" ", 1)[0].rstrip(",;:") + "…"


def normalize(posts: list[dict], title_pattern: str, exclude: str | None = None) -> list[dict]:
    pat = re.compile(title_pattern, re.I)
    skip = re.compile(exclude, re.I) if exclude else None
    out = []
    for p in posts:
        title = _text(p.get("title", {}).get("rendered", ""))
        if not pat.search(title) or (skip and skip.search(title)):
            continue
        out.append({"id": p.get("id"), "date": (p.get("date") or "")[:10], "title": title,
                    "summary": summary(p.get("excerpt", {}).get("rendered", "")), "link": p.get("link")})
    return sorted(out, key=lambda n: n["date"], reverse=True)


def fetch(region: Region) -> dict | None:
    import requests
    cfg = (region.extras or {}).get("mdmr_notices")
    if not cfg:
        return None
    topics = {}
    for topic, t in cfg["topics"].items():
        params = {"search": t["search"], "categories": ",".join(map(str, cfg["categories"])), "per_page": 30,
                  "orderby": "date", "order": "desc", "_fields": "id,date,link,title,excerpt"}
        r = requests.get(cfg["api"], params=params, headers=UA, timeout=60)
        r.raise_for_status()
        posts = r.json()
        if not isinstance(posts, list):
            raise RuntimeError(f"unexpected response: {str(posts)[:200]}")
        topics[topic] = normalize(posts, t["title"], t.get("exclude"))
    return {"fetched_at": pd.Timestamp.now(tz="UTC").isoformat(), "source": cfg.get("name"), "topics": topics}


def save(region: Region, data: dict) -> None:
    region.data_dir.mkdir(parents=True, exist_ok=True)
    (region.data_dir / "mdmr_notices.json").write_text(json.dumps(data, indent=1))


def load(region: Region, topic: str) -> list[dict] | None:
    """Notices for one topic, or None if never fetched or the snapshot is older than MAX_AGE."""
    p = region.data_dir / "mdmr_notices.json"
    if not p.exists():
        return None
    js = json.loads(p.read_text())
    if pd.Timestamp.now(tz="UTC") - pd.Timestamp(js["fetched_at"]) > MAX_AGE:
        return None
    return js["topics"].get(topic)


def recent(region: Region, topic: str, asof: pd.Timestamp, days: int = 365, count: int = 5) -> dict:
    """The newest notices for one topic from the past `days`, for a section's "Latest from MDMR" list.
    `available` is False when the snapshot is missing or stale (the page then says it couldn't check)."""
    notices = load(region, topic)
    cutoff = (asof - pd.Timedelta(days=days)).strftime("%Y-%m-%d")
    cfg = (region.extras or {}).get("mdmr_notices") or {}
    return {"notices": [n for n in notices or [] if cutoff <= n["date"] <= asof.strftime("%Y-%m-%d")][:count],
            "available": notices is not None, "link": cfg.get("topics", {}).get(topic, {}).get("link"),
            "source": cfg.get("name")}


def headline(notices: list[dict], asof: pd.Timestamp, days: int = 7) -> str | None:
    """MDMR's newest notice, in its own words, if it's from the past `days`."""
    if not notices or notices[0]["date"] < (asof - pd.Timedelta(days=days)).strftime("%Y-%m-%d"):
        return None
    n = notices[0]
    return f"MDMR, {pd.Timestamp(n['date']).strftime('%b %-d')}: {n['title'].rstrip('.')}."
