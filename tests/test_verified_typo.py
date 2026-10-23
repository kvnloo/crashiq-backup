"""#233 tier verified_typo (user 2026-10-22, "1 yes"; gate off until the Tester measures it and the user approves):
a misspelled name is corrected only when it isn't a guess."""

from crashiq import locate, placement
from crashiq.osm import Network

LINE = [(34.0, -118.011), (34.0, -117.997)]


def _raw() -> dict:
    """Main Street east-west; Magnolia, Westmont, Westmore, 16th, Pine and Oak cross it; Oak Lane meets it twice."""
    els, main, x = [], [], -118.0100
    for i, nm in enumerate(["Magnolia Avenue", "Westmont Drive", "Westmore Drive", "16th Street", "Pine Street",
                            "Oak Lane"]):
        nid = 100 + i
        els += [{"type": "node", "id": nid, "lat": 34.0, "lon": x + i * 0.002},
                {"type": "node", "id": nid + 50, "lat": 34.001, "lon": x + i * 0.002},
                {"type": "way", "id": 300 + i, "nodes": [nid, nid + 50], "tags": {"name": nm}}]
        main.append(nid)
    els += [{"type": "node", "id": 200, "lat": 34.0, "lon": x + 6 * 0.002},
            {"type": "way", "id": 399, "nodes": [155, 200], "tags": {"name": "Oak Lane"}}]
    els.append({"type": "way", "id": 400, "nodes": main + [200], "tags": {"name": "Main Street"}})
    return {"elements": els}


RAW = _raw()
NET = Network(RAW)


def crash(p, s, lat=None, lon=None):
    return {"crash_id": "x", "primary_road": p, "secondary_road": s, "offset_ft": None, "offset_dir": None,
            "lat": lat, "lon": lon, "location_source": "unmatched"}


def test_a_one_off_typo_with_one_possible_street_is_corrected():
    p = locate.place(NET, crash("MAIN ST", "MAONOLIA AV"))
    assert p.tier == "verified_typo" and p.node == 100 and "Magnolia" in p.note


def test_a_rival_street_as_close_or_one_edit_further_means_no_correction():
    assert locate.place(NET, crash("MAIN ST", "WESTMORT DR")).tier != "verified_typo"   # Westmont 1, Westmore 1
    assert locate.place(NET, crash("MAIN ST", "WESTMOMT DR")).tier != "verified_typo"   # Westmont 1, Westmore 2


def test_numbers_are_never_corrected():
    assert locate.place(NET, crash("MAIN ST", "15TH ST")).tier != "verified_typo"


def test_short_names_allow_one_edit_only_and_tiny_ones_none():
    assert locate.place(NET, crash("MAIN ST", "PINR ST")).tier == "verified_typo"           # 4 letters, 1 edit
    assert locate.place(NET, crash("MAIN ST", "PIRR ST")).tier != "verified_typo"           # 2 edits
    assert locate.place(NET, crash("MAIN ST", "PIN ST")).tier != "verified_typo"            # 3 letters: never


def test_a_corrected_pair_that_meets_twice_is_not_placed():
    assert locate.place(NET, crash("MAIN ST", "OAKK LN")).tier != "verified_typo"


def test_police_gps_must_agree_where_it_exists():
    at = NET.coord[100]
    assert locate.place(NET, crash("MAIN ST", "MAONOLIA AV", at[0] + 0.0003, at[1])).tier == "verified_typo"
    assert locate.place(NET, crash("MAIN ST", "MAONOLIA AV", at[0] + 0.01, at[1])).tier != "verified_typo"


def test_exact_names_are_untouched():
    assert locate.place(NET, crash("MAIN ST", "MAGNOLIA AV")).tier == "exact"
    assert locate.place(NET, crash("MAIN ST", "WESTMONT DR")).tier == "exact"


def test_off_by_default_a_one_click_suggestion():
    assert "verified_typo" not in locate.configured_tiers()
    r = {"cleaning": {}, "crashes": [crash("MAIN ST", "MAONOLIA AV")]}
    placement.place_unmatched(None, {"line": LINE}, r, raw=RAW)
    c = r["crashes"][0]
    assert c["location_source"] == "unmatched" and c["suggestion"]["tier"] == "verified_typo"
    r = {"cleaning": {}, "crashes": [crash("MAIN ST", "MAONOLIA AV")]}
    placement.place_unmatched(None, {"line": LINE}, r, raw=RAW,
                              gate=locate.Gate(auto_tiers=frozenset({"exact", "unique_pair", "verified_typo"})))
    assert r["crashes"][0]["location_source"] == "verified_typo"
