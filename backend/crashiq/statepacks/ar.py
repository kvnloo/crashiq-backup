"""Arkansas state pack (#19 plug-in): ARDOT's ACAT crash layer (ASP eCrash reports, 2021-2025), placed by GPS."""

from crashiq.packs import REF, StatePack


def _fetch(box, county_fips, years, cache_dir):
    from crashiq.sources import ar_ardot
    return ar_ardot.fetch_contract(box, county_fips, years, cache_dir)


PACK = StatePack(
    code="AR", name="Arkansas", fips="05", status="active",
    source="Crash data: ARDOT Arkansas Crash Analytics Tool layer (Arkansas State Police eCrash reports, cleaned and "
           "located by ARDOT; public, no published reuse licence, not an official record).",
    source_short="ARDOT crash layer", bounds=(32.9, -94.7, 36.6, -89.6), first_year=2021,
    methods=REF / "methods_ar.json", fetch=_fetch, county_boxes=REF / "county_boxes_ar.json",
    # ARDOT posts a whole year at once (2025 through 12-31 by 2026-11) and keeps only five; at 18 months the default
    # window would start in 2020, before the layer's first year
    final_lag_months=10,
    # the layer's own notice, quoted (research_notes/ar-2026-11-08/ar-import.md § Licence)
    legal=("ARDOT: \"The data contained in the web-based dashboard is not an official record for crash statistics or "
           "what transpired in a crash… Under federal law, this information is not subject to discovery and cannot be "
           "admitted into evidence in any federal or state court proceeding or considered for other purposes in any "
           "action for damages that involves the sites mentioned in these records (see 23 USC, Section 409).\""),
    data_notes=("ARDOT's public crash layer covers the latest five years only (2021-2025 at the last check) and has no "
                "driver, vehicle or person records: road-user movements and collision diagrams are empty.",
                "The layer carries no street names CrashIQ can read (the road is coded inside ARDOT's road id), so each "
                "crash is placed by its GPS alone, and a crash in a parking lot or on a parallel street inside the "
                "buffer can't be told apart: check such crashes by hand. The 0.4% of crashes with no GPS aren't read.",
                "People killed and injured: ARDOT counts only fatalities and serious injuries; a B or C crash counts "
                "one injured person, so injured totals are a floor.",
                "Weather is blank, and primary collision factor, DUI and speed rows are blank: CrashIQ doesn't read "
                "ARDOT's yes/no flags as violation codes.",
                "Crashes count as freeway crashes only when ARDOT files them under Interstate or Ramp, so a "
                "freeway-built US highway (US 67/167) loses that flag: check such corridors by hand."))
