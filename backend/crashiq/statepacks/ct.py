"""Connecticut: the Connecticut Crash Data Repository's public crash layers (UConn CTSRC for CTDOT), statewide, GPS on
every crash, KABCO. Research: research_notes/ct-2026-11-08/."""

from ..packs import REF, StatePack
from ..sources import ct_uconn


def _fetch(box, county_fips, years, cache_dir):
    return ct_uconn.fetch_contract(box, county_fips, years, cache_dir)


PACK = StatePack(
    code="CT", name="Connecticut", fips="09", status="active",
    source="Crash data: Connecticut Crash Data Repository (UConn Connecticut Transportation Safety Research Center for "
           "CTDOT), public crash, person and vehicle layers; no published reuse licence.",
    source_short="Connecticut Crash Data Repository", bounds=ct_uconn.CT_BOUNDS, first_year=2015,
    methods=REF / "methods_ct.json", fetch=_fetch, county_boxes=REF / "county_boxes_ct.json",
    final_lag_months=6,     # CTCDR: PDO about 3 months behind, fatal reports 3-6 months
    # the repository's own footer, quoted (research_notes/ct-2026-11-08/ct-import.md § licence)
    legal="Connecticut Crash Data Repository: \"This web site is exempt from discovery or admission under 23 U.S.C. 409.\"",
    data_notes=("Connecticut's public layers give each crash's point, KABCO, road and town, and its people and vehicles, "
                "but no vehicle movements: road-user movements and collision diagrams are empty.",
                "Crashes on state-maintained roads are filed under the route number (\"84-W\", \"187-N\"); CrashIQ reads "
                "them as I 84, US 44 or CT 187 by the route class. Only about a quarter of crashes name an "
                "intersecting road.",
                "Primary collision factor, DUI and speed rows are blank: CrashIQ doesn't map CTCDR's contributing "
                "circumstances yet."),
)
