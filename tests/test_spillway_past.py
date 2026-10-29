"""Past spillway openings side by side (decision 0038), on a made-up station: 15 ppt all year, except 0.5 ppt for 20 days
starting a week after a 2019 opening, with one missing day in the middle of that fresh spell."""
import pandas as pd

from msc.models.spillway import FRESH_PPT, _longest_run, past

SITE = "S"
OPENS = [{"opened": "2019-02-27", "year": 2019, "days": 43}, {"opened": "2019-05-10", "year": 2019, "days": 79},
         {"opened": "2008-04-11", "year": 2008, "days": 31}, {"opened": "1997-03-17", "year": 1997, "days": 31}]
ASOF = pd.Timestamp("2026-10-28")
FRESH_FROM = pd.Timestamp("2019-03-06")


def daily():
    rows = []
    for d in pd.date_range("2018-06-01", "2019-12-31"):
        if d == FRESH_FROM + pd.Timedelta(days=12):
            continue
        fresh = FRESH_FROM <= d < FRESH_FROM + pd.Timedelta(days=20)
        rows.append((SITE, "salinity", d, 0.5 if fresh else 15.0, "usgs"))
    return pd.DataFrame(rows, columns=["site", "var", "date", "value", "source"])


def normals():
    return pd.DataFrame({"site": SITE, "var": "salinity", "doy": range(1, 367), "p50": 12.0})


def test_one_chart_per_year_with_data_since_2000():
    out = past(daily(), normals(), SITE, OPENS, ASOF)
    assert [p["year"] for p in out] == [2019]           # 2008 has no readings, 1997 is before 2000
    p = out[0]
    assert p["opened"] == ["2019-02-27", "2019-05-10"]
    assert p["bands"] == [[0, 43], [72, 151]]           # second opening counted from the year's first
    assert p["days_open"] == 122
    assert p["before"] == 15.0 and p["low"] == 0.5 and p["low_day"] == 7
    assert p["series"][0][0] == -28 and p["series"][-1][0] == 196
    assert p["typical"] and all(v == 12.0 for _, v in p["typical"])


def test_missing_day_breaks_the_fresh_run():
    p = past(daily(), normals(), SITE, OPENS, ASOF)[0]
    assert p["fresh_run"] == 12 and p["fresh_run_day"] == 7


def test_longest_run():
    s = pd.Series([1, 1, 5, 1, 1, 1], index=pd.date_range("2020-01-01", periods=6), dtype=float)
    assert _longest_run(s, FRESH_PPT) == (3, pd.Timestamp("2020-01-04"))
    assert _longest_run(s * 10, FRESH_PPT) == (0, None)


def test_no_normals_still_draws():
    assert past(daily(), None, SITE, OPENS, ASOF)[0]["typical"] == []
