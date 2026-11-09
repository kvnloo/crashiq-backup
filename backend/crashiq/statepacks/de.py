"""Delaware: DSHS Public Crash Data on data.delaware.gov, statewide (sources/de_dshs.py)."""

from crashiq.packs import REF, StatePack


def _fetch(box, county_fips, years, cache_dir):
    from crashiq.sources import de_dshs
    return de_dshs.fetch_contract(box, county_fips, years, cache_dir)


PACK = StatePack(
    code="DE", name="Delaware", fips="10", status="active",
    source="Crash data: Public Crash Data, Delaware Department of Safety and Homeland Security (data.delaware.gov; "
           "police crash reports; no published reuse licence).",
    source_short="DSHS Public Crash Data", bounds=(38.4, -75.8, 39.9, -75.0), first_year=2009,
    methods=REF / "methods_de.json", fetch=_fetch, county_boxes=REF / "county_boxes_de.json",
    final_lag_months=6,                          # "crashes that occurred since 2009 through six months ago"
    # DSHS's dataset description, quoted (research_notes/de-2026-11-08/de-import.md §2)
    legal=("DSHS: \"The data contained on FirstMap and the Open Data Portal represents the best available information at "
           "DSHS and is not an official record of what transpired in a particular crash or for a particular crash "
           "type and does not contain personal information.\" Safety studies: 23 U.S.C. 407."),
    severity_note=("Delaware's public crash data gives a crash class only: fatal, personal injury or property damage. "
                   "KSI here is fatal crashes only, and there is no A/B/C split; injury crashes are counted as "
                   "'injury, level not reported' (U)."),
    data_notes=("Delaware's public crash data has no street names, road class, report number, or driver, vehicle and "
                "person records: crashes are placed by their GPS point only, freeway crashes aren't told apart, people "
                "killed and injured aren't counted, and road-user movements and collision diagrams are empty.",
                "Non-reportable crashes (private property, or damage under Delaware's $2,000 reporting threshold) are "
                "left out, as DelDOT's safety program counts fatal, injury and property damage only crashes.",
                "Primary collision factor, DUI and speed rows are blank: CrashIQ doesn't map Delaware's contributing "
                "circumstance and alcohol flags to them yet."),
)
