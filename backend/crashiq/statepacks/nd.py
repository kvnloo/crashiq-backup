"""North Dakota: NDDOT crash records (2017-2025), from the public crash layer NDSU's DOT Support Center hosts for NDDOT."""

from crashiq.packs import REF, StatePack


def _fetch(box, county_fips, years, cache_dir):
    from crashiq.sources import nd_nddot
    return nd_nddot.fetch_contract(box, county_fips, years, cache_dir)


PACK = StatePack(
    code="ND", name="North Dakota", fips="38", status="active",
    source="Crash data: NDDOT crash records, through the public ArcGIS crash layer NDSU's DOT Support Center (Upper "
           "Great Plains Transportation Institute) hosts for NDDOT (2017-2025; no published reuse licence).",
    source_short="NDDOT crash records", bounds=(45.9, -104.1, 49.1, -96.5), first_year=2017,
    methods=REF / "methods_nd.json", fetch=_fetch, county_boxes=REF / "county_boxes_nd.json",
    # NDDOT Traffic Operations Manual (Jan 2026), p. 19, quoted (research_notes/nd-2026-11-08/nd-import.md § licence)
    legal=("NDDOT: crash data \"is considered to be exempted from disclosure pursuant to 23 USC § 407\" (NDDOT Traffic "
           "Operations Manual, January 2026, p. 19)."),
    data_notes=("North Dakota's public crash layer gives each crash's point, severity and crash type but no street "
                "names, driver or vehicle records: road-user movements and collision diagrams are empty.",
                "North Dakota raised its reporting threshold from $1,000 to $4,000 of property damage on August 1, "
                "2019, so property-damage crashes before then aren't comparable with later years.",
                "Primary collision factor, DUI and speed rows are blank: CrashIQ doesn't read NDDOT's crash flags for "
                "them yet."))
