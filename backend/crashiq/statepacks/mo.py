"""Missouri state pack (#19 plug-in): the Missouri State Highway Patrol's public STARS crash layer (every Missouri
Uniform Crash Report, statewide), GPS-placed, with the officer's road pair and offset for crashes with no point;
severity K / A / U (minor injury = B and C together) / O."""

from crashiq.packs import REF, StatePack


def _fetch(box, county_fips, years, cache_dir):
    from crashiq.sources import mo_mshp
    return mo_mshp.fetch_contract(box, county_fips, years, cache_dir)


PACK = StatePack(
    code="MO", name="Missouri", fips="29", status="active",
    source="Crash data: Missouri State Highway Patrol, Statewide Traffic Accident Records System (STARS), through "
           "MSHP's public crash map layer (no published reuse licence).",
    source_short="MSHP STARS", bounds=(35.9, -95.8, 40.7, -89.0), first_year=2013,
    methods=REF / "methods_mo.json", fetch=_fetch, county_boxes=REF / "county_boxes_mo.json",
    legal=("Missouri crash data from the Missouri State Highway Patrol's public STARS crash layer; MSHP publishes no "
           "reuse licence (23 USC 407 applies to safety studies)."),
    data_notes=("MSHP's public layer keeps two injury counts: disabling (suspected serious, A) and minor. Minor covers "
                "evident and possible injuries (MoDOT: \"Minor Injury: B & C\"), so it is counted as injury, level not "
                "reported (U): there is no B/C split.",
                "Property-damage crashes are in the layer through 2023; 2024 has about a quarter of the usual number "
                "and 2025 on has none yet (counted 2026-11-08), so recent years undercount PDO crashes.",
                "The layer has no driver, vehicle or person records: road-user movements and collision diagrams are "
                "empty; crash type is MSHP's first-harmful-event type, and pedestrian and bicycle crashes are found "
                "from it.",
                "Freeway crashes are those MSHP files on an interstate (IS); a US or state route built as a freeway "
                "(US 71 in Kansas City) isn't flagged: check such corridors by hand.",
                "Weather and road surface are not in the layer; primary collision factor rows are blank; DUI and "
                "speeding are MSHP's driver flags.",
                "Crashes with no GPS point (about 5%) are placed from the officer's road, cross road and distance."))
