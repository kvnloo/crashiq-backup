"""Iowa: Iowa DOT's open crash layers (ICAT's data), statewide, CC BY 4.0 (research_notes/ia-2026-11-08)."""

from crashiq.packs import REF, StatePack


def _fetch(box, county_fips, years, cache_dir):
    from crashiq.sources import ia_dot
    return ia_dot.fetch_contract(box, county_fips, years, cache_dir)


PACK = StatePack(
    code="IA", name="Iowa", fips="19", status="active",
    source="Crash data: Iowa Department of Transportation, Crash Data (Iowa DOT open data, CC BY 4.0).",
    source_short="Iowa DOT crash data", bounds=(40.3, -96.7, 43.6, -90.1), first_year=2015,   # prior 10 years + current
    methods=REF / "methods_ia.json", fetch=_fetch, county_boxes=REF / "county_boxes_ia.json",
    # CC BY 4.0 credit, and Iowa DOT's GIS Data Terms of Use (effective 2026-06-19): "provided 'as is'"
    legal=("Crash data: Iowa Department of Transportation (CC BY 4.0). Iowa DOT provides the data \"as is\" and does "
           "not guarantee accuracy; see 23 USC 407."),
    data_notes=("Iowa DOT's open crash layer has no driver or party records: road-user movements and collision diagrams "
                "are empty. Pedestrian and bicycle crashes are flagged from Iowa DOT's person layer, which lacks some "
                "crashes, so those counts are a floor.",
                "Crashes with an injury of unknown level are counted as injury, level not reported (U) and are not "
                "priced; Iowa DOT's own worksheet prices them with possible injuries (C).",
                "Only Interstate crashes count as freeway crashes: on Iowa's other freeways and expressways, check "
                "ramp and mainline crashes by hand.",
                "Primary collision factor, DUI and speed rows are blank: CrashIQ doesn't map Iowa DOT's major-cause "
                "codes yet."))
