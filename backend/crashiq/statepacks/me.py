"""Maine: MaineDOT's open crash layer (sources/me_mainedot.py). Research: research_notes/me-2026-11-08/."""

from crashiq.packs import REF, StatePack


def _fetch(box, county_fips, years, cache_dir):
    from crashiq.sources import me_mainedot
    return me_mainedot.fetch_contract(box, county_fips, years, cache_dir)


PACK = StatePack(
    code="ME", name="Maine", fips="23", status="active",
    source="Crash data: MaineDOT Crash Locations, 10 years (MaineDOT open data on ArcGIS Online, the Maine Public Crash "
           "Query Tool's data; no open licence, MEGIS disclaimer).",
    source_short="MaineDOT crash data", bounds=(42.9, -71.1, 47.5, -66.9), first_year=2016,
    methods=REF / "methods_me.json", fetch=_fetch, county_boxes=REF / "county_boxes_me.json",
    # the item's licence text, quoted (research_notes/me-2026-11-08/me-import.md § Licence)
    legal=("MaineDOT crash data (MEGIS): \"Users must assume responsibility in determining the usability of this data "
           "for their purposes.\""),
    data_notes=("MaineDOT's public crash layer gives each crash's point and route code but no street names, cross "
                "street, drivers or vehicles: crashes are placed by MaineDOT's point alone, and road-user movements "
                "and collision diagrams are empty.",
                "Only crashes on Maine public roads are included; MaineDOT leaves out parking lots, driveways and "
                "private roads.",
                "MaineDOT's crash types 'Rear End / Sideswipe', 'Head-on / Sideswipe' and 'Intersection Movement' "
                "each merge CCRS types, so they keep Maine's words.",
                "Only Interstate crashes count as freeway crashes (the layer has no road class).",
                "Primary collision factor, DUI and speed rows are blank: CrashIQ doesn't map MaineDOT's driver "
                "actions yet."))
