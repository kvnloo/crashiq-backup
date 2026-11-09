"""South Dakota: DPS Office of Accident Records raw crash data (SDARS yearly files, 2011-2025, open, no login)."""

from crashiq.packs import REF, StatePack


def _fetch(box, county_fips, years, cache_dir):
    from crashiq.sources import sd_dps
    return sd_dps.fetch_contract(box, county_fips, years, cache_dir)


PACK = StatePack(
    code="SD", name="South Dakota", fips="46", status="active",
    source="Crash data: South Dakota Department of Public Safety, Office of Accident Records, raw crash data "
           "(safesd.gov yearly files; no published reuse licence).",
    source_short="SD DPS Accident Records", bounds=(42.4, -104.1, 46.0, -96.4), first_year=2011,
    methods=REF / "methods_sd.json", fetch=_fetch, county_boxes=REF / "county_boxes_sd.json",
    # safesd.gov, quoted (research_notes/sd-2026-11-08/sd-import.md § licence)
    legal=("SD DPS Office of Accident Records: \"Vehicle crash reports are covered by South Dakota open records "
           "statute\"; raw crash data downloaded from safesd.gov. CrashIQ reads no names, addresses or other personal "
           "details from it."),
    data_notes=("South Dakota's files give one most-harmful-event and the manner of collision, not CCRS's crash type: "
                "single-vehicle crashes show their first harmful event (e.g. DITCH, OVERTURNED).",
                "Primary collision factor, DUI and speed rows are blank: CrashIQ doesn't map DPS's contributing "
                "circumstances or citations yet."))
