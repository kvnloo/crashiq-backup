"""Idaho state pack (#19 plug-in): ITD's open CrashLayers service (Office of Highway Safety crash database), by GPS."""

from crashiq.packs import REF, StatePack


def _fetch(box, county_fips, years, cache_dir):
    from crashiq.sources import id_itd
    return id_itd.fetch_contract(box, county_fips, years, cache_dir)


PACK = StatePack(
    code="ID", name="Idaho", fips="16", status="active",
    source="Crash data: Idaho Transportation Department, Office of Highway Safety crash layers (ITD GIS open data; "
           "provided as is, no published reuse licence).",
    source_short="ITD crash layers", bounds=(41.9, -117.3, 49.1, -111.0), first_year=2008,
    methods=REF / "methods_id.json", fetch=_fetch, county_boxes=REF / "county_boxes_id.json",
    # ITD's open service runs about three years behind (2026-11: 2022 in full, 2023 to October only, no 2024-2025);
    # 46 months keeps the default window on full years. shortcut: tied to ITD's lag, re-check when ITD posts 2023
    final_lag_months=46,
    # ITD's spatial data disclaimer, quoted (research_notes/id-2026-11-08/id-import.md § Licence)
    legal=("ITD: \"The Idaho Transportation Department (ITD) provides this geographic data and any associated metadata "
           "'as is' without warranty of any kind, including but not limited to its completeness, fitness for a "
           "particular use, or accuracy of its content, positional or otherwise. It is the sole responsibility of the "
           "user to determine the usability of the data for their purposes.\""),
    data_notes=("ITD's open crash service runs about three years behind: 2022 is its newest full year, 2023 is loaded "
                "only to October and 2024-2025 aren't there. A part-loaded year is treated as missing, never counted.",
                "The layer has no street names, so each crash is placed by its GPS alone, and a crash on a parallel "
                "street or in a parking lot inside the buffer can't be told apart: check such crashes by hand.",
                "There are no driver or person records with their own injury level: road-user movements and "
                "collision diagrams are empty; the collision type is the first unit's most harmful event.",
                "Lighting, weather and road surface aren't in the open layers; those rows are blank.",
                "Crashes count as freeway crashes only on Interstate routes (ITD route system IN): check freeway-built "
                "US or state highways by hand."))
