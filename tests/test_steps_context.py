"""Step-event context on a made-up week: the Gulf water level sentence (decision 0030)."""
import pandas as pd

from msc.models.steps import context

CFG = {"level_site": "L", "level_label": "the water at Dauphin Island, AL,"}
ONSET = pd.Timestamp("2026-10-15")


def daily(before: float, after: float) -> pd.DataFrame:
    days = pd.date_range(ONSET - pd.Timedelta(days=12), ONSET)
    return pd.DataFrame({"site": "L", "var": "water_level", "date": days, "source": "coops",
                         "value": [before if d < ONSET - pd.Timedelta(days=2) else after for d in days]})


def test_level_fall_is_described():
    assert context(daily(0.30, 0.12), CFG, ONSET) == "In the days before, the water at Dauphin Island, AL, fell about 7 inches."


def test_small_change_is_not():
    assert "doesn't point to a cause" in context(daily(0.30, 0.26), CFG, ONSET)
