"""Montana: MDT Public Crash Information (statewide ArcGIS layer, 2016-2025, open, no login)."""

from crashiq.packs import REF, StatePack


def _fetch(box, county_fips, years, cache_dir):
    from crashiq.sources import mt_mdt
    return mt_mdt.fetch_contract(box, county_fips, years, cache_dir)


PACK = StatePack(
    code="MT", name="Montana", fips="30", status="active",
    source="Crash data: MDT Public Crash Information, Montana Department of Transportation (open ArcGIS layer; "
           "no open licence, MDT's as-is terms).",
    source_short="MDT Public Crash Information", bounds=(44.3, -116.1, 49.1, -104.0), first_year=2016,
    methods=REF / "methods_mt.json", fetch=_fetch, county_boxes=REF / "county_boxes_mt.json",
    # MDT's item licence text, quoted (research_notes/mt-2026-11-08/mt-import.md § licence)
    legal=("MDT: \"This data set is provided 'as-is' without warranty of any kind. This data should be used for "
           "planning purposes only. The Montana Department of Transportation makes no representations or warranties "
           "whatsoever with respect to the accuracy or completeness of this data set…\""),
    data_notes=("MDT's public crash layer gives each crash's point, date and crash severity, but no time of day, street "
                "names, report number, or driver, vehicle and person records: hour-of-day and road-user tables and "
                "collision diagrams are empty, and people killed and injured aren't counted.",
                "MDT places every crash on its route reference (route and reference point): crashes at one "
                "intersection share one point, so a crash's exact spot on the approach isn't known.",
                "MDT's 'Unknown' crash severity (about 4% of crashes) is counted as injury, level not reported (U), "
                "pending a decision.",
                "Primary collision factor, DUI and speed rows are blank: MDT's layer has no violation codes."))
