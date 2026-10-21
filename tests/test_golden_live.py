"""Golden tables on LIVE data (#53): every profile number recounted from the raw recorded CCRS rows, by code that
shares nothing with the app's cleaning. The app decides which crashes are in the study (assignment, tested
elsewhere); this file checks that T1 and T3-T11 count those crashes correctly from what CHP published.

Fixtures: tests/fixtures/live/ (record_live_fixture.py): Crenshaw Blvd (LA County, GPS on most reports) and Union
City Blvd (Union City PD records no GPS, #35), 2021-2025."""

from __future__ import annotations

import json
from collections import Counter, defaultdict

import pytest

from crashiq import assign, crashes, network, placement, profile
from crashiq.sources.ckan import Ckan
from crashiq.sources.fake_ckan import FakeCkan

from conftest import FIXTURES

LIVE = FIXTURES / "live"
STUDY = {"id": "golden", "from_year": 2021, "to_year": 2025, "radius_ft": 250, "buffer_ft": 100,
         "covid_years_in_window": False}

# The reference's own reading of CHP's codes (deliberately not imported from the app)
LEVEL = {"Fatal": "K", "SuspectSerious": "A", "SevereInactive": "A", "SuspectMinor": "B",
         "OtherVisibleInactive": "B", "PossibleInjury": "C", "ComplaintOfPainInactive": "C"}
RANK = "KABCUO"


def run(name, monkeypatch, cities=None):
    line = [tuple(p) for p in json.loads((LIVE / f"line_{name}.json").read_text())]
    osm = json.loads((LIVE / f"overpass_{name}.json").read_text())
    found = network.detect(osm, line)
    ints = [{**i, "is_study": True} for i in found["intersections"]]
    net = {"line": line, **found, "intersections": ints, "segments": network.segments(ints, found["length_ft"]),
           "length_mi": found["length_ft"] / 5280, "is_freeway": found["corridor_highway"] == "motorway", "cities": cities}
    monkeypatch.setattr(network, "fetch_overpass", lambda db, q: osm)
    pull = crashes.pull(STUDY, net, Ckan(FakeCkan(LIVE / f"ckan_{name}.json"), retries=0))
    placement.place_unmatched(None, net, pull)
    a = assign.assign(pull["crashes"], net, STUDY["radius_ft"], STUDY["buffer_ft"])
    return net, pull, a, profile.build(STUDY, net, pull, a)


def raw_tables(name):
    d = json.loads((LIVE / f"ckan_{name}.json").read_text())
    kind = {r["id"]: r["name"].split("_")[0] for r in d["package"]["resources"]}
    out = defaultdict(list)
    for rid, t in d["tables"].items():
        out[kind[rid]].extend(t["rows"])
    return out


def reference(name, study_ids: set[str]):
    """Recount from raw rows: one row per crash (live CCRS has one per Collision Id), severity from IWP."""
    raw = raw_tables(name)
    crash = {str(r["Collision Id"]): r for r in raw["Crashes"] if str(r["Collision Id"]) in study_ids}
    levels = defaultdict(list)
    for r in raw["InjuredWitnessPassengers"]:
        if str(r.get("IsWitnessOnly")) != "True" and r.get("ExtentOfInjuryCode") in LEVEL:
            levels[str(r["CollisionId"])].append(LEVEL[r["ExtentOfInjuryCode"]])
    types = defaultdict(set)
    for r in raw["Parties"]:
        types[str(r["CollisionId"])].add(str(r.get("PartyType")))
    sev = {}
    for cid, r in crash.items():
        if int(r["NumberKilled"] or 0) > 0:
            sev[cid] = "K"
        elif levels[cid]:
            sev[cid] = min(levels[cid], key=RANK.index)
        else:
            sev[cid] = "U" if int(r["NumberInjured"] or 0) > 0 else "O"
    return crash, sev, types


@pytest.fixture(scope="module", params=["crenshaw", "unioncity"])
def case(request):
    mp = pytest.MonkeyPatch()
    try:
        net, pull, a, p = run(request.param, mp)
    finally:
        mp.undo()
    ids = {x["crash_id"] for x in a["assignments"] if x["kind"] in ("intersection", "segment")}
    return request.param, pull, a, p, ids, *reference(request.param, ids)


def table(p, tid):
    return {r["key"]: r["values"] for r in next(t for t in p["tables"] if t["id"] == tid)["rows"]}


def test_every_study_crash_is_in_the_raw_rows(case):
    _, _, _, _, ids, crash, _, _ = case
    assert ids and set(crash) == ids


def test_T1_summary(case):
    _, _, a, p, ids, crash, sev, _ = case
    t1 = table(p, "T1")
    sv = Counter(sev.values())
    assert t1["crashes"]["value"] == len(ids)
    assert t1["ksi_crashes"]["value"] == sv["K"] + sv["A"]
    assert t1["fatal_crashes"]["value"] == sv["K"]
    assert t1["injury_crashes"]["value"] == sum(sv[k] for k in "KABCU")
    assert t1["pdo_crashes"]["value"] == sv["O"]
    assert t1["killed"]["value"] == sum(int(r["NumberKilled"] or 0) for r in crash.values())
    assert t1["injured"]["value"] == sum(int(r["NumberInjured"] or 0) for r in crash.values())
    assert t1["dark_crashes"]["value"] == sum("DARK" in str(r.get("LightingDescription") or "") for r in crash.values())
    assert t1["excluded"]["value"] == a["counts"]["excluded"] and t1["unplaced"]["value"] == a["counts"]["unmatched"]


def test_T3_severity(case):
    _, _, _, p, _, _, sev, _ = case
    t3 = table(p, "T3")
    sv = Counter(sev.values())
    assert {k: t3[k]["crashes"] for k in RANK} == {k: sv[k] for k in RANK}


@pytest.mark.parametrize("tid,col", [("T4", "Collision Type Description"), ("T6", "LightingDescription"),
                                     ("T7", "Weather 1")])
def test_T4_T6_T7_distributions(case, tid, col):
    _, _, _, p, _, crash, sev, _ = case
    want = Counter(str(r.get(col) or "").replace("PEDESTRAIN", "PEDESTRIAN").strip().upper() or "NOT_STATED"
                   for r in crash.values())
    got = {k.upper(): v["crashes"] for k, v in table(p, tid).items()}
    assert got == dict(want)
    ksi = Counter(str(r.get(col) or "").replace("PEDESTRAIN", "PEDESTRIAN").strip().upper() or "NOT_STATED"
                  for cid, r in crash.items() if sev[cid] in "KA")
    assert {k: v for k, v in ((k.upper(), v["ksi_crashes"]) for k, v in table(p, tid).items()) if v} == dict(ksi)


def test_T5_one_row_per_violation(case):
    _, _, _, p, _, crash, _, _ = case
    def vc(v):
        t = str(v or "").upper().replace("CVC", "").replace("VC", "").replace("(", "").replace(")", "").replace(" ", "")
        return t or "NOT_STATED"
    assert {k.upper(): v["crashes"] for k, v in table(p, "T5").items()} == dict(Counter(
        vc(r.get("Primary Collision Factor Violation")) for r in crash.values()))


def test_T8_surface(case):
    _, _, _, p, _, crash, _, _ = case
    code = {"A": "DRY", "B": "WET", "C": "SNOWY-ICY", "D": "SLIPPERY (MUDDY, OILY, ETC.)"}
    want = Counter(code.get(str(r.get("RoadwaySurfaceCode") or ""), "NOT_STATED") for r in crash.values())
    assert {k.upper(): v["crashes"] for k, v in table(p, "T8").items()} == dict(want)


def test_T9_day_and_hour(case):
    _, _, _, p, _, crash, _, _ = case
    t9 = table(p, "T9")
    want = Counter((r["Day Of Week"], int(r["Crash Date Time"][11:13])) for r in crash.values())
    got = Counter({(d, int(h)): n for d, vals in t9.items() for h, n in vals.items() if h.isdigit() and n})
    assert got == want


def test_T10_road_users(case):
    _, _, _, p, _, crash, sev, types = case
    t10 = table(p, "T10")
    ped = {cid for cid, r in crash.items() if "Pedestrian" in types[cid]
           or "PEDESTRIAN" in str(r.get("MotorVehicleInvolvedWithDesc") or "")
           or "PEDESTR" in str(r.get("Collision Type Description") or "")}
    bike = {cid for cid, r in crash.items() if "Bicyclist" in types[cid]
            or "BICYCLE" in str(r.get("MotorVehicleInvolvedWithDesc") or "")}
    assert (t10["ped"]["crashes"], t10["bike"]["crashes"]) == (len(ped), len(bike))
    assert t10["ped"]["ksi_crashes"] == sum(sev[c] in "KA" for c in ped)


def test_T11_by_year(case):
    _, _, _, p, _, crash, sev, _ = case
    t11 = table(p, "T11")
    want = Counter(r["Crash Date Time"][:4] for r in crash.values())
    assert {k: v["crashes"] for k, v in t11.items()} == dict(want)


def test_T2_locations_add_up(case):
    _, _, _, p, ids, _, _, _ = case
    assert sum(v["crashes"] for v in table(p, "T2").values()) == len(ids)


def test_fixture_covers_the_hard_cases():
    """#53: the hand fixture lacked these; the live one must keep them."""
    raw = raw_tables("crenshaw")
    iwp, cr, pa = raw["InjuredWitnessPassengers"], raw["Crashes"], raw["Parties"]
    assert any(r["ExtentOfInjuryCode"] == "Fatal" for r in iwp)
    assert any(str(r.get("IsWitnessOnly")) == "True" for r in iwp)
    assert any(r.get("PartyType") == "Bicyclist" for r in pa)
    assert any("Truck" in str(r.get("Vehicle1TypeDesc")) for r in pa)
    assert any(r.get("SecondaryUnitOfMeasure") == "M" for r in cr)
    assert any(str(r.get("Primary Collision Factor Violation") or "").startswith("VC ") for r in cr)


def test_every_placed_crash_has_a_station_for_the_strip_diagram(case):
    # #102: the strip draws one dot per placed crash at its station; T1 crashes = dots
    _, _, a, p, ids, _, _, _ = case
    placed = [x for x in a["assignments"] if x["kind"] in ("intersection", "segment")]
    assert len(placed) == table(p, "T1")["crashes"]["value"] == len(ids)
    assert all(x.get("station_ft") is not None and x["station_ft"] >= 0 for x in placed)


def test_T14_T17_safety_tables(case):
    # #52: hit-and-run from CCRS HitRun, DUI / speed from the PCF section, broadside split by party movement
    _, _, _, p, ids, crash, sev, _ = case
    raw = raw_tables(case[0])
    t14 = table(p, "T14")
    hr = {cid for cid, r in crash.items() if r.get("HitRun") in ("F", "M")}
    assert t14["hit_and_run"]["crashes"] == len(hr)
    assert t14["hit_and_run_felony"]["crashes"] == sum(crash[c].get("HitRun") == "F" for c in hr)
    sec = lambda r: str(r.get("Primary Collision Factor Violation") or "").upper().replace("VC", "").replace(" ", "")
    assert t14["dui"]["crashes"] == sum(sec(r).startswith(("23152", "23153")) for r in crash.values())
    assert t14["speed"]["crashes"] == sum(sec(r).startswith("22350") for r in crash.values())
    assert t14["dui"]["ksi_crashes"] == sum(sev[c] in "KA" for c, r in crash.items() if sec(r).startswith(("23152", "23153")))
    left = {str(r["CollisionId"]) for r in raw["Parties"] if str(r.get("MovementPrecCollDescription") or "").upper() == "MAKING LEFT TURN"}
    broad = {c for c, r in crash.items() if r.get("Collision Type Description") == "BROADSIDE"}
    t17 = table(p, "T17")
    assert (t17["left_turn"]["crashes"], t17["right_angle"]["crashes"]) == (len(broad & left), len(broad - left))
    assert sum(v["crashes"] for v in table(p, "T16").values()) == len(ids)


# Heavy truck (#52, user decision 2C): 3+ axles or a truck-tractor; CCRS carries axles only in the type code.
REF_HEAVY = {"TruckTractor", "ThreeOrMoreAxleTruck", "ThreeAxleTankTruck", "ThreeAxleTowTruck"}
REF_TRAILER = {"SemiTrailer", "SemiTankTrailer", "PullTrailer", "PullTankTrailer", "TwoTrailersIncludesSemiAndPull",
               "TwoTankTrailer", "ThreeTrailers", "ContainerChassis", "FederallyLegalSemi",
               "FederallyLegalDoubleComboOver75FeetLong"}


def test_T10_heavy_truck_is_three_axles_or_a_tractor(case):
    name, _, _, p, ids, _, _, _ = case
    raw = raw_tables(name)
    heavy = set()
    for r in raw["Parties"]:
        types = {str(r.get("Vehicle1TypeDesc") or ""), str(r.get("Vehicle2TypeDesc") or "")}
        if {t.removeprefix("Hmw").removeprefix("Hm") for t in types} & REF_HEAVY or r.get("Vehicle1TypeDesc") in REF_TRAILER:
            heavy.add(str(r["CollisionId"]))
    assert table(p, "T10")["heavy_truck"]["crashes"] == len(heavy & set(ids))


def test_T18_pcf_categories_match_the_testers_coverage(case):
    # #52 (1A): the Tester's own parser and crosswalk reading (tests/statewide/pcf_coverage.py) on the raw rows
    # must give the same outcome per crash as the app's T18.
    import csv
    import sys
    sys.path.insert(0, str(FIXTURES.parents[1] / "tests" / "statewide"))
    import pcf_coverage as ref
    _, _, _, p, ids, crash, _, _ = case
    rows = list(csv.DictReader((FIXTURES.parents[1] / "data" / "reference" / "pcf_categories.csv").open()))
    xw = {(r["section"], r["subsection"]): r for r in rows if r["key_type"] == "section"}
    want = Counter()
    for r in crash.values():
        k = ref.parse(r.get("Primary Collision Factor Violation"))
        if k == "blank":
            want["blank"] += 1
        elif k is None:
            want["words"] += 1
        elif k not in xw:
            want["unlisted"] += 1
        else:
            st, cat = xw[k]["status"], xw[k]["category"]
            if st == "split":           # user decision 2026-10-20: the 2024 category, every year
                y24 = dict(p.split() for p in xw[k]["split_by_year"].split("; ")).get("2024")
                if y24:
                    st, cat = ("unknown", "00") if y24.startswith("00:") else ("mapped", y24.split(":")[0])
            want[f"cat_{cat}" if st == "mapped" else st] += 1
    got = {k: v["crashes"] for k, v in table(p, "T18").items()}
    assert got == dict(want)
    assert sum(got.values()) == len(ids)


def _ref_ped_bike(crash, types):
    ped = {cid for cid, r in crash.items() if "Pedestrian" in types[cid]
           or "PEDESTRIAN" in str(r.get("MotorVehicleInvolvedWithDesc") or "")
           or "PEDESTR" in str(r.get("Collision Type Description") or "")}
    bike = {cid for cid, r in crash.items() if "Bicyclist" in types[cid]
            or "BICYCLE" in str(r.get("MotorVehicleInvolvedWithDesc") or "")}
    return ped, bike


def test_T19_how_dangerous_matches_raw_rows(case):
    # #136: KSI share of pedestrian, bicycle and all other crashes, and the ped+bike share of all KSI crashes
    _, _, _, p, ids, crash, sev, types = case
    ped, bike = _ref_ped_bike(crash, types)
    vru = ped | bike
    other = set(crash) - vru
    ksi = {c for c in crash if sev[c] in "KA"}
    pct = lambda a, b: round(100 * a / b, 1) if b else 0.0
    t = table(p, "T19")
    for key, grp in (("ped", ped), ("bike", bike), ("ped_or_bike", vru), ("other", other), ("all", set(crash))):
        assert t[key]["crashes"] == len(grp), key
        assert t[key]["ksi_crashes"] == len(grp & ksi), key
        assert t[key]["ksi_pct"] == (pct(len(grp & ksi), len(grp)) if grp else None), key   # no crashes: no %
        assert t[key]["share_of_ksi_pct"] == pct(len(grp & ksi), len(ksi)), key
    assert t["ped_or_bike"]["crashes"] + t["other"]["crashes"] == len(ids)


def test_T20_pedestrian_lighting_matches_raw_rows(case):
    _, _, _, p, _, crash, _, types = case
    ped, _ = _ref_ped_bike(crash, types)

    def group(t):
        t = (t or "").upper()
        if not t:
            return "not_stated"
        if t.startswith("DARK"):
            return "dark_unlit" if ("NO STREET" in t or "NOT FUNCTION" in t) else "dark_lit"
        return "dusk_dawn" if "DUSK" in t else "daylight" if t == "DAYLIGHT" else "not_stated"
    want = Counter(group(crash[c].get("LightingDescription")) for c in ped)
    got = {k: v["crashes"] for k, v in table(p, "T20").items() if v["crashes"]}
    assert got == dict(want)


def test_T2_ped_bike_column_adds_up(case):
    _, _, _, p, _, crash, sev, types = case
    ped, bike = _ref_ped_bike(crash, types)
    t2 = table(p, "T2")
    assert sum(v["vru_crashes"] for v in t2.values()) == len(ped | bike)
    assert sum(v["vru_ksi_crashes"] for v in t2.values()) == sum(sev[c] in "KA" for c in ped | bike)


def test_a_corridor_crossing_into_the_next_city_keeps_both_cities(monkeypatch):
    # #142: Union City Blvd runs into Fremont as Ardenwood Blvd (#53). Reports from both cities stay; a city the line
    # doesn't enter loses its no-GPS reports.
    _, _, a0, _ = run("unioncity", monkeypatch)
    _, pull, a, _ = run("unioncity", monkeypatch, {"cities": ["Union City", "Fremont"], "outside": False, "counties": []})
    assert a["assignments"] == a0["assignments"] and pull["cleaning"]["no_coords_other_city"] == 0
    _, pull, a, _ = run("unioncity", monkeypatch, {"cities": ["Union City"], "outside": False, "counties": []})
    assert pull["cleaning"]["other_cities"].get("Fremont", 0) > 0
    assert all(c.get("city") != "Fremont" or c["location_source"] == "gps" for c in pull["crashes"])
