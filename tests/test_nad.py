"""House-address crashes (D5; user decision 2026-10-25, docs/03, #264, #283): NAD address points, else a TIGER ADDRFEAT
suggestion. Synthetic fixtures only (no network)."""

import csv
import io
import zipfile

import pytest
import shapefile

from crashiq import addrfeat, nad
from crashiq.names import street_key

COLS = ["Add_Number", "AddNum_Suf", "St_PreDir", "St_PreTyp", "St_Name", "St_PosTyp", "St_PosDir", "StNam_Full", "County",
        "Inc_Muni", "Post_City", "Zip_Code", "Longitude", "Latitude", "Placement", "NAD_Source", "DateUpdate"]


def nad_row(num, full, county, inc, post, lat, lon):
    return {"Add_Number": num, "StNam_Full": full, "County": county, "Inc_Muni": inc, "Post_City": post,
            "Latitude": lat, "Longitude": lon, "Placement": "Structure - Rooftop", "NAD_Source": "Test County"}


@pytest.fixture()
def index(tmp_path):
    rows = [nad_row(5101, "Business Center Drive", "Solano", "Fairfield", "Fairfield", 38.2400, -122.0600),
            nad_row(5101, "Business Center Drive", "Solano", "Fairfield", "Fairfield", 38.2401, -122.0601),  # same lot
            nad_row(1677, "North Texas Street", "Solano", "Fairfield", "Fairfield", 38.2600, -122.0400),
            nad_row(200, "Main Street", "Solano", "Vacaville", "Vacaville", 38.3500, -121.9800),
            nad_row(200, "Main Street", "Solano", "Fairfield", "Fairfield", 38.2500, -122.0500),
            nad_row(300, "Oak Avenue", "Solano", "Fairfield", "Fairfield", 38.2000, -122.0000),
            nad_row(300, "Oak Avenue", "Solano", "Fairfield", "Fairfield", 38.2300, -122.0000),   # 2 places ~2 mi apart
            nad_row(42, "Pine Road", "Merced", "UNINCORPORATED", "Atwater", 37.3000, -120.6000)]
    src = tmp_path / "nad_ca_r24.csv"
    with src.open("w", newline="") as f:
        w = csv.DictWriter(f, COLS)
        w.writeheader()
        w.writerows({c: r.get(c, "") for c in COLS} for r in rows)
    return nad.NadIndex(tmp_path / "nad_ca.sqlite", src)


def test_a_house_number_on_a_street_in_its_city_gives_the_address_point(index):
    p = index.lookup(48, "FAIRFIELD", 5101, street_key("BUSINESS CENTER DR"))      # Solano = CCRS county 48
    assert p["lat"] == pytest.approx(38.24005) and p["lon"] == pytest.approx(-122.06005) and p["points"] == 2


def test_the_city_scopes_the_match(index):
    assert index.lookup(48, "VACAVILLE", 200, street_key("MAIN ST"))["lat"] == pytest.approx(38.35)
    assert index.lookup(48, "FAIRFIELD", 200, street_key("MAIN ST"))["lat"] == pytest.approx(38.25)
    assert index.lookup(48, "DIXON", 200, street_key("MAIN ST")) is None


def test_no_number_or_two_places_is_no_point(index):
    assert index.lookup(48, "FAIRFIELD", 5103, street_key("BUSINESS CENTER DR")) is None
    assert index.lookup(48, "FAIRFIELD", 300, street_key("OAK AVE")) is None                 # more than one place
    assert index.lookup(48, "FAIRFIELD", 5101, street_key("BUSINESS CENTER CT")) is None     # another street type


def test_a_leading_direction_the_report_leaves_out_still_matches(index):
    assert index.lookup(48, "FAIRFIELD", 1677, street_key("TEXAS ST")) is not None


def test_unincorporated_crashes_match_in_their_county(index):
    assert index.lookup(24, "UNINCORPORATED", 42, street_key("PINE RD")) is not None        # Merced = 24


def test_no_source_file_means_no_index(tmp_path):
    idx = nad.NadIndex(tmp_path / "nad_ca.sqlite", tmp_path / "missing.csv")
    assert not idx.ready() and idx.lookup(48, "FAIRFIELD", 5101, street_key("BUSINESS CENTER DR")) is None


def write_addrfeat(path, feats):
    shp, shx, dbf = io.BytesIO(), io.BytesIO(), io.BytesIO()
    w = shapefile.Writer(shp=shp, shx=shx, dbf=dbf, shapeType=shapefile.POLYLINE)
    for name in ("FULLNAME", "LFROMHN", "LTOHN", "RFROMHN", "RTOHN"):
        w.field(name, "C", 40)
    for name, l0, l1, r0, r1, pts in feats:
        w.line([[(lon, lat) for lat, lon in pts]])
        w.record(name, l0, l1, r0, r1)
    w.close()
    with zipfile.ZipFile(path, "w") as z:
        for ext, b in ((".shp", shp), (".shx", shx), (".dbf", dbf)):
            z.writestr(f"tl_2026_06037_addrfeat{ext}", b.getvalue())


def test_tiger_address_ranges_interpolate_a_suggestion(tmp_path):
    write_addrfeat(tmp_path / "tl_2026_06037_addrfeat.zip", [
        ("Geneva Ave", "1601", "1699", "1600", "1698", [(34.00, -118.300), (34.00, -118.290)]),
        ("Geneva Ave", "1701", "1799", "1700", "1798", [(34.00, -118.290), (34.00, -118.280)])])
    a = addrfeat.Addrfeat(tmp_path)
    p = a.lookup(19, 1650, street_key("GENEVA AV"))                                        # Los Angeles = 19
    assert p["lat"] == pytest.approx(34.0) and -118.300 < p["lon"] < -118.290
    assert a.lookup(19, 1650, street_key("GENEVA AV"))["lon"] == pytest.approx(-118.3 + 0.01 * 50 / 98, abs=1e-6)
    assert a.lookup(19, 2500, street_key("GENEVA AV")) is None                             # outside every range
    assert a.lookup(19, 1650, street_key("OTHER ST")) is None
    assert addrfeat.Addrfeat(tmp_path / "none").lookup(19, 1650, street_key("GENEVA AV")) is None


# -- routing and placement ---------------------------------------------------------------------------------------
from crashiq import crashes, placement  # noqa: E402

KEYS = [street_key("Business Center Drive")]


@pytest.mark.parametrize("p, s, want", [
    ("5101 BUSINESS CENTER DR", "NOT STATED", {"number": 5101, "street": "BUSINESS CENTER DR"}),
    ("BUSINESS CENTER DR 5101", None, {"number": 5101, "street": "BUSINESS CENTER DR"}),
    ("5101 BUSINESS CENTER DR (PARKING LOT)", "BUSINESS CENTER DR", {"number": 5101, "street": "BUSINESS CENTER DR"}),
    ("5101 BUSINESS CENTER DR", "WATNEY WAY", None),              # a cross street: a street pair, not D5
    ("100 FT N OF BUSINESS CENTER DR", None, None),                # a distance
    ("5101 BUSINESS CENTER DR", "PRIVATE PROPERTY", {"number": 5101, "street": "BUSINESS CENTER DR"}),  # #397
])
def test_a_house_address_on_the_corridor_is_d5(p, s, want):
    roads = [p, s]
    on = [i for i, r in enumerate(roads) if crashes._names_street(r, KEYS)]
    assert crashes.house_address(roads, on, KEYS) == want


def test_routes_and_numbered_streets_are_not_house_addresses():
    for raw, name in (("RT 101", "US 101"), ("AVENUE 200", "Avenue 200"), ("I 405", "I 405")):
        k = [street_key(name)]
        assert crashes.house_address([raw, None], [0], k) is None, raw


@pytest.mark.parametrize("raw", [
    "380 EB OFF-RAMP TO EL CAMINO REAL",          # PR #315 Tester: the route number read as house number 380
    "I-380 EB OFF-RAMP TO EL CAMINO REAL",
    "I 380 EL CAMINO REAL",
    "US-101 EL CAMINO REAL",
    "SR-82 EL CAMINO REAL",
    "CA-82 EL CAMINO REAL",
    "EL CAMINO REAL ONR 82",
    "82 NB ON RAMP EL CAMINO REAL",
])
def test_a_route_designation_or_a_ramp_is_never_a_house_number(raw):
    k = [street_key("El Camino Real")]
    for roads in ([raw, None], [raw, "EL CAMINO REAL"]):
        on = [i for i, r in enumerate(roads) if crashes._names_street(r, k)]
        assert crashes.house_address(roads, on, k) is None, roads


def test_a_plain_address_on_el_camino_real_is_still_d5():
    k = [street_key("El Camino Real")]
    assert crashes.house_address(["380 EL CAMINO REAL", None], [0], k) == {"number": 380, "street": "EL CAMINO REAL"}


class FakeAddrfeat:
    def lookup(self, county, number, k):
        return {"lat": 38.1, "lon": -122.1}


def d5(cid, num, street="BUSINESS CENTER DR", city="FAIRFIELD", county=48):
    return {"crash_id": cid, "location_source": "unmatched", "review_reason": "house_address", "lat": None,
            "lon": None, "city": city, "county_code": county, "house_address": {"number": num, "street": street}}


def test_nad_places_the_crash_approximately_and_takes_it_off_the_review_list(index):
    result = {"crashes": [d5("a", 5101), d5("b", 9999)], "cleaning": {}}
    counts = placement.place_unmatched(None, {}, result, addresses=nad.Addresses(index, FakeAddrfeat()))
    a, b = result["crashes"]
    assert a["location_source"] == "address_nad" and a["review_reason"] is None
    assert a["approximate"]["method"] == "address_nad" and a["approximate"]["plus_minus_ft"] == 400
    assert b["location_source"] == "unmatched" and b["review_reason"] == "house_address"
    assert b["suggestion"] == {"tier": "address_tiger", "lat": 38.1, "lon": -122.1}
    assert counts["house_address"] == {"tried": 2, "placed_nad": 1, "suggested_tiger": 1}


def test_without_address_sources_house_addresses_stay_on_the_review_list():
    result = {"crashes": [d5("a", 5101)], "cleaning": {}}
    placement.place_unmatched(None, {}, result)
    assert result["crashes"][0]["review_reason"] == "house_address"


def test_an_nad_placement_is_never_an_intersection_crash():
    from crashiq import assign
    net = {"line": [[38.0, -122.0], [38.0, -121.99]], "is_freeway": False,
           "intersections": [{"id": "I1", "is_study": True, "lat": 38.0, "lon": -122.0, "station_ft": 0}],
           "segments": [{"id": "S1", "from_station_ft": 0, "to_station_ft": 2870}]}
    c = {"crash_id": "a", "location_source": "address_nad", "lat": 38.0001, "lon": -121.9999}
    a = assign.assign([c], net, 250, 100)["assignments"][0]
    assert a["kind"] == "segment"


def test_the_profile_counts_and_explains_nad_placements():
    from crashiq import profile
    from test_profile import golden
    study, n, pull, asg = golden()
    seg = [a["crash_id"] for a in asg["assignments"] if a["kind"] == "segment"][:3]
    asg = {**asg, "assignments": [{**a, "location_provenance": "address_nad"} if a["crash_id"] in seg else a
                                  for a in asg["assignments"]]}
    p = profile.build(study, n, pull, asg)
    t1 = {r["key"]: r["values"]["value"] for r in {x["id"]: x for x in p["tables"]}["T1"]["rows"]}
    assert t1["located_address_nad"] == 3
    cav = {c["key"]: c for c in p["caveats"]}["address_nad"]
    assert cav["count"] == 3 and cav["text"].startswith("3 crash reports give a house address instead of a cross street")
    assert "never at an intersection" in cav["text"]


def test_lookups_from_many_threads_at_once_match_one_thread(index):
    # #323: the server answers requests on several threads; a shared SQLite connection gave errors and wrong rows
    import threading
    asks = [(48, "FAIRFIELD", 5101, "BUSINESS CENTER DR"), (48, "VACAVILLE", 200, "MAIN ST"), (48, "FAIRFIELD", 300, "OAK AVE"),
            (24, "UNINCORPORATED", 42, "PINE RD")]
    want = [index.lookup(c, city, n, street_key(s)) for c, city, n, s in asks]
    errors, wrong, go = [], [], threading.Barrier(12)

    def work():
        go.wait()
        for _ in range(50):
            for (c, city, n, s), w in zip(asks, want):
                try:
                    if index.lookup(c, city, n, street_key(s)) != w:
                        wrong.append(s)
                except Exception as e:      # noqa: BLE001
                    errors.append(repr(e))

    ts = [threading.Thread(target=work) for _ in range(12)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    assert not errors and not wrong, f"{len(errors)} errors, {len(wrong)} wrong; first: {errors[:2]}"


# PR #315 Tester: the 15 reports the first route/ramp guard (c7abb77) changed. On a state-highway corridor the route
# named is the corridor itself, so the house number stands; only Millbrae's "380 EB OFF-RAMP" is the route.
@pytest.mark.parametrize("corridor, p, s, kept", [
    (("Happy Trails Highway", "CA 18"), "OUTER HWY 18 N", "OUTER HWY 18 N 19170", 19170),            # 2806012
    (("San Gabriel Canyon Road", "CA 39"), "RT 39", "N SAN GABRIEL CANYON RD 2350", 2350),          # 2730879
    (("San Mateo Road", "CA 92"), "SR-92 (SAN MATEO RD)", "501 SAN MATEO RD", 501),                 # 1531528
    (("San Mateo Road", "CA 92"), "501 SAN MATEO RD", "SR-92", 501),                                # 1779268
    (("San Mateo Road", "CA 92"), "501 SAN MATEO RD", "SOUTHERN FOG LINE OF HWY 92", 501),          # 1848161
    (("San Mateo Road", "CA 92"), "211 SAN MATEO RD", "SR-92", 211),                                # 1891168
    (("San Mateo Road", "CA 92"), "196 SAN MATEO RD", "SR-92", 196),                                # 4999749
    (("Beach Boulevard", "CA 39"), "18972 BEACH BLVD (SR-39)", "NOT STATED", 18972),                # 1392969
    (("Beach Boulevard", "CA 39"), "19640 BEACH (SR-39)", "NOT STATED", 19640),                     # 1437506
    (("Beach Boulevard", "CA 39"), "17642 BEACH BLVD - SR39", "NOT STATED", 17642),                 # 4522412
    (("East Palm Canyon Drive", "CA 111"), "72840 STREET HWY 111", "NOT STATED", 72840),            # 2204295
    (("East Palm Canyon Drive", "CA 111"), "72845 ST HIGHWAY 111", "NOT STATED", 72845),            # 2273165
    (("East Palm Canyon Drive", "CA 111"), "72840  ST HWY 111", "NOT STATED", 72840),               # 4470370
    (("Pacific Coast Highway", "CA 1"), "699 SOUTH COAST HWY SR1", "NOT STATED", 699),              # 4715351
    (("El Camino Real", "CA 82"), "EL CAMINO REAL", "380 EB OFF-RAMP TO EL CAMINO REAL", None),     # 4542837
])
def test_the_corridor_s_own_route_keeps_the_house_number(corridor, p, s, kept):
    k = [street_key(n) for n in corridor]
    roads = [p, s]
    on = [i for i, r in enumerate(roads) if crashes._names_street(r, k)]
    got = crashes.house_address(roads, on, k)
    assert (got and got["number"]) == kept, got
