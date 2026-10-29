"""Fresh-and-hot days near the reefs (decision 0039), on a made-up station: 15 ppt and 28 °C every day, except
three summers with fresh spells. 2019: 20 days at 3 ppt in July with one missing day in the middle. 2020: 10 days at
3 ppt in January (cold, so none count). 2021: half the summer missing, with 5 fresh days."""
import pandas as pd

from msc.models.oyster_stress import _summary, station_years

CFG = {"salinity_below": 5, "temp_above_c": 25, "season_months": [5, 10], "min_coverage": 0.8}
SITE = "S"
ASOF = pd.Timestamp("2022-10-28")
GAP = pd.Timestamp("2019-07-11")


def daily():
    rows = []
    for d in pd.date_range("2019-01-01", ASOF):
        if d == GAP or (d.year == 2021 and pd.Timestamp("2021-05-01") <= d < pd.Timestamp("2021-08-01")):
            continue
        fresh = (pd.Timestamp("2019-07-01") <= d < pd.Timestamp("2019-07-21")
                 or pd.Timestamp("2020-01-10") <= d < pd.Timestamp("2020-01-20")
                 or pd.Timestamp("2021-08-10") <= d < pd.Timestamp("2021-08-15"))
        temp = 12.0 if d.month in (12, 1, 2) else 28.0
        rows += [(SITE, "salinity", d, 3.0 if fresh else 15.0, "usgs"), (SITE, "water_temp", d, temp, "usgs")]
    return pd.DataFrame(rows, columns=["site", "var", "date", "value", "source"])


def by_year():
    return {y["year"]: y for y in station_years(daily(), SITE, ASOF, CFG)}


def test_fresh_and_hot_both_needed_and_a_missing_day_ends_a_run():
    y = by_year()
    assert y[2019]["days"] == 19 and y[2019]["run"] == 10          # the gap splits 20 days into 10 + 9
    assert y[2020]["days"] == 0                                    # fresh but cold
    assert y[2019]["complete"] and y[2020]["complete"]


def test_a_gappy_summer_is_not_complete():
    y = by_year()
    assert y[2021]["days"] == 5 and not y[2021]["complete"]


def test_this_year_compares_only_with_complete_years_to_the_same_date():
    years = station_years(daily(), SITE, ASOF, CFG)
    s = _summary(years, ASOF)
    assert s["days"] == 0 and s["of"] == 2 and s["more"] == 1      # 2019 had some by Oct 28; 2021 isn't compared
    assert s["last_as_many"] is None


def test_a_run_still_going_is_reported():
    d = daily()
    d.loc[(d.date >= pd.Timestamp("2022-10-20")) & (d["var"] == "salinity"), "value"] = 2.0
    s = _summary(station_years(d, SITE, ASOF, CFG), ASOF)
    assert s["days"] == 9 and s["run_now"] == 9 and s["more"] == 1
