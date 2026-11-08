"""Minnesota: DPS MNCrash public crash portal, statewide, by GPS (research_notes/mn-2026-11-08)."""

from crashiq.packs import REF, StatePack


def _fetch(box, county_fips, years, cache_dir):
    from crashiq.sources import mn_mncrash
    return mn_mncrash.fetch_contract(box, county_fips, years, cache_dir)


PACK = StatePack(
    code="MN", name="Minnesota", fips="27", status="active",
    source="Crash data: Minnesota Department of Public Safety, MNCrash public crash data portal (no published licence).",
    source_short="MNCrash", bounds=(43.4, -97.3, 49.5, -89.4), first_year=2016,
    methods=REF / "methods_mn.json", fetch=_fetch, county_boxes=REF / "county_boxes_mn.json",
    legal=("Crash data: Minnesota Department of Public Safety (MNCrash public portal), as published; no licence or "
           "warranty is stated. See 23 USC 407."),
    data_notes=("MNCrash's public export has one row per crash and no driver, vehicle or person records: road-user "
                "movements and collision diagrams are empty, and pedestrian, bicycle, motorcycle and truck crashes "
                "can't be picked out (those counts read zero).",
                "Collision type, lighting, weather and road surface aren't in the public export; those rows are blank.",
                "About 3% of crashes have no severity in MNCrash: CrashIQ counts them fatal if someone died, injury "
                "of unknown level (U, unpriced) if someone was hurt, otherwise property damage.",
                "Only Interstate crashes count as freeway crashes: on Minnesota's other freeways, check ramp and "
                "mainline crashes by hand."))
