# South Carolina: crash data for CrashIQ (Hermes, 2026-11-08)

**Verdict: bucket D (gated) statewide, verified live 2026-11-08. No state pack.** The 2026-11-02 screen was right in
effect, but it missed one thing: SCDPS *did* publish its raw statewide collisions under **CC BY 4.0** (2017 – Oct 2021).
That public layer now returns 0 rows, and the layer behind it needs a token. If SCDPS refreshes it, South Carolina becomes
open (bucket A) with a licence that allows paid use with attribution. A "bring your export" column map is in
`sc-column-map.json`.

## 1. Statewide: SCDPS (gated today)

| Source | What it is | Access (2026-11-08) |
|---|---|---|
| SCDPS master crash file (Office of Highway Safety and Justice Programs, Statistics Section), https://scdps.sc.gov/media-and-public-information/traffic-collision-facts | Every TR-310 report; "Statistics Section maintains the South Carolina traffic collision database" | Records/statistics request only. The 2026-11-02 URL `scdps.sc.gov/ohsjp/stat_services` now returns "Page not found". |
| SCDPS Collisions, https://services7.arcgis.com/TdsEnMqzMcTd7pnb/arcgis/rest/services/Extrnl_Collisions_Collision_Dashboard/FeatureServer/0 (item 6b1c4cc6aa5b4042ab8458a0f24c422b, owner `SCDPS_Admin`) | "SCDPS 2017-2021 Raw Collision Data … Collision data dates Jan. 2017- Oct. 2021. Data will be updated on a yearly basis." 39 fields: AccidentNumber, CrashDate, hour, County, Agency, Route/Street + base and second intersection, fatalities and injuries by K/A/B/C, harmful events, factors, light, surface, weather, Latitude/Longitude, CMV, WorkZone | Public view, but `returnCountOnly` = **0** and any row query fails ("Invalid query parameters"). Last data edit 2021-12-07. The dashboard's source layer `Extrnl_Collisions/FeatureServer/16` answers "Token Required". |
| SCDPS Collision Dashboard (item 3bf3eb760f5a4642820d158a88408e55) | "statewide collision data from Highway Patrol and local agencies … updated on an annual basis" | Same token-gated layer. |
| SCDPS Traffic Collision Fact Books (PDF) | yearly tables | Aggregates only. |
| SCDOT (gis.scdot.org/hosting) | 90+ public services (ADT, speed limits, routes, `SC_Geolocator_2025`) | No crash layer. SCDOT gets the master file from SCDPS quarterly (ED 75, per the 2026-11-02 screen). |

Licence for paid use: **ok_with_attribution, if SCDPS republishes** (CC BY 4.0 on items 6b1c4cc6… and 3bf3eb76…:
"This work is licensed under a Creative Commons Attribution 4.0 International License"; access information "2021 SCDPS").
For the master file by request: unclear (no terms found).

## 2. Open regional layers (fill gaps only; none is statewide)

| Layer | Owner | Rows | Years | Location | Severity | Licence |
|---|---|---|---|---|---|---|
| 2017 to 2025 GPATS Crash Data, https://services3.arcgis.com/bjOyhhlaaCIcmO3H/arcgis/rest/services/2017_to_2025_GPATS_Crash_Data/FeatureServer/0 (item 4bc1d05d6a9848049ca8b2132fe3d91f) | Greenville County GIS for the GPATS MPO | 188,597 crashes (Greenville 156,298 · Pickens 15,944 · Anderson 8,965 · Spartanburg 6,331 · Laurens 1,059) | 2017-01-01 to 2025-12-31 (updated 2026-09-11) | Latitude/Longitude; SCDOT SMS main route + base route + milepoint | crash max injury: Fatal 800, Serious/Incapacitating 2,245, Minor/Non-Incapacitating 9,439, Possible 25,377, No Injury 150,736 | none stated |
| Spartanburg County Crash Data Monthly Update, https://services6.arcgis.com/bom7L4u7y1k0qkF1/arcgis/rest/services/Spartanburg_County_Crash_Data_Monthly_Update/FeatureServer/0 (item 778df09381b44d9982bc5c7fe9489ad5) | `tdgsoutheastgis` for Spartanburg County | 32,463 person rows; 10,674 crashes in 2024 | 2024-01-01 to 2025-04-27; "intended to be replaced monthly" but last changed 2025-05-05 | GPS (DMS + decimal) 99.95%; TR-310 on-route + base-route + offset miles + direction | per person: Fatal / Incapacitating / Non-Incapacitating / Possible Injury / Not Injured | none stated |
| Sumter County Accident Data; Clemson SS4A; Florence ped/cycle | local | not measured | | | | |

## 3. Placement sample, the California way (`placement_sample.py`, `placement_sample.json`)

2,000 random Spartanburg County 2024 crashes (of 10,674; seed 2026) from the county layer, which carries SCDPS's
TR-310 location fields. GPS hidden, placed from `on_route_street_name` + `base_route_street_name` (route number when the
name is blank or fails: `Interstate 85` → `I 85`, `SC Primary 9` → `SC 9`), offset `base_distance_offset` miles toward
`offset_direction`, on TIGER/Line 2024 (45083).

| Measure | Value |
|---|---|
| GPS present and inside SC | 99.95% |
| On-route + base-route both given | 99.35% |
| Placed by name (any tier but review) | 84.35% (152 needed the route-number retry) |
| Tier gate (`exact` / `unique_pair`) | 80.55% |
| Within 250 ft, tier gate | **47.7%** (Wilson 95% low 45.2%) |
| `Gate().auto` | 0%: TIGER-only network, `tiger_only_auto` off |
| House-address share | 0% (no address field) |

Why the 47.7% (an extra check on 800 crashes, seed 7, `exact` tier only):

| Offset in the report | n | Within 250 ft, at the intersection | Same, offset applied as miles |
|---|---|---|---|
| 0 | 99 | 73.7% | 73.7% |
| under 0.1 mi | 233 | 72.5% | 72.1% |
| 0.1 mi or more | 204 | 13.7% | 12.7% (median 915 → 1,321 ft) |

So at the intersection SC places about as well as Georgia (74%), and the long offsets are the problem: moving the point
along the on-route toward `offset_direction` makes it *worse*. Either SC's direction means something else (direction
from the crash to the base point, not from the base point), or the officer GPS isn't at the offset spot. The TR-310
manual (`~/.hermes/state-manuals/sc/TR-310_Report_Manual_May2019.pdf`, 122 pages) is scanned, with no text layer, so we
couldn't read its definition. This goes in `shared-fixes.md` only once the meaning is known: no fix proposed.

What else breaks in the names: bare route numbers (`60 & DUNCAN REIDVILLE RD`), `HIGHWAY 56`, ramps
(`85 SB ON RAMP`, `EXIT RAMP`), and the same street as on- and base-route (`ASHEVILLE HWY & ASHEVILLE HWY`).

## 4. Cities
- Greenville area: GPATS layer above (the best SC open source found: 9 years, current to 2025, no licence).
- Columbia, Charleston: no open crash feed found (ArcGIS Online search, 2026-11-08).

## 5. Methods (costs, rates)
Not collected: no pack. SCDOT ED 75 (VRU Safety Program) and the "Crash Rates" layer (`gallowayra_SCDOT`) suggest SCDOT
methods exist; not checked.

## What the user needs to do
1. Ask SCDPS (OHSJP Statistics Section) to refresh the CC BY 4.0 "SCDPS Collisions" public layer (2022–2025), or for
   the statewide master crash file (crash + unit + occupant, 2021–2025) and written permission for a paid tool.
2. Ask what TR-310's "direction from base point" means (which way the offset runs).
3. Optional: ask Greenville County GIS / GPATS for a licence on its 2017–2025 layer.

## What we didn't check
- The TR-310 field definitions (scanned PDF).
- GPATS placement (only Spartanburg was sampled).
- SCDOT crash costs and rates.
