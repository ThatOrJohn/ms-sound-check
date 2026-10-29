"""Sun and moon times (decision 0040), checked against the US Naval Observatory's tables for 30.30 N, 88.95 W,
fetched 2026-10-29 from aa.usno.navy.mil/api/rstt/oneday and /api/moon/phases."""
from msc.models.sky import day

LAT, LON, TZ = 30.30, -88.95, "America/Chicago"


def test_rise_and_set_match_usno():
    d = day(LAT, LON, TZ, "2026-11-09")
    assert (d["sunrise"], d["sunset"]) == ("2026-11-09 06:17", "2026-11-09 17:02")
    assert (d["moonrise"], d["moonset"]) == ("2026-11-09 06:41", "2026-11-09 17:05")


def test_principal_phase_is_named_on_its_local_day():
    assert day(LAT, LON, TZ, "2026-11-09")["moon_phase"] == "new moon"      # 07:02 UTC = 01:02 CST
    assert day(LAT, LON, TZ, "2026-11-24")["moon_phase"] == "full moon"
    assert day(LAT, LON, TZ, "2026-11-17")["moon_phase"] == "first quarter"
    assert day(LAT, LON, TZ, "2026-11-01")["moon_phase"] == "last quarter"  # 20:28 UTC, the day DST ends
    assert day(LAT, LON, TZ, "2026-11-24")["moon_lit_pct"] == 100


def test_in_between_days_and_a_missing_moonrise():
    d = day(LAT, LON, TZ, "2026-11-02")
    assert d["moon_phase"] == "waning crescent"
    assert d["moonrise"] is None                                          # rises 23:38 on the 1st, 00:4x on the 3rd
    assert day(LAT, LON, TZ, "2026-10-29")["moon_phase"] == "waning gibbous"
    assert day(LAT, LON, TZ, "2026-11-11")["moon_phase"] == "waxing crescent"
