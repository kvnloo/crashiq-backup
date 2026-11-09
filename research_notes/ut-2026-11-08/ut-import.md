# Utah: crash data import (Hermes, 2026-11-08)

Bucket **A** (verified live 2026-11-08): open, record-level, a GPS point on every row, KABCO, statewide, nightly.
Status **active** (end-to-end check passed). Licence for paid use: **unclear**.

## 1. Source: UDOT "Utah Crash Locations"
- Service: https://services.arcgis.com/pA2nEVnB6tquxgOW/arcgis/rest/services/Utah_Crash_Locations/FeatureServer
  (item https://www.arcgis.com/home/item.html?id=834f76028e934c7b84cd32498fe6a1eb, owner UPlan). Query + Extract,
  maxRecordCount 2,000, no login. One layer per year, "2019 Crash Locations" ... "2026 Crash Locations".
- Rows per layer (returnCountOnly, 2026-11-08): 2019 64,544 · 2020 50,409 · 2021 61,141 · 2022 58,806 ·
  2023 59,882 · 2024 59,316 · 2025 59,860 · 2026 48,416 (newest crash 2026-11-04T19:04Z).
  The 2026-11-02 screen's "2025 has only 19,962 rows" is no longer true: 2025 is loaded in full.
- GPS: 2024, 59,316 of 59,316 rows have a point inside Utah (envelope query). The layer's own `lat_utm_y` /
  `long_utm_x` columns hold Web Mercator numbers despite the names; the reader asks for `outSR=4326` instead.
- Time: `crash_datetime` is real UTC (the 2025 layer runs 2025-01-01T07:06Z to 2025-12-31T06:59Z); converted to
  America/Denver for date and hour.
- Severity: crash-level `crash_severity_desc` (Fatal, Suspected Serious Injury, Suspected Minor Injury, Possible
  Injury, No Injury/PDO) = KABCO. People at each level: `number_fatalities`, `number_four_injuries` (A),
  `number_three_injuries` (B), `number_two_injuries` (C), `number_one_injuries` (O) — UDOT's 5-1 scale (UDOT Safety
  Standards site, Crash Costs page). 2024 statewide: O 40,328 · C 9,792 · B 7,421 · A 1,524 · K 251.
- Streets: `main_road_name` ("I-15", "Bangerter Highway Southbound", or a house address "6844 S HIGHLAND DR") and
  `location_desc` ("I-15, at 249 Feet S of 700 South, at 3 tenths of a mile N of MP 307"), from which the reader takes
  the cross street, feet and direction.
- Other columns: functional class, route, milepoint, light, weather, surface, manner of collision, junction, and
  yes/no flags (pedestrian, bicyclist, motorcycle, commercial vehicle, DUI, speed, distracted, hit and run ...).
- No person or vehicle tables (PII removed). UDOT's Numetric / AASHTOWare Safety app has them behind a login.
- Older years: opendata.utah.gov `7ihm-46s4` (State of Utah Crash Data 2015-2019, Socrata) — not read.

## 2. Licence
Item terms (licenseInfo), quoted 2026-11-08: "All data presented here is for informational purposes only and must be
field verified prior to being used on a project. ... Neither the Utah Department of Transportation, the State of Utah,
nor any agency thereof ... make any warranty". Description: "This data is protected under 23 USC 407. 2025 numbers are
preliminary and could change at any time." No reuse grant and no ban: **unclear** for a paid product.
Contact named in the item: Chris Whipple (chriswhipple@utah.gov) for the data.

## 3. Placement sample (the California way)
Salt Lake County (49035), 2024, random 2,000 of 22,871 rows (seed 2026); TIGER/Line 2024 network; `placement_sample.json`.
- GPS present and plausible: **100%**.
- Cross street given: 28.2%. House address instead (no cross street): 64.4%. Neither: 7.4%.
- Hidden-GPS locator test on the street pairs: placed 22.3% of pairs (6.3% of all), auto under
  `Gate(tiger_only_auto=True)` 5.8% of all; within 250 ft 40.5% (Wilson low 32.0%).
  Most pairs are freeway + cross street ("I-15 & 2100 South"), which meet at an interchange, not a TIGER intersection.
  Placement by name doesn't matter here: every crash has GPS.
- House addresses: NAD coverage for Utah not checked.

## 4. Importer
`backend/crashiq/sources/ut_udot.py` (`fetch_contract`), plug-in `backend/crashiq/statepacks/ut.py`, methods
`data/reference/methods_ut.json`, counties `data/reference/county_boxes_ut.json` (29), test `tests/test_source_ut.py`
on a 108 KB fixture of 49 live rows. The reader queries each year's layer by the study box, pages by OBJECTID, caches
the raw JSON, and marks the newest two layers preliminary.

## 5. End to end (port 8102, 2026-11-08)
State Street, 2100 South to 3300 South, South Salt Lake (1.5 mi, 21 study intersections), 2020-2024:
pulled 755, **counted 396**: K 1 · A 13 · B 57 · C 75 · U 0 · O 250. Crash cost **$95,123,826** (UDOT 2026 costs,
K and A at the weighted KA cost). 9 findings shown. PDF 75,568 bytes, Excel 40,994 bytes, 74 s.
Excluded 359: freeway 187 (the I-80 crossing), outside the study limits 114, outside the buffer 30, not on the corridor
street 22, grade-separated crossing 6. (`e2e_result.json`)

## 6. Cities
Salt Lake City: `maps.slc.gov/server/rest/services/Hosted/SLC_Crash_Data/FeatureServer` (SLCPD, snapshot 2023-03-13)
— not needed (the statewide layer covers the city), licence not checked.

## What we didn't check
NAD / county address points for the house-address rows; how Utah grid names ("700 South", "2100 S") key in
`names.py` against TIGER; the 2015-2019 Socrata set; UDOT's statewide crash rates (none found).
