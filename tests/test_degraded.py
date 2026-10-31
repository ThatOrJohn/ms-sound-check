"""One source going bad hides its own section and nothing else (decision 0046)."""
import json

import pandas as pd
import pytest

from msc import build as build_mod
from msc import normals as nm
from msc import store
from msc.adapters import beaches, mdmr
from msc.config import Region, load_region
from msc.snapshots import read_json, write_json

NOW = pd.Timestamp.now(tz="UTC").isoformat()


@pytest.fixture
def region(tmp_path, monkeypatch):
    monkeypatch.setattr(build_mod, "SITE_OUT", tmp_path / "site")
    monkeypatch.setattr(Region, "data_dir", property(lambda self: tmp_path / "store"))
    (tmp_path / "store").mkdir()
    return load_region("ms")


def _build(region):
    asof = pd.Timestamp.now(tz=region.timezone).tz_localize(None).normalize()
    return build_mod.build(region, store.read_daily(region), nm.load(region), asof)


def test_read_json_treats_bad_files_as_missing(tmp_path):
    p = tmp_path / "x.json"
    for text in ("<html>Service Unavailable</html>", "[]", "{}", json.dumps({"fetched_at": NOW, "periods": None})):
        p.write_text(text)
        assert read_json(p, pd.Timedelta(days=2), need=("fetched_at", "periods")) is None
    write_json(p, {"fetched_at": NOW, "periods": []})
    assert read_json(p, pd.Timedelta(days=2), need=("fetched_at", "periods")) == {"fetched_at": NOW, "periods": []}
    write_json(p, {"fetched_at": "2001-01-01T00:00:00+00:00", "periods": []})
    assert read_json(p, pd.Timedelta(days=2), need=("fetched_at", "periods")) is None   # stale


SNAPSHOTS = ["beaches.json", "beaches.geojson", "marine_forecast.json", "mdmr_notices.json", "mdmr_pages.json",
             "shellfish_areas.json", "spillway.json", "tides.json", "weather_forecast.json"]
BAD = ["<html>oops", "{}", "[]", json.dumps({"fetched_at": NOW}),
       json.dumps({"fetched_at": NOW, "stations": None, "topics": None, "pages": None, "geojson": None,
                   "periods": None, "predictions": None, "features": None})]


@pytest.mark.parametrize("name", SNAPSHOTS)
def test_build_survives_a_bad_snapshot(region, name):
    for text in BAD:
        (region.data_dir / name).write_text(text)
        latest = _build(region)
        assert latest["cards"] and set(latest["headlines"]) == {p["id"] for p in region.personas}


@pytest.mark.parametrize("name", ["recent.parquet", "rain_forecast.parquet", "stage_forecast.parquet", "beach_history.parquet"])
def test_build_survives_a_bad_table(region, name):
    (region.data_dir / name).write_bytes(b"not parquet")
    assert _build(region)["cards"]


def test_a_section_that_raises_is_left_out_and_named(region, monkeypatch):
    from msc.models import spillway

    def boom(*a):
        raise KeyError("observed")
    monkeypatch.setattr(spillway, "section", boom)
    latest = _build(region)
    assert latest["spillway"] is None and "spillway" in latest["unavailable"]
    assert build_mod._section.failures == ["spillway"]
    assert json.loads((build_mod.SITE_OUT / region.id / "latest.json").read_text())["cards"]


def test_unavailable_lists_configured_sections_with_no_current_data(region):
    latest = _build(region)   # an empty store: nothing has been fetched
    assert {"beaches", "fishing_outlook"} <= set(latest["unavailable"])
    assert "vibrio" not in latest["unavailable"]   # seasonal, not sourced


def test_a_page_that_fails_keeps_its_last_good_copy(region, monkeypatch):
    old = {"fetched_at": NOW, "pages": {"shrimp_status": {"areas": [{"area": "A", "status": "open"}], "fetched_at": NOW}}}

    def fetch(cfg, key, p):
        if key == "shrimp_status":
            raise AttributeError("layout changed")
        return {"summary": ["s"], "orders": [], "no_harvest": None, "link": "l", "modified": "2026-10-01"}
    monkeypatch.setattr(mdmr, "_fetch_page", fetch)
    got = mdmr.fetch_pages(region, old)
    assert got["failed"] == ["shrimp_status"]
    assert got["pages"]["shrimp_status"] == old["pages"]["shrimp_status"]
    assert got["pages"]["oyster_season"]["fetched_at"] == got["fetched_at"]


def test_a_carried_page_hides_once_its_own_copy_is_stale(region):
    stale = "2001-01-01T00:00:00+00:00"
    mdmr.save_pages(region, {"fetched_at": NOW, "failed": ["shrimp_status"],
                             "pages": {"shrimp_status": {"areas": [], "fetched_at": stale},
                                       "oyster_season": {"summary": ["s"], "fetched_at": NOW}}})
    assert mdmr.page(region, "shrimp_status") is None
    assert mdmr.page(region, "oyster_season")["summary"] == ["s"]


def test_every_page_failing_raises_so_the_old_snapshot_stands(region, monkeypatch):
    monkeypatch.setattr(mdmr, "_fetch_page", lambda *a: (_ for _ in ()).throw(ValueError("html, not json")))
    with pytest.raises(RuntimeError):
        mdmr.fetch_pages(region, None)


def test_beaches_with_no_stations_is_a_failed_fetch(region, monkeypatch):
    monkeypatch.setattr(beaches, "_query", lambda url, layer, geojson: {"features": []})
    with pytest.raises(RuntimeError):
        beaches.fetch(region)


def test_beaches_keep_stations_when_only_the_map_lines_fail(region, monkeypatch):
    def query(url, layer, geojson):
        if geojson:
            raise TimeoutError("segments")
        return {"features": [{"attributes": {"stationnumber": 1, "name": "Pass Christian", "isadvisory": 1}}]}
    monkeypatch.setattr(beaches, "_query", query)
    data = beaches.fetch(region)
    assert data["stations"][0]["status"] == "advisory" and data["segments"] is None
