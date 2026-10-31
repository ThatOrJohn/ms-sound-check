"""MDMR season pages (0044), shellfish growing-area classes (0043) and Grand Bay from NDBC (0045)."""
import pytest

from msc.adapters import mdmr, ndbc, shellfish

BUTTON = '<span class="elementor-button-text">{}</span>'
SHRIMP_PAGE = (
    "<h5>SHRIMP SEASON STATUS</h5>"
    "<p><strong>MS WATERS NORTH OF INTRACOASTAL WATERWAY (ICW)</strong></p>" + BUTTON.format("OPEN") +
    "<p><strong>MS WATERS SOUTH OF ICW &amp; WEST OF GULFPORT SHIP CHANNEL*</strong></p>" + BUTTON.format("CLOSED") +
    "<p>*waters south of the ICW and east of Gulfport Ship Channel remain open year-round</p>"
    "<h5>SHRIMP ZONES MAP</h5><p><strong>NOT A ZONE</strong></p>" + BUTTON.format("OPEN"))


def test_shrimp_status_pairs_each_area_with_its_button_and_keeps_the_footnote():
    s = mdmr.shrimp_status(SHRIMP_PAGE)
    assert s["areas"] == [
        {"area": "Mississippi waters north of Intracoastal Waterway (ICW)", "status": "open", "footnote": False},
        {"area": "Mississippi waters south of ICW & west of Gulfport ship channel", "status": "closed", "footnote": True},
    ]
    assert s["note"] == "Waters south of the ICW and east of Gulfport Ship Channel remain open year-round"


def test_shrimp_status_raises_when_the_box_is_gone():
    with pytest.raises(RuntimeError):
        mdmr.shrimp_status("<h5>SHRIMP & CRAB BUREAU</h5><p>No box here.</p>")


OYSTER_PAGE = (
    "<h5>SEASON INFORMATION</h5><p>On October 1, 2026, the season opened. "
    'Please refer to <a href="x">this link</a> for daily sunrise times.</p>'
    "<h2>MANAGEMENT PLAN/OPENING AND CLOSING ORDERS</h2><ul>"
    '<li><a href="/plan.pdf">Molluscan Shellfish Growing Waters Management Plan</a></li>'
    '<li><a href="/open.pdf">Order Opening the Season</a></li>'
    '<li><a href="/close.pdf">Order Closing Area I &#8220;B&#8221;</a></li></ul>'
    "<p>All Mississippi waters and public reef areas therein shall remain closed on Sundays and the following days: </p>"
    "<ul><li><span>Thanksgiving Day, Thursday, November 26, 2026</span></li></ul>"
    "<p>The maps below depict areas.</p><ul><li>Not a holiday</li></ul>")


def test_oyster_season_quotes_the_season_text_orders_and_no_harvest_days():
    s = mdmr.oyster_season(OYSTER_PAGE)
    assert s["summary"] == ["On October 1, 2026, the season opened."]
    assert s["orders"] == [{"title": "Order Opening the Season", "link": "/open.pdf"},
                           {"title": "Order Closing Area I “B”", "link": "/close.pdf"}]   # not the plan
    assert s["no_harvest"]["lead"].endswith("closed on Sundays and the following days:")
    assert s["no_harvest"]["days"] == ["Thanksgiving Day, Thursday, November 26, 2026"]


@pytest.mark.parametrize("zone,short", [('Area II "E"', "II-E"), ("Area I “B”", "I-B"), ("Area V", "V"), ("Bay", "Bay")])
def test_zone_names_match_the_closure_watch(zone, short):
    assert shellfish.short(zone) == short


def square(x0, size):
    return {"type": "Polygon", "coordinates": [[[x0, 0], [x0 + size, 0], [x0 + size, size], [x0, size], [x0, 0]]]}


def test_shellfish_keeps_only_zone_and_class_and_labels_the_biggest_piece():
    raw = {"features": [
        {"geometry": square(0, 1), "properties": {"ZONE_ID": 'Area II "E"', "CONDITIONS": "conditionally approved", "Status": "Closed"}},
        {"geometry": square(5, 3), "properties": {"ZONE_ID": 'Area II "E"', "CONDITIONS": "conditionally approved", "Status": "Closed"}},
        {"geometry": square(9, 2), "properties": {"ZONE_ID": "Area III", "CONDITIONS": "prohibited", "Status": "Closed"}},
        {"geometry": square(12, 2), "properties": {"ZONE_ID": "Area IV", "CONDITIONS": "something new"}},
    ]}
    feats = shellfish.normalize(raw)["features"]
    assert len(feats) == 3                                         # an unknown class is dropped
    assert all("Status" not in f["properties"] and "status" not in f["properties"] for f in feats)
    assert [f["properties"].get("label") for f in feats] == [None, True, None]   # biggest II-E piece; no label on prohibited
    assert feats[0]["properties"] == {"zone": "II-E", "name": 'Area II "E"', "class": "conditional"}


NDBC = """#YY  MM DD hh mm   DEPTH  OTMP   COND   SAL   O2% O2PPM  CLCON  TURB    PH    EH
#yr  mo dy hr mn       m  degC  mS/cm   psu     %   ppm   ug/l   FTU     -    mv
{rows}"""


def test_ndbc_daily_mean_needs_twelve_hours_and_uses_local_days():
    # 2026-10-30 12:00 to 23:45 UTC is 07:00 to 18:45 Central: 48 readings, one local day. Then one stray reading.
    rows = [f"2026 10 30 {h:02d} {m:02d}     0.3 22.60  45.87 {29 + (h % 2):.2f}  85.3  6.20     MM     7  7.30    MM"
            for h in range(12, 24) for m in (0, 15, 30, 45)]
    rows.append("2026 10 31 12 00     0.3 22.60  45.87    MM  85.3  6.20     MM     7  7.30    MM")
    rows.append("2026 10 31 12 15     0.3 22.60  45.87 29.00  85.3  6.20     MM     7  7.30    MM")
    df = ndbc.parse({"id": "NDBC-GDQM6", "tz": "America/Chicago"}, NDBC.format(rows="\n".join(rows)))
    assert list(df.date.dt.strftime("%Y-%m-%d")) == ["2026-10-30"]
    assert df.value.iloc[0] == pytest.approx(29.5)
    assert set(df.site) == {"NDBC-GDQM6"} and set(df["var"]) == {"salinity"}


def test_ndbc_empty_file_gives_no_rows():
    assert ndbc.parse({"id": "x"}, "").empty
