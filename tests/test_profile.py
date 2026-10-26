"""Golden profile: 50 placed crashes built by hand (+6 unplaced, +4 excluded); every expected number below was
worked out on paper from how the set is built, not by running the code."""

import pytest

from crashiq import profile


def golden():
    crashes, assignments = [], []
    n = 0

    def add(loc, kind, sev, ctype, dark=False, ped=False, prelim=False, injured=None, prov="gps"):
        nonlocal n
        n += 1
        cid = f"c{n:03d}"
        crashes.append({
            "crash_id": cid, "year": 2021 + (n - 1) % 5, "severity": sev, "collision_type": ctype,
            "killed": 1 if sev == "K" else 0,
            "injured": injured if injured is not None else (1 if sev in "ABCU" else 0),
            "lighting": "DARK-STREET LIGHTS" if dark else "DAYLIGHT", "ped": ped, "bike": False,
            "motorcycle": False, "heavy_truck": False, "preliminary": prelim, "day_of_week": "Friday",
            "hour": 17, "pcf": "VC 22350", "weather": "Clear", "surface": "DRY"})
        assignments.append({"crash_id": cid, "kind": kind, "location_id": loc, "location_provenance": prov})

    # Intersection I1: 30 crashes. K 1, A 2, B 5, C 7, O 15. Broadside 20 (incl. K and both A), rear end 10.
    add("I1", "intersection", "K", "BROADSIDE", dark=True, ped=True)
    add("I1", "intersection", "A", "BROADSIDE", dark=True)
    add("I1", "intersection", "A", "BROADSIDE", ped=True)
    for i in range(5):
        add("I1", "intersection", "B", "BROADSIDE", dark=i < 2)
    for i in range(7):
        add("I1", "intersection", "C", "BROADSIDE", dark=i < 2, injured=2 if i == 0 else None)
    for i in range(15):
        add("I1", "intersection", "O", "BROADSIDE" if i < 5 else "REAR END", prelim=i < 3)
    # Segment S1: 20 crashes. A 1, B 4, U 1, O 14. Rear end 8 (incl. the A), side swipe 12. Dark 4.
    add("S1", "segment", "A", "REAR END", dark=True)
    for i in range(4):
        add("S1", "segment", "B", "REAR END", dark=i < 3, prov="jev(0.95)" if i < 2 else "gps")
    add("S1", "segment", "U", "SIDE SWIPE", prov="jev(0.91)")
    for i in range(14):
        add("S1", "segment", "O", "REAR END" if i < 3 else "SIDE SWIPE", prov="jev(0.97)" if i < 2 else "gps")
    for i in range(6):
        add(None, "unmatched", "O", "REAR END", prov="unmatched")
    for i in range(4):
        add(None, "excluded", "O", "REAR END")

    study = {"id": "s", "from_year": 2021, "to_year": 2025, "covid_years_in_window": False}
    net = {"length_mi": 1.0,
           "intersections": [{"id": "I1", "name": "Main St", "station_ft": 1000, "is_study": True, "control": "signal",
                              "major_aadt": 30000, "minor_aadt": 10000}],
           "segments": [{"id": "S1", "name": "Main St – End", "from_station_ft": 1000, "to_station_ft": 4168,
                         "length_mi": 0.6, "aadt": 20000}]}
    pull = {"crashes": crashes, "years": [2021, 2022, 2023, 2024, 2025], "cleaning": {"years_missing": []},
            "source": "test", "pulled_at": "2026-10-18"}
    return study, net, pull, {"assignments": assignments}


def P(**kw):
    return profile.build(*golden(), **kw)


def v(p, addr):
    return profile.cell(p["tables"], addr)


def test_summary_table():
    p = P()
    expect = {"crashes": 50, "crashes_per_year": 10.0, "ksi_crashes": 4, "fatal_crashes": 1, "injury_crashes": 21,
              "pdo_crashes": 29, "killed": 1, "injured": 21, "dark_crashes": 10, "years": 5, "length_mi": 1.0,
              "crashes_per_mi_yr": 10.0, "unplaced": 6, "excluded": 4}
    for k, val in expect.items():
        assert v(p, f"T1/{k}/value") == val, k


def test_locations_with_rates():
    p = P()
    assert [r["key"] for r in p["tables"][1]["rows"]] == ["I1", "S1"]
    assert v(p, "T2/I1/crashes") == 30 and v(p, "T2/I1/crashes_per_year") == 6.0 and v(p, "T2/I1/ksi_crashes") == 3
    assert v(p, "T2/I1/rate") == 0.41                         # 30e6 / (365 × 5 × 40,000)
    assert v(p, "T2/S1/crashes") == 20 and v(p, "T2/S1/ksi_crashes") == 1
    assert v(p, "T2/S1/crashes_per_mi_yr") == 6.67             # 20 / 0.6 / 5
    assert v(p, "T2/S1/rate") == 91.32                         # 20e8 / (365 × 5 × 20,000 × 0.6)


def test_severity_once_per_crash():
    p = P()
    got = {k: (v(p, f"T3/{k}/crashes"), v(p, f"T3/{k}/share_pct")) for k in "KABCUO"}
    assert got == {"K": (1, 2.0), "A": (3, 6.0), "B": (9, 18.0), "C": (7, 14.0), "U": (1, 2.0), "O": (29, 58.0)}
    assert sum(c for c, _ in got.values()) == v(p, "T1/crashes/value")   # each crash exactly once


def test_collision_type_and_road_users():
    p = P()
    assert [(r["key"], r["values"]["crashes"], r["values"]["ksi_crashes"], r["values"]["share_pct"])
            for r in p["tables"][3]["rows"]] == [("BROADSIDE", 20, 3, 40.0), ("REAR END", 18, 1, 36.0),
                                                 ("SIDE SWIPE", 12, 0, 24.0)]
    assert v(p, "T10/ped/crashes") == 2 and v(p, "T10/ped/ksi_crashes") == 2   # the K and one A
    assert [v(p, f"T11/{y}/crashes") for y in range(2021, 2026)] == [10] * 5
    assert v(p, "T9/Friday/17") == 50


def test_rate_formulas():
    assert profile.segment_rate(20, 5, 20000, 0.6) == pytest.approx(91.3242, rel=1e-5)
    assert profile.intersection_rate(30, 5, 30000, 10000) == pytest.approx(0.410959, rel=1e-5)
    assert profile.segment_rate(20, 5, None, 0.6) is None
    assert profile.intersection_rate(30, 5, None, 1000) is None


def test_no_aadt_means_rates_not_computed():
    study, net, pull, a = golden()
    net["intersections"][0].update(major_aadt=None, minor_aadt=None)
    net["segments"][0]["aadt"] = None
    p = profile.build(study, net, pull, a)
    assert v(p, "T2/I1/rate") is None and v(p, "T2/S1/rate") is None
    assert any(c["key"] == "rates_not_computed" for c in p["caveats"])


def test_caveats_only_when_they_apply():
    p = P()
    keys = {c["key"]: c for c in p["caveats"]}
    assert keys["preliminary"]["count"] == 3
    assert keys["unplaced"]["count"] == 6 and keys["unplaced"]["limitation"] is True      # 6/56 = 10.7% > 10%
    assert keys["injury_level_unknown"]["count"] == 1
    assert "covid" not in keys and "rates_not_computed" not in keys
    study, net, pull, a = golden()
    study["covid_years_in_window"] = True
    assert any(c["key"] == "covid" for c in profile.build(study, net, pull, a)["caveats"])


def test_provenance_mix_and_exclude_jev_rerun():
    p = P()
    assert p["location_provenance"] == {"gps": 45, "jev(0.91)": 1, "jev(0.95)": 2, "jev(0.97)": 2, "unmatched": 6}
    assert p["tables"][0]["provenance"] == {"gps": 45, "jev(0.91)": 1, "jev(0.95)": 2, "jev(0.97)": 2}
    q = P(exclude={"jev"})
    assert v(q, "T1/crashes/value") == 45 and v(q, "T2/S1/crashes") == 15
    assert v(q, "T3/U/crashes") == 0                            # the U crash was jev-placed
    assert any(c["key"] == "excluded_provenance" for c in q["caveats"])
    # #53: the left-out crashes have their own T1 row, so the summary still adds up to every assigned crash
    assert v(q, "T1/excluded_provenance/value") == 5
    assert (v(q, "T1/crashes/value") + v(q, "T1/unplaced/value") + v(q, "T1/excluded/value")
            + v(q, "T1/excluded_provenance/value")) == len(golden()[3]["assignments"])


def test_every_kpi_address_resolves():
    p = P()
    for addr in p["kpis"].values():
        assert v(p, addr) is not None


def test_api_profile_on_crenshaw(client):
    from conftest import FIXTURES
    from crashiq.sources.fake_ckan import FakeCkan
    client.app.state.overpass = lambda url, data, timeout: (FIXTURES / "overpass_crenshaw.json").read_bytes()
    client.app.state.ckan = FakeCkan(FIXTURES / "ckan_crenshaw.json")
    sid = client.post("/api/studies", json={"name": "Crenshaw", "mode": "profile"}).json()["id"]
    client.put(f"/api/studies/{sid}/corridor", json={"line": [[33.8953, -118.32662], [33.9123, -118.32662]]})
    client.post(f"/api/studies/{sid}/crashes/pull")
    p = client.get(f"/api/studies/{sid}/profile").json()
    a = client.get(f"/api/studies/{sid}/assignment").json()["counts"]
    assert profile.cell(p["tables"], "T1/crashes/value") == a["intersection"] + a["segment"]
    assert profile.cell(p["tables"], "T1/unplaced/value") == 0  # the 4 no-GPS Crenshaw reports are now placed by the locator (#35, PR #36)
    first = p["tables"][1]["rows"][0]["key"]
    loc = client.get(f"/api/studies/{sid}/profile/locations/{first}").json()
    assert loc["tables"][0]["id"] == f"T3@{first}"
    assert len(loc["crashes"]) == profile.cell(p["tables"], f"T2/{first}/crashes")


def test_t2_carries_each_locations_severity_split_and_rate_ratio():
    # #103 location ranking: the severity bar and the "rate vs critical" sort come from T2, not the frontend
    p = P()
    for r in next(t for t in p["tables"] if t["id"] == "T2")["rows"]:
        v = r["values"]
        assert sum(v[f"sev_{k}"] for k in "kabcuo") == v["crashes"]
        assert v["sev_k"] + v["sev_a"] == v["ksi_crashes"]
        if v["critical_rate"]:
            assert v["rate_to_critical"] == round(v["rate"] / v["critical_rate"], 2) or abs(
                v["rate_to_critical"] - v["rate"] / v["critical_rate"]) < 0.02


def test_t11_has_every_window_year_with_the_split_preliminary_and_covid():
    # #104 year trend: zero years kept; injury + property damage = crashes; COVID years flagged per docs/03
    p = P()
    t11 = next(t for t in p["tables"] if t["id"] == "T11")
    years = [int(r["key"]) for r in t11["rows"]]
    assert years == list(range(2021, 2026))
    for r in t11["rows"]:
        v = r["values"]
        assert v["injury_crashes"] + v["pdo_crashes"] == v["crashes"]
        assert v["covid"] == ("Yes" if int(r["key"]) in (2020, 2021) else "No")
        assert 0 <= v["preliminary"] <= v["crashes"]
        assert sum(v[f"sev_{k}"] for k in "kabcuo") == v["crashes"]          # #104 round 1: the trend stacks the ramp
    assert sum(r["values"]["crashes"] for r in t11["rows"]) == v_(p, "T1/crashes/value")


def v_(p, addr):
    return profile.cell(p["tables"], addr)


def test_t1_location_sources_add_up_to_crashes():
    # #104 data-quality strip: every counted crash is in exactly one "how located" row
    p = P()
    parts = ("located_gps", "located_fars", "located_exact", "located_other", "user_placed")
    assert sum(v_(p, f"T1/{k}/value") for k in parts) == v_(p, "T1/crashes/value")


def test_t13_collision_type_by_location_matches_t2_and_t4():
    # #105 grid: rows = T2 locations in corridor order; each row sums to the location's crashes; columns to T4
    p = P()
    t2 = next(t for t in p["tables"] if t["id"] == "T2")
    t4 = next(t for t in p["tables"] if t["id"] == "T4")
    t13 = next(t for t in p["tables"] if t["id"] == "T13")
    assert [r["key"] for r in t13["rows"]] == [r["key"] for r in t2["rows"]]
    cols = [c["key"] for c in t13["columns"] if c["key"] != "total"]
    for r, l in zip(t13["rows"], t2["rows"]):
        assert sum(r["values"][k] for k in cols) == r["values"]["total"] == l["values"]["crashes"]
    for row in t4["rows"]:
        assert sum(r["values"][row["key"]] for r in t13["rows"]) == row["values"]["crashes"]
    assert all("moto_crashes" in r["values"] for r in t2["rows"])


def test_distribution_rows_carry_the_severity_split():
    # #119: collision-type bars stack the ramp; every T4..T8 row's severity split sums to its crashes
    p = P()
    for tid in ("T4", "T5", "T6", "T7", "T8"):
        for r in next(t for t in p["tables"] if t["id"] == tid)["rows"]:
            v = r["values"]
            assert sum(v[f"sev_{k}"] for k in "kabcuo") == v["crashes"]
            assert v["sev_k"] + v["sev_a"] == v["ksi_crashes"]


def test_t9_has_a_day_not_stated_row_only_when_needed():
    p = P()
    t9 = next(t for t in p["tables"] if t["id"] == "T9")
    total = sum(v for r in t9["rows"] for k, v in r["values"].items())
    assert total == v_(p, "T1/crashes/value")


def test_count_caveats_agree_in_number():
    # #266: "1 crash on this corridor (0.5%) have no coordinates and aren't placed yet"
    from crashiq.profile import unplaced_text
    assert unplaced_text(1, 0.5, 0, False) == "1 crash on this corridor (0.5%) has no coordinates and isn't placed yet."
    assert unplaced_text(3, 1.6, 0, False) == "3 crashes on this corridor (1.6%) have no coordinates and aren't placed yet."
    assert unplaced_text(1, 0.5, 1, False) == ("1 crash on this corridor (0.5%) has no coordinates and isn't placed yet, "
                                               "including 1 fatal or serious-injury crash not in the KSI count.")
    assert unplaced_text(4, 12.0, 2, True).endswith("including 2 fatal or serious-injury crashes not in the KSI count. "
                                                    "This is a data limitation for this study.")


def test_the_stale_findings_note_agrees_in_number():
    from crashiq.export import stale_text
    assert stale_text(1) == ("1 accepted finding no longer matches the data after a study change and is left out "
                             "until reviewed again.")
    assert stale_text(2).startswith("2 accepted findings no longer match the data") and "and are left out" in stale_text(2)


def test_the_approximate_and_gps_far_caveats_agree_in_number():
    # PM review of #284: "1 crash has a GPS point ... They are counted where the GPS puts them"
    from crashiq.profile import approximate_text, gps_far_text
    one, two = gps_far_text(1, 400), gps_far_text(2, 400)
    assert one.startswith("1 crash has a GPS point more than 400 ft") and "It is counted where the GPS puts it; check it" in one
    assert two.startswith("2 crashes have") and "They are counted where the GPS puts them; check them" in two
    one, two = approximate_text(1), approximate_text(3)
    assert one.startswith("1 freeway crash has no usable GPS and is placed") and "It counts" in one and "leave it out" in one
    assert two.startswith("3 freeway crashes have") and "They count" in two and "leave them out" in two
