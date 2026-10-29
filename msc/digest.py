"""Weekly digest (decision 0031): one short entry a week, kept in the store, published as RSS and posted to Bluesky.

The scheduled build adds an entry on the first run on or after `digest.weekday` at `digest.hour` (region time), from
the same latest.json the page shows, so the digest never says anything the site doesn't. `python -m msc post` posts
the newest unposted entry when Bluesky credentials are set, and does nothing otherwise.
"""
from __future__ import annotations

import json
import logging
import os

import pandas as pd

from .config import SITE_OUT, Region
from .indicators import SEVERITY

log = logging.getLogger(__name__)
BSKY = "https://bsky.social/xrpc"
POST_MAX = 300          # Bluesky's limit, in graphemes; our text is plain ASCII-ish, so characters are close enough


def _path(region: Region):
    return region.data_dir / "digest.json"


def load(region: Region) -> list[dict]:
    p = _path(region)
    return json.loads(p.read_text()) if p.exists() else []


def _save(region: Region, entries: list[dict]) -> None:
    region.data_dir.mkdir(parents=True, exist_ok=True)
    _path(region).write_text(json.dumps(entries, indent=1))
    out = SITE_OUT / region.id
    out.mkdir(parents=True, exist_ok=True)
    (out / "digest.json").write_text(json.dumps([{k: v for k, v in e.items() if k != "posted"} for e in entries],
                                                separators=(",", ":")))


def compose(region: Region, latest: dict, now: pd.Timestamp) -> dict:
    """This week's entry: the Coast headline, then up to three signals it doesn't already say, then the beaches."""
    headline = latest["headlines"].get("general", "")
    lines = []
    # Most serious first; among notices, "in the record" lines before plain "running low" ones.
    for f in sorted(latest["findings"], key=lambda f: (-SEVERITY.get(f["severity"], 0), "rank" not in f)):
        if "general" in f["topics"] and f["text"] not in headline and len(lines) < 3:
            lines.append(f.get("short") or f["text"])
    b = latest.get("beaches")
    if b and b.get("total") and "beaches" not in headline:
        flagged = b["counts"]["advisory"] + b["counts"]["closure"]
        lines.append(f"All {b['total']} monitored beaches are clear for swimming, per MDEQ." if not flagged else
                     f"MDEQ has {flagged} of {b['total']} monitored beaches under an advisory or closure.")
    sim = latest.get("similar_years")
    if sim and sim.get("years"):
        ys = [str(y["year"]) for y in sim["years"]]
        like = f"{', '.join(ys[:-1])} and {ys[-1]}" if len(ys) > 1 else ys[0]
        lines.append(f"Rivers over the last {sim['days']} days look most like {like} (background, not a forecast).")
    iso = now.isocalendar()
    return {"id": f"{iso.year}-W{iso.week:02d}", "date": now.isoformat(),
            "title": f"{region.name} this week: {now.strftime('%B')} {now.day}, {now.year}",
            "headline": headline, "lines": lines, "posted": False}


def update(region: Region, latest: dict, now: pd.Timestamp | None = None) -> dict | None:
    """Add this week's entry if it's time and there isn't one yet. Returns the new entry, or None."""
    cfg = region.extras.get("digest")
    if not cfg:
        return None
    now = now or pd.Timestamp.now(tz=region.timezone)
    entries = load(region)
    day = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"].index(cfg["weekday"].lower())
    due = now.weekday() > day or (now.weekday() == day and now.hour >= cfg.get("hour", 6))
    entry = compose(region, latest, now)
    if not due or any(e["id"] == entry["id"] for e in entries):
        _save(region, entries)          # still publish the feed the site reads
        return None
    entries = ([entry] + entries)[:cfg.get("keep", 12)]
    _save(region, entries)
    log.info("digest: added %s", entry["id"])
    return entry


def post_text(entry: dict) -> str:
    """The headline and as many lines as fit; the link and picture go in the card under it."""
    text = entry["headline"]
    for line in entry["lines"]:
        if len(text) + 1 + len(line) > POST_MAX:
            break
        text += " " + line
    return text if len(text) <= POST_MAX else text[:POST_MAX - 1].rsplit(" ", 1)[0] + "…"


def post(region: Region, site_url: str, image: str | None = None) -> bool:
    """Post the newest unposted entry from the last day to Bluesky. No credentials, nothing to post: no-op."""
    import requests
    handle, password = os.environ.get("BLUESKY_HANDLE"), os.environ.get("BLUESKY_APP_PASSWORD")
    entries = load(region)
    now = pd.Timestamp.now(tz=region.timezone)
    todo = [e for e in entries if not e["posted"] and now - pd.Timestamp(e["date"]) < pd.Timedelta(days=1)]
    if not todo:
        log.info("digest: nothing new to post")
        return False
    if not (handle and password):
        log.info("digest: %s is ready; set BLUESKY_HANDLE and BLUESKY_APP_PASSWORD to post it", todo[0]["id"])
        return False
    e = todo[0]
    s = requests.post(f"{BSKY}/com.atproto.server.createSession", timeout=30,
                      json={"identifier": handle, "password": password})
    s.raise_for_status()
    auth = {"Authorization": f"Bearer {s.json()['accessJwt']}"}
    card = {"uri": site_url, "title": e["title"], "description": "Free, plain-language conditions for the "
            f"{region.name}. Not for navigation or harvest decisions."}
    if image and os.path.exists(image):
        with open(image, "rb") as f:
            b = requests.post(f"{BSKY}/com.atproto.repo.uploadBlob", data=f.read(), timeout=60,
                              headers={**auth, "Content-Type": "image/png"})
        b.raise_for_status()
        card["thumb"] = b.json()["blob"]
    r = requests.post(f"{BSKY}/com.atproto.repo.createRecord", timeout=30, headers=auth, json={
        "repo": s.json()["did"], "collection": "app.bsky.feed.post",
        "record": {"$type": "app.bsky.feed.post", "text": post_text(e), "langs": ["en"],
                   "createdAt": pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                   "embed": {"$type": "app.bsky.embed.external", "external": card}}})
    r.raise_for_status()
    e["posted"] = True
    _save(region, entries)
    log.info("digest: posted %s", e["id"])
    return True
