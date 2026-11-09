"""Nebraska: NDOT's NTIP crash map, statewide (sources/ne_ntip.py). reader_only until NDOT allows reuse."""

from crashiq.packs import REF, StatePack


def _fetch(box, county_fips, years, cache_dir):
    from crashiq.sources import ne_ntip
    return ne_ntip.fetch_contract(box, county_fips, years, cache_dir)


PACK = StatePack(
    code="NE", name="Nebraska", fips="31", status="reader_only",   # the portal's notice forbids redistribution
    source="Crash data: Nebraska Transportation Information Portal (NTIP) crash map, Nebraska Department of "
           "Transportation (ntip2021.nebraska.gov; police crash reports; marked confidential, 23 U.S.C. 407).",
    source_short="NDOT NTIP", bounds=(39.9, -104.1, 43.1, -95.3), first_year=2021,
    methods=REF / "methods_ne.json", fetch=_fetch, county_boxes=REF / "county_boxes_ne.json",
    final_lag_months=12,                         # not stated by NDOT; NTIP is a live query
    # the portal's notice, quoted (research_notes/ne-2026-11-08/ne-import.md §2)
    legal=("NDOT: \"The safety and crash data information contained in this document is confidential, protected "
           "and/or privileged information. Federal Law, 23 U.S.C. §407, prohibits the production of this document "
           "or its contents in discovery or its use in evidence in a State or Federal Court.\""),
    data_notes=("Nebraska's public crash map gives one row per crash: no people, vehicles, light, road surface or "
                "work zone, so people killed and injured aren't counted and road-user movements and collision "
                "diagrams are empty.",
                "Pedestrian, bicycle, motorcycle and freeway crashes come from the map's own filters; its pedestrian "
                "and bicycle filters look incomplete (Omaha 2024: 21 pedestrian and 3 bicycle crashes).",
                "Non-reportable crashes are left out, and the map starts in 2021."),
)
