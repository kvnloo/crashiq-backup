"""Pennsylvania: PennDOT public crash data, statewide (sources/pa_penndot.py)."""

from crashiq.packs import REF, StatePack


def _fetch(box, county_fips, years, cache_dir):
    from crashiq.sources import pa_penndot
    return pa_penndot.fetch_contract(box, county_fips, years, cache_dir)


PACK = StatePack(
    code="PA", name="Pennsylvania", fips="42", status="active",
    source="Crash data: PennDOT public crash data (PennDOT GIS Open Data, Crash Data Download; police reports of "
           "reportable crashes; no published reuse licence).",
    source_short="PennDOT crash data", bounds=(39.7, -80.6, 42.3, -74.6), first_year=2006,
    methods=REF / "methods_pa.json", fetch=_fetch, county_boxes=REF / "county_boxes_pa.json",
    final_lag_months=6,                          # PennDOT posts a year in June of the next year (2025 on 2026-06-05)
    legal=("PennDOT crash data: \"Data that is protected due to containing Personally Identifiable Information, or "
           "that could be used to infer information about persons involved in a crash are not included in the "
           "public dataset.\" (Crash Data Dictionary, 06-26). Safety studies: 75 Pa.C.S. 3754 and 23 U.S.C. 407."),
    data_notes=("PennDOT's public files give each crash's month, day of week and hour but not the day: crash lists "
                "show no date.",
                "PennDOT's 'injury, unknown severity' (about 8% of crashes) and 'unknown if injured' (about 3%) are "
                "counted as injury, level not reported (U), as PennDOT's Crash Facts counts them among injury "
                "crashes; U crashes are not priced (PennDOT prices them at the C cost).",
                "CrashIQ doesn't read PennDOT's vehicle and person tables yet: road-user movements and collision "
                "diagrams are empty.",
                "Primary collision factor, DUI and speed rows are blank: CrashIQ doesn't map PennDOT's flags to "
                "them yet."),
)
