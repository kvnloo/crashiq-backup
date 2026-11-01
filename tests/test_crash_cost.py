"""Crash cost by location from Caltrans LRSM v1.8 (#273; user decisions 2026-10-25 and 2026-11-01)."""

from crashiq import crash_cost
from crashiq.settings import ROOT


def test_the_cost_table_is_the_lrsm_one_with_its_source():
    t = crash_cost.table()
    assert t == {("KA", "signalized_intersection"): 2379000, ("KA", "non_signalized_intersection"): 3784000,
                 ("KA", "roadway"): 3276000, ("B", "any"): 213000, ("C", "any"): 121000, ("O", "any"): 20000}
    head = (ROOT / "data" / "reference" / "crash_costs_ca.csv").read_text().splitlines()[:2]
    assert "Version 1.8, May 2026" in head[0] and "Appendix D" in head[0] and "page 100" in head[0]
    assert head[1].startswith("# https://dot.ca.gov/") and "lrsm2026final.pdf" in head[1]
    md = (ROOT / "data" / "reference" / "crash_costs_ca.md").read_text()
    assert "SHA-256" in md and "2026 Dollars" in md


SIX = [{"severity": s} for s in "KABCUO"]


def test_six_crashes_hand_computed_by_location_type():
    # K + A at the KA price, then B 213,000 + C 121,000 + U (priced at C) 121,000 + O 20,000 = 475,000
    rest = 213000 + 121000 + 121000 + 20000
    assert crash_cost.location_cost(SIX, "intersection", "signal") == \
        {"crash_cost": 2 * 2379000 + rest, "cost_control_unknown": False}              # 5,233,000
    assert crash_cost.location_cost(SIX, "intersection", "stop")["crash_cost"] == 2 * 3784000 + rest   # 8,043,000
    assert crash_cost.location_cost(SIX, "segment", None)["crash_cost"] == 2 * 3276000 + rest          # 7,027,000
    for ctrl in ("yield", "roundabout"):                                              # non-signalized (PM, 2026-11-01)
        assert crash_cost.location_cost(SIX, "intersection", ctrl)["crash_cost"] == 2 * 3784000 + rest


def test_u_is_priced_at_c_and_unknown_control_at_the_signalized_price():
    assert crash_cost.cost("U", "roadway") == crash_cost.cost("C", "roadway") == 121000
    got = crash_cost.location_cost(SIX, "intersection", "unknown")
    assert got == {"crash_cost": 2 * 2379000 + 475000, "cost_control_unknown": True}
    # without a KA crash the control doesn't matter, so it isn't flagged
    assert crash_cost.location_cost([{"severity": "O"}], "intersection", None)["cost_control_unknown"] is False


def test_t2_carries_the_cost_of_each_location_and_its_source():
    from crashiq import profile
    from test_profile import golden
    study, n, pull, asg = golden()
    p = profile.build(study, n, pull, asg)
    t2 = next(t for t in p["tables"] if t["id"] == "T2")
    by = {c["crash_id"]: c for c in pull["crashes"]}
    ints = {i["id"]: i for i in n["intersections"]}
    for r in t2["rows"]:
        cs = [by[a["crash_id"]] for a in asg["assignments"] if a["location_id"] == r["key"]]
        kind, ctrl = r["values"]["kind"], ints.get(r["key"], {}).get("control")
        lt, _ = crash_cost.location_type(kind, ctrl)
        assert r["values"]["crash_cost"] == sum(crash_cost.cost(c["severity"], lt) for c in cs), r["key"]
    assert "crash_cost" in [c["key"] for c in t2["columns"]] and "Safety Manual v1.8" in t2["source_note"]
