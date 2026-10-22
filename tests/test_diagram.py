"""#106 collision diagram (N10): symbol type, marks, NCDOT stacking, numbering, layout frame."""

from crashiq import diagram

NET = {"line": [(33.8953, -118.32662), (33.9123, -118.32662)], "corridor_name": "Crenshaw Boulevard"}
IT = {"id": "i1", "name": "West 135th Street", "control": "signal", "is_study": True, "station_ft": 0}


def P(n, d, mv="PROCEEDING STRAIGHT", t="DRIVER", fault=False):
    return {"party_number": str(n), "direction": d, "movement": mv, "party_type": t, "at_fault": fault}


def C(cid, date, ct, parties, sev="O", hour=12, lighting="DAYLIGHT", surface="DRY", **kw):
    return {"crash_id": cid, "date": date, "hour": hour, "collision_type": ct, "severity": sev, "lighting": lighting,
            "surface": surface, "parties": parties, **kw}


def test_symbol_type_from_ccrs_type_movement_and_parties():
    k = lambda c: diagram.classify(c)[0]                                         # noqa: E731
    assert k(C("1", "2023-01-01", "REAR END", [P(1, "N", fault=True), P(2, "N")])) == "rear"
    assert k(C("1", "2023-01-01", "BROADSIDE", [P(1, "N", "MAKING LEFT TURN", fault=True), P(2, "S")])) == "left"
    assert k(C("1", "2023-01-01", "BROADSIDE", [P(1, "N", fault=True), P(2, "E")])) == "angle"
    assert k(C("1", "2023-01-01", "SIDE SWIPE", [P(1, "N", fault=True), P(2, "N")])) == "ss_same"
    assert k(C("1", "2023-01-01", "SIDE SWIPE", [P(1, "N", fault=True), P(2, "S")])) == "ss_opp"
    assert k(C("1", "2023-01-01", "VEHICLE/PEDESTRIAN", [P(1, "N", fault=True), P(2, "E", t="PEDESTRIAN")])) == "ped"
    assert k(C("1", "2023-01-01", "SIDE SWIPE", [P(1, "N", fault=True), P(2, "N", "PARKED", t="PARKEDVEHICLE")])) == "parked"
    assert k(C("1", "2023-01-01", "REAR END", [P(1, "S", "BACKING", fault=True), P(2, "S")])) == "backing"
    assert k(C("1", "2023-01-01", "HIT OBJECT", [P(1, "W", "RAN OFF ROAD", fault=True)])) == "ooc"
    assert k(C("1", "2023-01-01", "HIT OBJECT", [P(1, "W", fault=True)])) == "object"
    # the at-fault party is drawn, else party 1
    assert diagram.classify(C("1", "2023-01-01", "REAR END", [P(1, "N"), P(2, "E", fault=True)]))[1]["direction"] == "E"


def test_light_code_and_night():
    assert diagram.light_code({"surface": "WET", "lighting": "DARK-STREET LIGHTS"}) == ("WL", True)
    assert diagram.light_code({"surface": "DRY", "lighting": "DARK-NO STREET LIGHTS"}) == ("CN", True)
    assert diagram.light_code({"surface": "DRY", "lighting": "DAYLIGHT"}) == ("CD", False)


def test_identical_crashes_stack_numbers_follow_date_and_the_worst_mark_shows():
    cs = [C("a", "2023-05-01", "REAR END", [P(1, "N", fault=True), P(2, "N")], sev="O"),
          C("b", "2021-02-01", "REAR END", [P(1, "N", fault=True), P(2, "N")], sev="B"),
          C("c", "2022-03-01", "REAR END", [P(1, "N", fault=True), P(2, "N")], sev="O", lighting="DARK-STREET LIGHTS"),
          C("d", "2024-01-01", "BROADSIDE", [P(1, "E", fault=True), P(2, "N")], sev="K")]
    d = diagram.build(NET, IT, cs)
    assert [r["crash_id"] for r in d["crashes"]] == ["b", "c", "a", "d"] and [r["n"] for r in d["crashes"]] == [1, 2, 3, 4]
    assert d["stacks"] == 3                                     # b + a share a symbol; c differs in light; d its own
    labels = [s["t"] for s in d["steps"] if s["op"] == "text" and s["color"] == "muted" and s["t"][0].isdigit()]
    assert sorted(labels) == ["1, 3", "2", "4"]
    rings = [s for s in d["steps"] if s["op"] == "circle" and s["stroke"].startswith("sev_")]
    assert any(s["stroke"] == "sev_b" for s in rings)            # the stack of B + O shows the B ring
    assert any(s["op"] == "circle" and s["fill"] == "sev_k" for s in d["steps"])        # fatal: filled
    assert all(0 <= x <= d["width"] and 0 <= y <= d["height"] for s in d["steps"] if s["op"] == "line"
               for x, y in s["pts"])


def test_crashes_without_party_data_are_listed_not_drawn():
    cs = [C("x", "2025-03-01", "REAR END", []), C("y", "2023-03-01", "REAR END", [P(1, "S", fault=True), P(2, "S")])]
    d = diagram.build(NET, IT, cs)
    assert d["not_drawn"] == {"no_party_data": 1, "no_direction": 0, "no_room": 0}
    assert {r["crash_id"]: r["approach"] for r in d["crashes"]} == {"y": "SB", "x": "—"}
