"""New Jersey: NJDOT crash records (Crash, Occupant, Pedestrian and Vehicle tables, 2017-2023, open, no login)."""

from crashiq.packs import REF, StatePack


def _fetch(box, county_fips, years, cache_dir):
    from crashiq.sources import nj_njdot
    return nj_njdot.fetch_contract(box, county_fips, years, cache_dir)


PACK = StatePack(
    code="NJ", name="New Jersey", fips="34", status="active",
    source="Crash data: New Jersey Department of Transportation, Bureau of Transportation Data and Safety, crash "
           "records from police NJTR-1 reports (dot.nj.gov crash tables; no published reuse licence).",
    source_short="NJDOT crash records", bounds=(38.9, -75.6, 41.4, -73.9), first_year=2017,
    methods=REF / "methods_nj.json", fetch=_fetch, county_boxes=REF / "county_boxes_nj.json",
    # NJDOT crash-records pages, quoted (research_notes/nj-2026-11-08/nj-import.md § licence)
    legal=("NJDOT: \"By using this site, you agree to abide by the NJDOT Legal Notice, the NJDOT Privacy Notice, "
           "23 USC §407 and all other applicable statutes, rules, and regulations.\" CrashIQ reads no names, addresses "
           "or birth dates from NJDOT's tables."),
    data_notes=("New Jersey's tables give a map point for only 26-38% of 2017-2022 crashes and 60% of 2023's (Essex "
                "2023: 40%); the rest are placed from the road and cross-street names, and a crash on a county route "
                "numbered 600 or up with no street name stays unplaced (the Census map doesn't carry those numbers).",
                "NJDOT posts years 2017-2023 in this format; newer years are in its Crash Data Portal only.",
                "Primary collision factor, DUI and speed rows are blank: CrashIQ doesn't map NJDOT's contributing "
                "circumstances or alcohol flag yet."))
