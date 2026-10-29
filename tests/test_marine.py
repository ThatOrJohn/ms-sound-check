"""Dating the NWS marine zone periods, which carry names but no times."""
from msc.adapters.nws import parse_marine

JS = {"properties": {"updated": "2026-10-29T05:37:00-05:00", "periods": [
    {"name": "Today", "detailedForecast": "Northeast winds 5 to 10 knots. Waves 2 to 3 feet this morning, then 1 foot or less."},
    {"name": "Tonight", "detailedForecast": "Northeast winds around 5 knots. Waves 1 foot or less."},
    {"name": "Saturday", "detailedForecast": "East winds 10 to 15 knots. Waves 2 to 3 feet. A chance of showers."},
    {"name": "Saturday Night", "detailedForecast": "East winds 10 to 15 knots. Bay waters a light chop."},
    {"name": "Wednesday", "detailedForecast": "North winds 5 knots."},
]}}


def test_periods_get_dates_and_keep_the_nws_wave_words():
    p = parse_marine(JS, "America/Chicago")["periods"]
    assert [(x["date"], x["is_day"]) for x in p] == [
        ("2026-10-29", True), ("2026-10-29", False), ("2026-10-31", True), ("2026-10-31", False), ("2026-11-04", True)]
    assert p[0]["waves"] == "Waves 2 to 3 feet this morning, then 1 foot or less."
    assert p[2]["waves"] == "Waves 2 to 3 feet."          # the showers sentence stays out
    assert p[3]["waves"] == "Bay waters a light chop."
    assert p[4]["waves"] is None


def test_a_forecast_issued_after_midnight_starts_on_its_own_weekday():
    js = {"properties": {"updated": "2026-10-31T00:30:00-05:00", "periods": [
        {"name": "Overnight", "detailedForecast": "Waves 1 foot or less."},
        {"name": "Saturday", "detailedForecast": "Waves 2 to 3 feet."},
        {"name": "Saturday Night", "detailedForecast": "Waves 2 feet."},
        {"name": "Sunday", "detailedForecast": "Waves 1 to 2 feet."}]}}
    assert [x["date"] for x in parse_marine(js, "America/Chicago")["periods"]] == [
        "2026-10-31", "2026-10-31", "2026-10-31", "2026-11-01"]
