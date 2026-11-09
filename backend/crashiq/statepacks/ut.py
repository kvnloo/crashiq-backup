"""Utah state pack (#19 plug-in): UDOT's public Utah Crash Locations service (2019 on, nightly), by GPS."""

from crashiq.packs import REF, StatePack


def _fetch(box, county_fips, years, cache_dir):
    from crashiq.sources import ut_udot
    return ut_udot.fetch_contract(box, county_fips, years, cache_dir)


PACK = StatePack(
    code="UT", name="Utah", fips="49", status="active",
    source="Crash data: UDOT Utah Crash Locations (UPlan open data, refreshed nightly; informational use, field-verify, "
           "23 USC 407; no published reuse licence).",
    source_short="UDOT Utah Crash Locations", bounds=(36.9, -114.1, 42.1, -108.9), first_year=2019,
    methods=REF / "methods_ut.json", fetch=_fetch, county_boxes=REF / "county_boxes_ut.json",
    # the item's terms and description, quoted (research_notes/ut-2026-11-08/ut-import.md § Licence)
    legal=("UDOT: \"All data presented here is for informational purposes only and must be field verified prior to "
           "being used on a project.\" \"This data is protected under 23 USC 407.\""),
    data_notes=("UDOT's public layer has one row per crash and no driver, vehicle or person records: road-user "
                "movements and collision diagrams are empty; pedestrian, bicycle, motorcycle and commercial-vehicle "
                "crashes come from UDOT's yes/no flags.",
                "Crashes are placed by UDOT's GPS point (every row has one). About two in three give a house address "
                "instead of a cross street, so a crash on a side street inside the buffer can't always be told apart: "
                "check such crashes by hand.",
                "The newest two years are preliminary in UDOT's own words and change as reports are reviewed.",
                "Primary collision factor rows are blank: the layer has DUI and speed flags but no violation codes.",
                "Crashes count as freeway crashes on Interstates and other freeways and expressways (UDOT's "
                "functional class)."))
