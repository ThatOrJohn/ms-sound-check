"""Weekly digest: one entry per week, added on or after the configured day, and a post that fits Bluesky."""
import pandas as pd
import pytest

from msc import digest
from msc.config import Region

LATEST = {"headlines": {"general": "The Sound is close to normal for late October."},
          "findings": [{"severity": "notice", "topics": ["general"], "text": "The Pearl River is running low."},
                       {"severity": "notice", "topics": ["general"], "text": "The Pearl is at its third-lowest.", "rank": 3},
                       {"severity": "notice", "topics": ["oyster"], "text": "Oyster only."}],
          "beaches": {"total": 21, "counts": {"advisory": 2, "closure": 0}}}


@pytest.fixture
def region(tmp_path, monkeypatch):
    monkeypatch.setattr(digest, "SITE_OUT", tmp_path / "site")
    monkeypatch.setattr(Region, "data_dir", property(lambda self: tmp_path / "store"))
    return Region(id="t", name="Test Sound", timezone="America/Chicago", units={}, sites=[], personas=[],
                  indicators=[], extras={"digest": {"weekday": "friday", "hour": 6, "keep": 2}})


def at(s):
    return pd.Timestamp(s, tz="America/Chicago")


def test_once_a_week_from_friday_morning(region):
    assert digest.update(region, LATEST, at("2026-10-29 12:00")) is None      # Thursday
    assert digest.update(region, LATEST, at("2026-10-30 05:00")) is None      # Friday, too early
    e = digest.update(region, LATEST, at("2026-10-30 06:17"))
    assert e["id"] == "2026-W44"
    assert digest.update(region, LATEST, at("2026-10-31 09:00")) is None      # already have this week
    digest.update(region, LATEST, at("2026-11-06 06:17"))
    digest.update(region, LATEST, at("2026-11-13 06:17"))
    assert [x["id"] for x in digest.load(region)] == ["2026-W46", "2026-W45"]   # keep: 2


def test_entry_lines(region):
    e = digest.compose(region, LATEST, at("2026-10-30 06:17"))
    assert e["lines"] == ["The Pearl is at its third-lowest.", "The Pearl River is running low.",
                          "MDEQ has 2 of 21 monitored beaches under an advisory or closure."]


def test_post_text_fits():
    e = {"headline": "x" * 250, "lines": ["y" * 40, "z" * 10]}
    assert digest.post_text(e) == "x" * 250 + " " + "y" * 40          # the next line would pass 300: stop there
    assert digest.post_text({"headline": "w " * 200, "lines": []}).endswith("…")
    assert len(digest.post_text({"headline": "w " * 200, "lines": []})) <= digest.POST_MAX
