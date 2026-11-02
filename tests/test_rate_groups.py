"""Caltrans rate groups and the statewide expected rate (#287 part 1; user decision 2026-10-29, docs/03 #294)."""

import pytest

from crashiq import rate_groups


def test_the_table_has_every_group_of_the_book():
    t = rate_groups.table()
    assert [g for g in t if g[0] == "H"] == [f"H{i:02d}" for i in range(1, 68)]
    assert [g for g in t if g[0] == "I"] == [f"I{i:02d}" for i in range(1, 32)]
    assert [g for g in t if g[0] == "R"] == [f"R{i:02d}" for i in range(1, 81)]
    h01 = t["H01"]
    assert (h01["base_rate"], h01["adt_factor"], h01["adt_op"], h01["pct_fatal"], h01["pct_fi"]) == (1.09, 0.0, "", 3.0, 43.7)
    assert h01["kind"] == "highway" and h01["label"] == "Conventional 2 lanes or less, flat, design speed <=55, rural"
    assert t["I14"]["label"] == "Intersection F, M and S, signals, urban"
    assert t["R10"]["label"] == "Ramp diamond, 1-4 areas, off, urban"


@pytest.mark.parametrize("factor, op, adt, add", [
    (0.60, "/", 5000, 0.12),       # the table's note: "0.60/" with 5,000 ADT adds 0.12
    (0.017, "*", 20000, 0.34),     # "0.017" (times) with 20,000 ADT adds 0.34
    (0.0, "", 20000, 0.0),
])
def test_the_adt_factor_follows_the_table_s_note(factor, op, adt, add):
    assert rate_groups.adt_add(factor, op, adt) == pytest.approx(add)


def test_the_expected_rate_is_base_plus_adt_factor_with_the_group_s_severity_shares():
    e = rate_groups.expected("H03", 10000)            # 1.28 + 0.188 / 10
    assert e["expected_all"] == pytest.approx(1.2988)
    assert e["expected_fi"] == pytest.approx(1.2988 * 0.459)
    assert e["expected_fatal"] == pytest.approx(1.2988 * 0.023)
    assert rate_groups.expected("H62", 150000)["expected_all"] == pytest.approx(0.89 + 0.001 * 150)


def test_a_divided_factor_needs_an_adt_and_an_unknown_group_has_no_expected_rate():
    assert rate_groups.expected("H03", None) is None
    assert rate_groups.expected("H03", 0) is None
    assert rate_groups.expected("H01", None)["expected_all"] == pytest.approx(1.09)   # no factor: no ADT needed
    assert rate_groups.expected("H99", 1000) is None


@pytest.mark.parametrize("kind, group, ok", [
    ("segment", "H07", True), ("segment", "h 07", True), ("intersection", "I14", True), ("ramp", "R80", True),
    ("segment", "I14", False), ("ramp", "H07", False), ("segment", "H68", False),
])
def test_a_group_must_match_the_location_kind(kind, group, ok):
    if ok:
        assert rate_groups.normalize(kind, group) == group.upper().replace(" ", "")
    else:
        with pytest.raises(ValueError):
            rate_groups.normalize(kind, group)


# -- the engineer enters a location's rate group (API) ------------------------------------------------------------
from test_network import LINE, sid  # noqa: E402,F401


def test_the_engineer_enters_a_rate_group_per_segment_intersection_and_ramp(client, sid):  # noqa: F811
    net = client.put(f"/api/studies/{sid}/corridor", json={"line": LINE}).json()
    seg, it = net["segments"][0]["id"], net["intersections"][0]["id"]
    assert net["segments"][0]["rate_group"] is None and net["ramp_rate_groups"] == {}
    net = client.put(f"/api/studies/{sid}/rate-groups/segment/{seg}", json={"rate_group": "h 07"}).json()
    assert net["segments"][0]["rate_group"] == "H07"
    net = client.put(f"/api/studies/{sid}/rate-groups/intersection/{it}", json={"rate_group": "I14"}).json()
    assert net["intersections"][0]["rate_group"] == "I14"
    net = client.put(f"/api/studies/{sid}/rate-groups/ramp/7-LA-405-13.42", json={"rate_group": "R10"}).json()
    assert net["ramp_rate_groups"] == {"7-LA-405-13.42": "R10"}

    r = client.put(f"/api/studies/{sid}/rate-groups/segment/{seg}", json={"rate_group": "I14"})
    assert r.status_code in (400, 422) and "segment rate group" in r.text
    net = client.put(f"/api/studies/{sid}/rate-groups/segment/{seg}", json={"rate_group": None}).json()
    assert net["segments"][0]["rate_group"] is None

    # a redrawn corridor has new segments and intersections: their groups go; a Caltrans ramp's stays
    net = client.put(f"/api/studies/{sid}/corridor", json={"line": LINE}).json()
    assert net["intersections"][0]["rate_group"] is None and net["ramp_rate_groups"] == {"7-LA-405-13.42": "R10"}


def test_the_rate_group_list_for_the_picker(client):
    rows = client.get("/api/reference/rate-groups").json()
    assert len(rows["groups"]) == 178 and rows["source"].startswith("Caltrans, 2024 Crash Data")
    h03 = next(g for g in rows["groups"] if g["group"] == "H03")
    assert h03 == {"group": "H03", "kind": "highway", "label": "Conventional 2 lanes or less, roll, design speed <=55, rural",
                   "base_rate": 1.28, "adt_factor": 0.188, "adt_op": "/", "pct_fatal": 2.3, "pct_fi": 45.9,
                   "printed_page": 83}
