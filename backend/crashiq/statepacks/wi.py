"""Wisconsin: WisDOT's open annual DT4000 crash extracts, statewide, 2017-2022 (research_notes/wi-2026-11-08)."""

from crashiq.packs import REF, StatePack


def _fetch(box, county_fips, years, cache_dir):
    from crashiq.sources import wi_dt4000
    return wi_dt4000.fetch_contract(box, county_fips, years, cache_dir)


PACK = StatePack(
    code="WI", name="Wisconsin", fips="55", status="active",
    source="Crash data: Wisconsin Department of Transportation, Division of State Patrol, annual DT4000 crash data "
           "sets (WisDOT open data; no licence text).",
    source_short="WisDOT crash data", bounds=(42.4, -93.0, 47.4, -86.2), first_year=2017,
    methods=REF / "methods_wi.json", fetch=_fetch, county_boxes=REF / "county_boxes_wi.json",
    # WisDOT's open files stop at 2022 (posted 2023-09); 46 months keeps the default window on 2018-2022.
    # shortcut: tied to WisDOT's posting lag, re-check when WisDOT posts 2023 (then add its Box id to wi_dt4000.YEARS)
    final_lag_months=46,
    legal=("Crash data: Wisconsin Department of Transportation (annual crash data sets, published as open data, no "
           "warranty stated). See 23 USC 407."),
    data_notes=("WisDOT's open crash files stop at 2022 (posted September 2023); 2023 on are in WisDOT's Community "
                "Maps, which allows no bulk download. A study window past 2022 lists those years as missing.",
                "CrashIQ reads WisDOT's crash file only, not its driver and person files: road-user movements and "
                "collision diagrams are empty. Pedestrian, bicycle, motorcycle and truck crashes come from WisDOT's "
                "own crash flags.",
                "Freeway crashes are those WisDOT codes as full access control or on an Interstate."))
