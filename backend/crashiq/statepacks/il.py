"""Illinois state pack (#19 plug-in): IDOT's statewide crash layers (2014-2025) on its public ArcGIS hub, placed by GPS,
IDOT's own crash KABCO."""

from crashiq.packs import COMING, REF, StatePack

COMING.pop("IL", None)   # shortcut: built now, so no longer "coming"; drop IL from packs.COMING centrally (shared-fixes.md)


def _fetch(box, county_fips, years, cache_dir):
    from crashiq.sources import il_idot
    return il_idot.fetch_contract(box, county_fips, years, cache_dir)


PACK = StatePack(
    code="IL", name="Illinois", fips="17", status="active",
    source="Crash data: IDOT statewide crash layers, Illinois Department of Transportation open data hub (police "
           "reports, SR 1050; 2014-2020 CC BY-SA 2.0, 2021 on with no published licence).",
    source_short="IDOT crash data", bounds=(36.9, -91.6, 42.6, -87.0), first_year=2014,
    methods=REF / "methods_il.json", fetch=_fetch, county_boxes=REF / "county_boxes_il.json",
    final_lag_months=8,   # IDOT freezes a year and posts it the next August (CL 2026-09, 2025 data, Aug 24 2026)
    # IDOT's notice on its 2024 crash layer, quoted (research_notes/il-2026-11-08/il-import.md § Licence)
    legal=("IDOT: \"these maps and the data included hereon, lack the accuracy required for site-specific uses ... the "
           "Department of Transportation and the State of Illinois make no representation, guarantee, or warrant, "
           "either express or implied, regarding the accuracy of these maps or the data furnished thereon.\""),
    data_notes=("IDOT's public layers give one row per crash: no driver, vehicle or person records, so road-user "
                "movements, collision diagrams, motorcycle and truck flags are empty. Pedestrian and bicycle crashes "
                "are found from IDOT's first-crash type only.",
                "Street names are in the 2025 layer only; for 2014-2024 crashes are placed by GPS and the "
                "not-on-the-corridor-street check has no names to use.",
                "IDOT's collision types are its own (Turning, Parked Motor Vehicle, Animal); Angle is counted as "
                "broadside and Front to Rear as rear end.",
                "Primary collision factor, DUI and speed rows are blank: CrashIQ doesn't map IDOT's cause codes yet.",
                "Freeway crashes are those IDOT codes as Interstate or Freeway and Expressway (functional class)."))
