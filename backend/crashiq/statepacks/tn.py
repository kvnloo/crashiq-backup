"""Tennessee state pack (#19 plug-in): TDOT's public statewide crash layer for 2021-2024 (every crash, KABCO), then
TDOSHS's public fatal+injury dashboard layer (TITAN reports, KABC) for 2025 on; inside Nashville, Metro's no-injury
crashes fill the property-damage gap from 2025."""

from crashiq.packs import REF, StatePack


def _fetch(box, county_fips, years, cache_dir):
    from crashiq.sources import tn_tdot
    return tn_tdot.fetch_contract(box, county_fips, years, cache_dir)


PACK = StatePack(
    code="TN", name="Tennessee", fips="47", status="active",
    source="Crash data: TDOT's statewide crash layer, 2021-2024 (TDOT GIS); from 2025, the Department of Safety and "
           "Homeland Security's public crash dashboard layer (TITAN reports) and, inside Nashville, Metro Nashville "
           "Traffic Accidents (Nashville Open Data). No published reuse licence.",
    source_short="TDOT and TDOSHS crash layers", bounds=(34.9, -90.4, 36.7, -81.6), first_year=2021,
    methods=REF / "methods_tn.json", fetch=_fetch, county_boxes=REF / "county_boxes_tn.json",
    # TDOT's layer disclaimer, quoted (research_notes/tn-2026-11-08/tn-import.md § Licence)
    legal=("TDOT: \"All data presented here is for informational purposes only… Neither the Tennessee Department of "
           "Transportation, the State of Tennessee, nor any agency thereof… make any warranty, express or implied… "
           "for the accuracy, completeness, or usefulness of the data.\" (23 USC 407 applies to safety studies.)"),
    data_notes=("2021-2024 come from TDOT's statewide layer (every crash, KABCO). From 2025 the only public statewide "
                "source is the Department of Safety's fatal and injury layer: outside Nashville a 2025 or later year "
                "has no property-damage crashes, so its totals and PDO share are low.",
                "Inside Nashville, from 2025, Metro Nashville's no-injury crashes are added as property damage only "
                "(O); Metro's injury crashes are already in the state's layer and are not read twice.",
                "Neither state layer has street names (TDOT gives a route number: SR 11, I 24) or driver and vehicle "
                "records: crashes are placed by their point, and road-user movements and collision diagrams are empty.",
                "Freeway crashes are those TDOT puts on an interstate (2021-2024); from 2025 the state's layer has no "
                "road field, so check a corridor beside an interstate by hand.",
                "Primary collision factor rows are blank; DUI and speeding are the Department of Safety's flags (2025 "
                "on); motorcycle and truck counts are 2025 on only."))
