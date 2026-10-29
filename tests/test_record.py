"""The `record` indicator on a made-up series: 20 years of a river whose late-October flow is 1000 + 100 * (year - 2000),
so every year is higher than the last."""
import pandas as pd

from msc.config import Region
from msc.indicators import evaluate, record

SITE = {"id": "R", "name": "Test River", "short": "Test", "kind": "river", "source": "usgs", "vars": ["flow"]}
CFG = {"id": "river_record", "type": "record", "var": "flow", "kinds": ["river"], "window": 14, "min_days": 10,
       "top": 3, "topics": ["general"], "low_word": "lowest", "high_word": "highest", "low_cmp": "lower",
       "high_cmp": "higher", "low_text": "The {site} is at its {rank} {season} flow since {since}.",
       "high_text": "The {site} is at its {rank} {season} flow since {since}."}
VS_NORMAL = {"id": "river_vs_normal", "type": "vs_normal", "var": "flow", "kinds": ["river"], "low_pct": 10,
             "high_pct": 90, "low_text": "{site} low", "high_text": "{site} high"}
ASOF = pd.Timestamp("2019-10-28")


def region(*indicators):
    return Region(id="t", name="t", timezone="UTC", units={"flow": "cfs"}, sites=[SITE], personas=[],
                  indicators=list(indicators))


def daily(today_value, drop_years=()):
    rows = []
    for d in pd.date_range("2000-01-01", ASOF):
        if d.year in drop_years:
            continue
        v = today_value if d.year == ASOF.year else 1000 + 100 * (d.year - 2000)
        rows.append(("R", "flow", d, v, "usgs"))
    return pd.DataFrame(rows, columns=["site", "var", "date", "value", "source"])


def test_lowest_third():
    # 1150 sits above 2000 (1000) and 2001 (1100) and below every later year: third-lowest.
    f = record(region(CFG), CFG, daily(1150), pd.DataFrame(), ASOF)
    assert len(f) == 1 and f[0]["side"] == "low" and f[0]["rank"] == 3
    assert f[0]["text"] == ("The Test River is at its third-lowest late-October flow since 2000. "
                            "Only 2000 and 2001 were lower.")


def test_highest_and_middle():
    f = record(region(CFG), CFG, daily(99_999), pd.DataFrame(), ASOF)
    assert f[0]["text"] == "The Test River is at its highest late-October flow since 2000."
    assert record(region(CFG), CFG, daily(2000), pd.DataFrame(), ASOF) == []


def test_thin_years_left_out():
    # Drop 2000 and 2001: 1150 becomes the lowest, and "since" moves to 2002.
    f = record(region(CFG), CFG, daily(1150, drop_years=(2000, 2001)), pd.DataFrame(), ASOF)
    assert f[0]["rank"] == 1 and "since 2002" in f[0]["text"]


def test_too_few_years():
    short = daily(1150)
    short = short[short.date.dt.year >= 2012]
    assert record(region(CFG), CFG, short, pd.DataFrame(), ASOF) == []


def test_replaces_vs_normal():
    normals = pd.DataFrame([{"site": "R", "var": "flow", "doy": doy, "p10": 1500, "p25": 1800, "p50": 2000,
                             "p75": 2200, "p90": 2500, "n_years": 19} for doy in range(1, 366)])
    r = region(VS_NORMAL)
    assert [f["indicator"] for f in evaluate(r, daily(1150), normals, ASOF)] == ["river_vs_normal"]
    r = region(VS_NORMAL, CFG)
    assert [f["indicator"] for f in evaluate(r, daily(1150), normals, ASOF)] == ["river_record"]


def test_year_dots_agree_with_record():
    # The year dots (decision 0032) come from the same means as the record line, so their rank is the sentence's.
    from msc.build import _year_dots
    for today, side in ((1150, "low"), (99_999, "high")):
        f = record(region(CFG), CFG, daily(today), pd.DataFrame(), ASOF)[0]
        d = _year_dots(region(CFG), daily(today), ASOF)[("R", "flow")]
        assert d[f"rank_{side}"] == f["rank"] and d["of"] == f["years"] == len(d["points"])
        assert d["points"][0] == [2000, 1000.0] and d["season"] == "late-October"
    d = _year_dots(region(CFG), daily(2050), ASOF)[("R", "flow")]   # mid-pack: no record line, still dots
    assert record(region(CFG), CFG, daily(2050), pd.DataFrame(), ASOF) == [] and d["rank_high"] + d["rank_low"] == d["of"] + 1
