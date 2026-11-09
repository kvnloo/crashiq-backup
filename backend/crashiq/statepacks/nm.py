"""New Mexico: Bernalillo County crashes (UNM/NMDOT data the City of Albuquerque publishes, 2020-2024, open, no login).
Statewide NMDOT crash data is by records request only, so this pack is reader_only (research_notes/nm-2026-11-08)."""

from crashiq.packs import REF, StatePack


def _fetch(box, county_fips, years, cache_dir):
    from crashiq.sources import nm_cabq
    return nm_cabq.fetch_contract(box, county_fips, years, cache_dir)


PACK = StatePack(
    code="NM", name="New Mexico", fips="35", status="reader_only",
    source="Crash data: NMDOT crash records compiled by UNM Geospatial and Population Studies, published by the City "
           "of Albuquerque (\"Crashes Five Year 2020 - 2024\", Bernalillo County only; provided as is).",
    source_short="UNM/NMDOT crashes (Bernalillo County)", bounds=(31.3, -109.05, 37.0, -103.0), first_year=2020,
    methods=REF / "methods_nm.json", fetch=_fetch, county_boxes=REF / "county_boxes_nm.json",
    # the layer's description, quoted, and the federal notice UNM cites (research_notes/nm-2026-11-08/nm-import.md)
    legal=("City of Albuquerque / UNM-GPS: \"All data is provided AS IS from UNM/NMDOT and has not been modified.\" "
           "Crash data compiled for highway safety purposes may be protected from discovery or admission as evidence "
           "under 23 U.S.C. 407."),
    data_notes=("Only Bernalillo County (Albuquerque) crashes from 2020 to 2024 are open; anywhere else in New Mexico "
                "the years show as missing, not as zero crashes.",
                "The data has no driver, vehicle or person records and no road surface: road-user tables and the "
                "surface row are empty, and primary collision factor, DUI and speed rows are blank.",
                "Severity comes from the crash's counts of people killed and class A, B and C injured."))
