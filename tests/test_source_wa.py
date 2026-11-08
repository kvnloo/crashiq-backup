"""Washington sources (state onboarding 2026-11-07): Seattle SDOT reader, WSDOT export-layout reader, WSDOT portal
reader. Offline: recorded fixtures in tests/fixtures/wa/ (real 2025 rows, recorded 2026-11-07)."""

import json
from pathlib import Path

from crashiq.sources import wa_sdot, wa_wsdot

FX = Path(__file__).parent / "fixtures" / "wa"


def _sdot():
    d = json.loads((FX / "sdot_2025_sample.json").read_text())
    return {r["collision_id"]: r for r in wa_sdot.build(d["crashes"], d["persons"])}


def test_sdot_location_split():
    assert wa_sdot.split_location("15TH AVE NW BETWEEN NW 85TH ST AND NW 87TH ST") == \
        ("15TH AVE NW", "NW 85TH ST", "NW 87TH ST")
    assert wa_sdot.split_location("HOWELL ST AND MINOR AVE") == ("HOWELL ST", "MINOR AVE", None)
    assert wa_sdot.split_location(None) == (None, None, None)
    # divided-street roadway tags are not part of the name
    assert wa_sdot.split_location("BEACON ER AVE S AND S GRAHAM ST")[0] == "BEACON AVE S"
    assert [wa_sdot.clean_street(s) for s in ("62ND E AVE S", "8TH N AVE N", "2ND AV ET S", "S INDUSTRIAL WB WAY")] == \
        ["62ND AVE S", "8TH AVE N", "2ND AV S", "S INDUSTRIAL WAY"]
    assert wa_sdot.clean_street("E PIKE ST") == "E PIKE ST"


def test_sdot_records_known_answers():
    rows = _sdot()
    assert len(rows) == 40
    r = rows["386378"]                      # M L KING JR WR WAY S AND S FAIRBANKS ST
    assert (r["primary_road"], r["secondary_road"]) == ("M L KING JR WAY S", "S FAIRBANKS ST")
    assert r["date"] == "2025-02-12" and r["hour"] == 20 and r["severity"] == "O"
    k = rows["380551"]                      # fatal, Aurora Ave N & N 125th St
    assert k["severity"] == "K" and k["killed"] == 1 and "K" in [p["kabco"] for p in k["persons"]]
    assert rows["387044"]["hour"] is None   # INCDTTM gives a date only
    alley = rows["390845"]
    assert alley["addr_type"] == "A" and alley["primary_road"] is None and alley["lat"] is None


def test_sdot_severity_rules():
    # the city's crash code wins; persons only split "injury" (U) into B or C
    f = {"attributes": {"COLDETKEY": 1, "MAXSEVERITYCODE": "2", "INCDTTM": "1/2/2025 3:04:00 PM",
                        "LOCATION": "A ST AND B ST"}, "geometry": {"x": -122.33, "y": 47.6}}
    pc = wa_sdot.person_record({"ST_INJRY_CLSS_DESC": "Possible Injury"})
    pb = wa_sdot.person_record({"ST_INJRY_CLSS_DESC": "Non Serious Injury (Evident Injury)"})
    assert wa_sdot.crash_record(f, [pc, pb])["severity"] == "B"
    assert wa_sdot.crash_record(f, [])["severity"] == "U"
    f["attributes"]["MAXSEVERITYCODE"] = "1"
    assert wa_sdot.crash_record(f, [pc])["severity"] == "O"
    f["geometry"] = {"x": 0, "y": 0}
    assert wa_sdot.crash_record(f)["lat"] is None          # outside Washington = no GPS


def test_sdot_fixture_severity_counts():
    from collections import Counter
    assert Counter(r["severity"] for r in _sdot().values()) == \
        Counter({"O": 21, "B": 6, "A": 4, "C": 3, "K": 3, None: 2, "U": 1})


def test_wsdot_export_layout():
    feats = json.loads((FX / "tacoma_wsdot_layout_2025_sample.json").read_text())["features"]
    cols = wa_wsdot.resolve(feats[0]["attributes"])
    assert {"primary", "intersecting", "ref_point", "dist", "unit", "dir", "severity", "collision_type"} <= set(cols)
    rows = {r["collision_id"]: r for r in (wa_wsdot.export_record(f["attributes"], cols, f["geometry"]) for f in feats)}
    a = rows["EF69252"]                     # N I ST & N 6TH ST, block 600
    assert (a["primary_road"], a["secondary_road"], a["block_number"]) == ("N I ST", "N 6TH ST", 600)
    assert a["sec_distance"] is None and a["severity"] == "C" and a["date"] == "2025-02-26" and a["hour"] == 5
    b = rows["EG35847"]                     # 686.4 ft SE of DIVISION AVE on S STADIUM WAY
    assert (b["secondary_road"], b["sec_distance"], b["sec_direction"]) == ("DIVISION AVE", 686.4, "SE")
    assert b["hour"] == 19
    s = rows["EG69678"]                     # state route: route + milepost only
    assert s["jurisdiction"] == "State Route" and s["milepost"] == 3.84 and s["secondary_road"] is None
    assert all(r["lat"] is not None for r in rows.values())


def test_wsdot_export_spaced_headers():
    """A WSDOT Excel export has spaced headers ("PRIMARY TRAFFICWAY"); the same reader takes them."""
    row = {"REPORT NUMBER": "EF1", "JURISDICTION": "City Street", "PRIMARY TRAFFICWAY": "MAIN ST",
           "INTERSECTING TRAFFICWAY": "1ST AVE", "DATE": "2025-03-04", "FULL TIME": "1630",
           "MOST SEVERE INJURY TYPE": "Suspected Minor Injury", "TOTAL SUSPECTED MINOR INJURIES": 2}
    r = wa_wsdot.export_record(row)
    assert (r["primary_road"], r["secondary_road"], r["hour"], r["severity"], r["injured"]) == \
        ("MAIN ST", "1ST AVE", 16, "B", 2)
    assert r["lat"] is None


def test_wsdot_portal():
    rows = json.loads((FX / "wsdot_portal_seattle_2025_sample.json").read_text())["rows"]
    out = [wa_wsdot.portal_record(r) for r in rows]
    assert [o["severity"] for o in out[:4]] == ["K", "U", "K", "O"]
    assert out[0]["report_number"] == "3898784" and out[0]["hour"] == 23
    assert all(o["lat"] is not None and o["primary_road"] is None for o in out)
