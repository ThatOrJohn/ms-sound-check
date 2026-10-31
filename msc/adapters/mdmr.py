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


# ---------- season pages (decision 0044): MDMR's own status boxes and season text, quoted as published

PAGES_MAX_AGE = MAX_AGE
_PROPER = {"ms": "Mississippi", "icw": "ICW", "intracoastal": "Intracoastal", "gulfport": "Gulfport", "biloxi": "Biloxi",
           "waterway": "Waterway", "(icw)": "(ICW)"}


def _sentence_case(caps: str) -> str:
    """'MS WATERS NORTH OF INTRACOASTAL WATERWAY (ICW)' -> 'Mississippi waters north of Intracoastal Waterway (ICW)'."""
    words = [_PROPER.get(w.lower(), w.lower()) for w in caps.split()]
    return " ".join(words)[:1].upper() + " ".join(words)[1:]


def _block(rendered: str, start: str, end: str | None) -> str:
    """The page HTML between two heading texts (case-insensitive). Empty if `start` isn't there."""
    m = re.search(re.escape(start), rendered, re.I)
    if not m:
        return ""
    rest = rendered[m.end():]
    e = re.search(re.escape(end), rest, re.I) if end else None
    return rest[:e.start()] if e else rest


def shrimp_status(rendered: str) -> dict:
    """The Shrimp & Crab page's status box: each area's label and the OPEN/CLOSED button after it, plus the footnote."""
    box = _block(rendered, "SHRIMP SEASON STATUS", "SHRIMP ZONES MAP")
    areas, label = [], None
    for m in re.finditer(r"<strong>(.*?)</strong>|elementor-button-text\">(.*?)<", box, re.S):
        if m.group(1):
            label = _text(m.group(1))
        elif label and _text(m.group(2)).upper() in ("OPEN", "CLOSED"):
            starred = label.endswith("*")
            areas.append({"area": _sentence_case(label.rstrip("* ")), "status": _text(m.group(2)).lower(),
                          "footnote": starred})
            label = None
    if not areas:
        raise RuntimeError("no area status found on the shrimp page")
    notes = [t.lstrip("* ").strip() for t in (_text(p) for p in re.findall(r"<p[^>]*>(.*?)</p>", box, re.S))
             if t.startswith("*")]
    note = notes[0] if notes else None
    return {"areas": areas, "note": note[:1].upper() + note[1:] if note else None}


def _paras(html_part: str) -> list[str]:
    return [t for t in (_text(p) for p in re.findall(r"<p[^>]*>(.*?)</p>", html_part, re.S)) if t]


def oyster_season(rendered: str) -> dict:
    """The season page: what MDMR says about the season so far, its orders, and the days with no harvest."""
    info = _block(rendered, "SEASON INFORMATION", "OPENING AND CLOSING ORDERS")
    orders_part = _block(rendered, "OPENING AND CLOSING ORDERS", "closed on Sundays")
    days_part = _block(rendered, "OPENING AND CLOSING ORDERS", "The maps below")
    summary = [re.sub(r"\s*Please refer to this link for daily sunrise times\.?", "", t) for t in _paras(info)]
    orders = [{"title": _text(t), "link": u} for u, t in re.findall(r"<a[^>]+href=\"([^\"]+)\"[^>]*>(.*?)</a>", orders_part, re.S)
              if _text(t).lower().startswith("order")]
    m = re.search(r"<p[^>]*>([^<]*closed on Sundays[^<]*)</p>(.*)", days_part, re.S | re.I)
    no_harvest = {"lead": _text(m.group(1)).rstrip(": ") + ":", "days": [_text(x) for x in re.findall(r"<li[^>]*>(.*?)</li>", m.group(2), re.S)]} if m else None
    if not summary and not orders:
        raise RuntimeError("no season text or orders found on the oyster season page")
    return {"summary": [t for t in summary if t], "orders": orders, "no_harvest": no_harvest}


PARSERS = {"shrimp_status": shrimp_status, "oyster_season": oyster_season}


def fetch_pages(region: Region) -> dict | None:
    """Each configured page, found by slug (or the newest page whose slug matches a pattern) and parsed. A page that
    fails to parse is left out; the others still save."""
    import requests
    cfg = (region.extras or {}).get("mdmr_pages")
    if not cfg:
        return None
    pages, failed = {}, []
    for key, p in cfg["pages"].items():
        params = {"_fields": "slug,link,modified,content", "per_page": 20, "orderby": "modified", "order": "desc"}
        params.update({"slug": p["slug"]} if p.get("slug") else {"search": p["search"]})
        r = requests.get(cfg["api"], params=params, headers=UA, timeout=60)
        r.raise_for_status()
        hits = [x for x in r.json() if p.get("slug") or re.fullmatch(p["slug_pattern"], x.get("slug", ""))]
        if not hits:
            failed.append(key)
            continue
        page = hits[0]
        try:
            body = PARSERS[key](page["content"]["rendered"])
        except RuntimeError:
            failed.append(key)
            continue
        season = re.match(r"(\d{4})-(\d{4})", page["slug"])
        pages[key] = {**body, "link": page["link"], "modified": page["modified"][:10],
                      **({"season": f"{season.group(1)}–{season.group(2)}"} if season else {})}
    if failed and not pages:
        raise RuntimeError(f"no MDMR page parsed ({', '.join(failed)})")
    return {"fetched_at": pd.Timestamp.now(tz="UTC").isoformat(), "pages": pages, "failed": failed}


def save_pages(region: Region, data: dict) -> None:
    region.data_dir.mkdir(parents=True, exist_ok=True)
    (region.data_dir / "mdmr_pages.json").write_text(json.dumps(data, indent=1))


def page(region: Region, key: str) -> dict | None:
    """One parsed page, or None if never fetched, not parsed last time, or the snapshot is older than PAGES_MAX_AGE."""
    p = region.data_dir / "mdmr_pages.json"
    if not p.exists():
        return None
    js = json.loads(p.read_text())
    if pd.Timestamp.now(tz="UTC") - pd.Timestamp(js["fetched_at"]) > PAGES_MAX_AGE:
        return None
    return js["pages"].get(key)
