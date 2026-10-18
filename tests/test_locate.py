"""Locator on a tiny synthetic network: tiers, offset along the road, ambiguity, addresses, Jev seam."""
from crashiq import locate
from crashiq.osm import Network, metres

# Main St runs east-west through A(1)-B(2)-C(3); Oakland Ave runs north-south through B(2) and D(4).
# Elm St crosses Main twice (at 1 and 3, ~180 m apart) to make an ambiguous pair.
NET = Network({"elements": [
    {"type": "node", "id": 1, "lat": 37.7700, "lon": -122.4210},
    {"type": "node", "id": 2, "lat": 37.7700, "lon": -122.4200},
    {"type": "node", "id": 3, "lat": 37.7700, "lon": -122.4190},
    {"type": "node", "id": 4, "lat": 37.7710, "lon": -122.4200},
    {"type": "node", "id": 5, "lat": 37.7690, "lon": -122.4200},
    {"type": "node", "id": 6, "lat": 37.7690, "lon": -122.4210},
    {"type": "node", "id": 7, "lat": 37.7690, "lon": -122.4190},
    {"type": "way", "id": 10, "nodes": [1, 2, 3], "tags": {"name": "Main Street"}},
    {"type": "way", "id": 11, "nodes": [5, 2, 4], "tags": {"name": "Oakland Avenue"}},
    {"type": "way", "id": 12, "nodes": [1, 6, 7, 3], "tags": {"name": "Elm Street"}},
]})


def crash(p, s, ft=None, d=None):
    return {"primary_road": p, "secondary_road": s, "offset_ft": ft, "offset_dir": d}


def test_exact_match_at_intersection():
    p = locate.place(NET, crash("MAIN ST", "OAKLAND AV"))
    assert p.tier == "exact" and p.node == 2


def test_offset_moves_along_primary_road_toward_reported_direction():
    p = locate.place(NET, crash("MAIN ST", "OAKLAND AV", 100, "E"))
    assert abs(metres((p.lat, p.lon), NET.coord[2]) - 30.48) < 0.5
    assert p.lon > NET.coord[2][1]  # moved east


def test_wrong_suffix_is_relaxed_not_exact():
    assert locate.place(NET, crash("MAIN AVE", "OAKLAND AV")).tier == "relaxed"


def test_typo_goes_to_fuzzy():
    assert locate.place(NET, crash("MAIN ST", "OAKLANDD AVE")).tier == "fuzzy"


def test_streets_meeting_twice_go_to_review():
    p = locate.place(NET, crash("MAIN ST", "ELM ST"))
    assert p.tier == "review" and "more than one place" in p.note


def test_missing_name_goes_to_review():
    assert locate.place(NET, crash("MAIN ST", None)).tier == "review"


def test_address_tier_interpolates_house_numbers():
    idx = locate.AddressIndex([("Main Street", "100", 37.77, -122.4210), ("Main Street", "200", 37.77, -122.4190)])
    p = locate.place(NET, crash("MAIN ST", "MAIN ST 150"), addresses=idx)
    assert p.tier == "address" and abs(p.lon - (-122.4200)) < 1e-6


class FakePicker:
    def __init__(self, answer):
        self.answer = answer

    def pick(self, city, primary, secondary, labels):
        return (labels[0] if self.answer == "first" else self.answer), 0.9, 0.05


def test_jev_can_only_choose_a_code_generated_candidate():
    c = crash("MAIN ST", "OAKLANDD AVE")
    assert locate.place_with_jev(NET, c, FakePicker("first"), "Test").tier == "jev"
    invented = locate.place_with_jev(NET, c, FakePicker("Pine St & 9th Ave"), "Test")
    assert invented.tier == "review" and invented.lat is None


def test_short_names_are_not_fuzzy_matched():
    # "OAKK" vs "OAK" style typos on short names are too risky to auto-match; they go to review.
    net = Network({"elements": [
        {"type": "node", "id": 1, "lat": 37.77, "lon": -122.42}, {"type": "node", "id": 2, "lat": 37.771, "lon": -122.42},
        {"type": "node", "id": 3, "lat": 37.77, "lon": -122.421},
        {"type": "way", "id": 1, "nodes": [1, 2], "tags": {"name": "Oak Street"}},
        {"type": "way", "id": 2, "nodes": [3, 1], "tags": {"name": "Main Street"}}]})
    assert locate.place(net, crash("MAIN ST", "OAKK ST")).tier == "review"


def test_alias_file_is_applied(tmp_path):
    from crashiq.names import load_aliases
    f = tmp_path / "aliases.csv"
    f.write_text("raw,replacement\nPIONEER BLVD,MAIN ST\n")
    aliases = load_aliases(f)
    assert aliases == {"PIONEER BLVD": "MAIN ST"}
    assert locate.place(NET, crash("PIONEER BLVD", "OAKLAND AV"), aliases=aliases).tier == "exact"
    assert load_aliases(tmp_path / "missing.csv") == {}


def test_gate_defaults_jev_never_auto():
    g = locate.Gate()
    assert g.auto(locate.Placement("exact", 1, 1)) and not g.auto(locate.Placement("relaxed", 1, 1))
    assert not g.auto(locate.Placement("jev", 1, 1, p=0.99, p2=0.0))


def test_gate_jev_below_tau_or_margin_goes_to_review():
    g = locate.Gate(jev_tau=0.9, jev_margin=0.3)
    assert g.auto(locate.Placement("jev", 1, 1, p=0.95, p2=0.05))
    assert not g.auto(locate.Placement("jev", 1, 1, p=0.85, p2=0.05))   # below tau
    assert not g.auto(locate.Placement("jev", 1, 1, p=0.92, p2=0.70))   # below margin


def test_relaxed_keeps_suffix_before_dropping_it():
    # Long Beach, 2026-10-18: "ATLANTIC AV & ATLANTIC PL"; OSM calls the small street "North Atlantic Place".
    net = Network({"elements": [
        {"type": "node", "id": 1, "lat": 33.880, "lon": -118.186}, {"type": "node", "id": 2, "lat": 33.881, "lon": -118.186},
        {"type": "node", "id": 3, "lat": 33.880, "lon": -118.185}, {"type": "node", "id": 4, "lat": 33.870, "lon": -118.186},
        {"type": "node", "id": 5, "lat": 33.870, "lon": -118.185},
        {"type": "way", "id": 1, "nodes": [4, 1, 2], "tags": {"name": "Atlantic Avenue"}},
        {"type": "way", "id": 2, "nodes": [1, 3], "tags": {"name": "North Atlantic Place"}},
        {"type": "way", "id": 3, "nodes": [4, 5], "tags": {"name": "45th Street"}}]})
    p = locate.place(net, crash("ATLANTIC AV", "ATLANTIC PL"))
    assert p.tier == "relaxed" and p.node == 1
