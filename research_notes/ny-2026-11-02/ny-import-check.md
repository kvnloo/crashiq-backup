# New York import check (Hermes, 2026-11-02, live queries)

## Statewide public tables (data.ny.gov, DMV, OPEN-NY terms: commercial use OK)
- Case e8ky-4vqe: years 2021-2024 only (372,159 / 390,855 / 381,290 / 380,819). Last update Jan 2026; 2025 not posted.
- Case columns: year, date, time, county_name, municipality, dot_reference_marker_location, accident_descriptor, collision type, road/weather/light/surface, traffic control, ped/bike action, event, n vehicles.
- **No street names, no coordinates, no case ID.** Individual (ir4y-sesj) and Vehicle (xe9x-a24f) tables have no key back to Case, so person severity can't be tied to a crash.
- Crash severity = accident_descriptor only: 2024 Fatal 1,026; Injury 38,114; PD 264,557; PD&Injury 77,122. Not KABCO.
- Person severity (Individual, 2024): Killed 1,090; Severe 13,133; Moderate 20,199; Minor 118,066; Unknown 7,230.
- Reference marker filled: 135,683 of 380,819 (35.6%) in 2024 = state-highway crashes; 126,195 of them outside NYC.

## Reference marker -> GPS join (works)
- NYSDOT layer: https://gisportalny.dot.ny.gov/hostingny/rest/services/Roadways/Roadway/FeatureServer/0 (185,384 markers, public, no login).
- Panel = 4-char route (right-justified, suffix letter in 4th char) + 8 digits. Crash value is left-stripped: `panel = rm[:-8].rjust(4) + rm[-8:]`.
- Sample of 100 2024 crash markers (4 offsets): 99 exact matches to a marker point. Last 4 digits = tenths of a mile, so placement is +-0.05 mi along the route; side street unknown.
- Same service: Milepoint (2), Roadway Inventory (3). RDM_Roadway_Current has route, functional class, lanes, speed limit, Traffic_Station_ID. RDM_Traffic_Stations has station segments (58,181) but no AADT values in that layer; AADT source still to confirm (gis.ny.gov AADT set dated 2019/2020, NYSDOT Traffic Data Viewer).

## NYC (data.cityofnewyork.us h9gi-nx95)
- Feed live again: max crash_date 2026-10-31 (was paused 2026-06-11 in the Oct check). 2,302,571 rows.
- Lat/long: 2023 92.5%, 2024 92.2%, 2025 99.2%, 2026 99.3%.
- Has on/cross/off street names, collision_id, injured/killed counts by mode, contributing factors. Not KABCO (injured vs killed only).
- NYC = 88,924 of 380,819 statewide 2024 crashes in DMV table (23%).

## CLEAR (NYSDOT)
- Geocoded, all public roads, 2013-present, nightly, KABCO-capable; access = NY government staff and consultants on NY government projects; everyone else FOIL. (dot.ny.gov Crash Analysis Toolbox.)
- TSSR (ITSMR) public but aggregate only (state/county/municipality).

## User decision (2026-11-02, Telegram)
- Plan: Part A (public: state highways via reference markers + NYC open data) **and** Part B (CLEAR export importer).
- Sample CLEAR export: user will find one later; Part B waits for it.
