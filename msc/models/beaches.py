"""Findings from the beach snapshot: one line per kind of problem, naming the beaches."""
from __future__ import annotations

from ..adapters import beaches as src

def _what(event: str | None) -> str:
    e = (event or "").lower()
    if "hab" in e or "algal" in e:
        return "an algal bloom"
    if "debris" in e:
        return "debris"
    return "high bacteria"


def _names(items: list[dict]) -> str:
    names = [s["name"] for s in items]
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def findings(region, cfg, daily, normals, asof):
    snap, _ = src.load(region)
    if not snap:
        return []
    out = []
    for kind, sev, verb in (("closure", "warning", "closed"), ("advisory", "watch", "under a swimming advisory")):
        items = [s for s in snap["stations"] if s["status"] == kind]
        if not items:
            continue
        reasons = sorted({_what(s["event"]) for s in items})
        n = len(items)
        out.append({"indicator": cfg["id"], "site": None, "severity": sev, "topics": cfg.get("topics", []),
                    "var": "beach", "text": f"{_names(items)} {'is' if n == 1 else 'are'} {verb} for "
                                            f"{' and '.join(reasons)}. Avoid swimming there until it's lifted."})
    return out
