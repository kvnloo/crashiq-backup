"""Alaska: DOT&PF Public Crash Portal (DMV crash reports, the most recent five complete years), no login."""

from crashiq.packs import REF, StatePack


def _fetch(box, county_fips, years, cache_dir):
    from crashiq.sources import ak_dotpf
    return ak_dotpf.fetch_contract(box, county_fips, years, cache_dir)


PACK = StatePack(
    code="AK", name="Alaska", fips="02", status="active",
    source="Crash data: Alaska DOT&PF Public Crash Portal (public.alaskadata.net; DMV crash reports, the most recent "
           "five complete years; no published reuse licence).",
    source_short="Alaska DOT&PF Public Crash Portal", bounds=(51.0, -180.0, 71.6, -129.9), first_year=2021,
    methods=REF / "methods_ak.json", fetch=_fetch, county_boxes=REF / "county_boxes_ak.json",
    # shortcut: the portal held 2025 complete by Nov 2026 (built 2026-11-04) and drops its oldest year as it adds one;
    # first_year stays 2021 until the 2026 roll-in is seen, then the reader reports 2021 as missing
    final_lag_months=10,
    # the portal's opening notice, quoted (research_notes/ak-2026-11-08/ak-import.md § licence)
    legal=("Alaska DOT&PF: \"The information in this report is compiled for highway safety planning purposes. Federal "
           "law prohibits its discovery or admissibility in litigation against state, tribal or local government that "
           "involves a location or locations mentioned in the collision data. 23 U.S.C. § 407; 23 U.S.C. § 148(h)(4); "
           "Walden v. DOT, 27 P.3d 297, 304-305 (Alaska 2001).\" The Alaska DMV is the official custodian of the data."),
    data_notes=("Alaska's public crash portal gives each crash's point, severity and crash type but no street names, "
                "driver, vehicle or person records: people killed and injured aren't counted, and road-user movements "
                "and collision diagrams are empty. About 1% of crashes have no point and can't be placed.",
                "The portal holds only the most recent five complete years (2021-2025 in November 2026).",
                "Crashes on routes Alaska classes as Interstate (the Parks Highway in Wasilla, the Sterling Highway in "
                "Soldotna) count as freeway crashes, so an arterial study on such a route loses them: check those "
                "corridors by hand.",
                "Primary collision factor, DUI and speed rows are blank: CrashIQ doesn't read the portal's alcohol, "
                "drug and speeding flags yet."))
