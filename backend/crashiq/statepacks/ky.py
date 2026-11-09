"""Kentucky state pack (#19 plug-in): Kentucky State Police's public Collision Analysis site (KyOPS reports), placed
by GPS; severity is fatal / injury / no injury only."""

from crashiq.packs import REF, StatePack


def _fetch(box, county_fips, years, cache_dir):
    from crashiq.sources import ky_ksp
    return ky_ksp.fetch_contract(box, county_fips, years, cache_dir)


PACK = StatePack(
    code="KY", name="Kentucky", fips="21", status="active",
    source="Crash data: Kentucky State Police Collision Analysis for the Public (KyOPS police reports; public, no "
           "published reuse licence, no warranty).",
    source_short="KSP collision search", bounds=(36.4, -89.6, 39.2, -81.9), first_year=2015,
    methods=REF / "methods_ky.json", fetch=_fetch, county_boxes=REF / "county_boxes_ky.json",
    # the site's own notice, quoted (research_notes/ky-2026-11-08/ky-import.md § Licence)
    legal=("Kentucky State Police: \"no warranty, either expressed or implied, is given to the accuracy, "
           "completeness, reliability, or suitability for any particular purpose\" of the collision data."),
    severity_note=("Kentucky's public crash search doesn't report injury levels: a crash is fatal, injury or no "
                   "injury. KSI here is fatal crashes only, and there is no A/B/C split; injury crashes are counted "
                   "as 'injury, level not reported' (U)."),
    data_notes=("KSP's public search has no driver, vehicle or person records: road-user movements, collision "
                "diagrams, motorcycle and truck flags are empty, and pedestrian and bicycle crashes are found only "
                "from KSP's direction-of-analysis code.",
                "Crashes are read by their GPS point; the officer's road and cross street are kept for the "
                "not-on-the-corridor-street check, but the road name has no suffix (PRESTON for Preston Hwy).",
                "Weather, light and road surface are KSP's words; primary collision factor, DUI and speed rows are "
                "blank: the public rows have no violation codes.",
                "Freeway crashes are those on an interstate or a 9000-series state parkway (KYTC road number).",
                "KyOPS is updated daily, so a recent year keeps growing for months; KYTC's annual analysis freezes "
                "its own extract once a year."))
