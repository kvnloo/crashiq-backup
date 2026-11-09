"""Ohio state pack (#19 plug-in): ODOT's public TIMS crash layers (OH-1 reports from ODPS), placed by GPS, KABCO."""

from crashiq.packs import REF, StatePack


def _fetch(box, county_fips, years, cache_dir):
    from crashiq.sources import oh_tims
    return oh_tims.fetch_contract(box, county_fips, years, cache_dir)


PACK = StatePack(
    code="OH", name="Ohio", fips="39", status="active",
    source="Crash data: ODOT TIMS public crash layers (OH-1 reports compiled by ODPS; public domain per ODOT TIMS).",
    source_short="ODOT TIMS", bounds=(38.3, -84.9, 42.4, -80.4), first_year=2021,   # TIMS serves 2021-2025
    methods=REF / "methods_oh.json", fetch=_fetch, county_boxes=REF / "county_boxes_oh.json",
    # ODOT's 2025 layer matched ODOT's own 2025 totals by May 2026 (CrashCostsUpdate.pdf, updated 5/5/26)
    final_lag_months=10,
    # TIMS's disclaimer, quoted (research_notes/oh-2026-11-08/oh-import.md § Licence)
    legal=("ODOT TIMS: \"While every effort is made to assure the data is accurate and current, it must be accepted and "
           "used by the recipient with the understanding that no warranties, expressed or implied, concerning the "
           "accuracy, reliability or suitability of this data have been made.\" Crash location data is owned and "
           "provided to ODOT by the Ohio Department of Public Safety."),
    data_notes=("Ohio's public crash layer gives each crash's month, weekday and hour but not the day of the month, "
                "so crash dates are blank; the year and month are kept.",
                "It has no street names, no driver, vehicle or person records and no people counts: crashes are placed "
                "by GPS only, people killed and injured aren't counted, road-user movements and collision diagrams "
                "are empty, and motorcycle and truck flags are blank.",
                "Pedestrian and bicycle crashes are those ODOT types as Pedestrian or Pedalcycles (first harmful "
                "event), so a crash that hit a pedestrian after another vehicle is missed.",
                "Light, weather and road surface are blank; primary collision factor, DUI and speed rows are blank: "
                "the public layer has no violation codes.",
                "Freeway crashes are those on functional class 1-2 roads (interstates, other freeways and "
                "expressways)."))
