"""Colorado state pack (#19 plug-in): CDOT's Statewide Crash Data Listing (yearly Excel files, 2021 on), by GPS with
the reported street pair."""

from crashiq.packs import REF, StatePack


def _fetch(box, county_fips, years, cache_dir):
    from crashiq.sources import co_cdot
    return co_cdot.fetch_contract(box, county_fips, years, cache_dir)


PACK = StatePack(
    code="CO", name="Colorado", fips="08", status="active",
    source="Crash data: CDOT Statewide Crash Data Listing (codot.gov, from DOR's DRIVES crash records; protected under "
           "23 USC 407, no published reuse licence).",
    source_short="CDOT crash listing", bounds=(36.9, -109.1, 41.1, -102.0), first_year=2021,
    methods=REF / "methods_co.json", fetch=_fetch, county_boxes=REF / "county_boxes_co.json",
    # CDOT called the 2025 listing "considered complete" on 2026-07-23, about 7 months after the year ended; 10 months
    # makes the default window 2021-2025, inside first_year (study.default_window doesn't clamp, shared-fixes.md #3)
    final_lag_months=10,
    # CDOT's crash-data page, quoted (research_notes/co-2026-11-08/co-import.md § Licence)
    legal=("CDOT: \"All crash data listings, reports and dashboards are protected under 23 U.S.C. Section 407.\" "
           "\"All crash data from 2021 to 2026 is subject to updates and revisions.\""),
    data_notes=("CrashIQ reads CDOT's listings from 2021 on; 2007-2020 use another layout and aren't read yet. Each "
                "year's file is about 50 MB, so the first study in Colorado waits a few minutes per year while it "
                "downloads; later studies read the saved copy. If CDOT's download site refuses a year, that year is "
                "reported missing, never counted in part.",
                "The listing has no person or vehicle tables, only the first two traffic units: road-user movements "
                "and collision diagrams are empty; pedestrian, bicycle, motorcycle and truck crashes come from those "
                "two units and CDOT's crash type.",
                "Crash costs aren't shown yet: CDOT's 2025 costs are cited but not checked against a saved copy of "
                "the report.",
                "Primary collision factor rows are blank: CrashIQ doesn't map CDOT's human contributing factors yet.",
                "Crashes count as freeway crashes only on Interstate highways (CDOT system code): check freeway-built "
                "state highways (US 36, C-470, E-470) by hand."))
