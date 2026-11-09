# Georgia: crash data for CrashIQ (Hermes, 2026-11-08)

**Verdict: bucket D (gated) statewide, verified live 2026-11-08. No state pack.** The 2026-11-02 screen was right for Georgia.
An open regional layer covers the 19-county Atlanta region (half the state's crashes), but it has the year only (no date
or time) and no licence. A "bring your export" column map is in `ga-column-map.json`.

## 1. Statewide: GDOT (gated)

| Source | What it is | Access | Checked |
|---|---|---|---|
| GEARS (Georgia Electronic Accident Reporting System), https://www.gearsportal.com/Pages/Public/Home.aspx | GDOT's crash database, every GDOT-523 report | "Only authorized users have access to GEARS data and reporting." Law-enforcement and non-law-enforcement access by request | 2026-11-08 |
| GDOT Crash Data Dashboard, https://gdot.aashtowaresafety.net/crash-data-dashboard (linked from https://www.dot.ga.gov/GDOT/pages/CrashReporting.aspx) | AASHTOWare Safety (Numetric) public dashboard, "crashes that occurred over the last 5 years" | Charts and map only. The page is a JavaScript app (`/bundle/portals-v2`); no download or open API is offered. We did not reverse-engineer the vendor's private API. | 2026-11-08 |
| GDOT Request for Crash Data (Office of Traffic Safety & Design), https://www.dot.ga.gov/PartnerSmart/permits/Documents/Request_for_Crash_Data.pdf | Detailed listing / summary / rates per county + route + milepost or intersection | Form by fax. Disclaimer: the data "is not to be sold to anyone … GDOT does not support business decisions based upon the use of this data." | 2026-11-08 |
| BuyCrash (LexisNexis), https://buycrash.lexisnexisrisk.com | Single crash reports, paid | Per-report purchase; not a dataset | 2026-11-08 |
| gis10.dot.ga.gov `GeoTRAQS/MapServer/26` "GDOT_Crashes" (found via ArcGIS Online search) | GDOT internal map layer | No response from outside (curl status 000, 2026-11-08) | 2026-11-08 |

Licence for paid use: **no / unclear**. The only GDOT licence text found is the request-form disclaimer above
("is not to be sold to anyone"). CrashIQ would not resell the rows, but the text doesn't grant use in a paid tool either.

## 2. Open regional and city layers (fill gaps only; none is statewide)

| Layer | Owner | Rows | Years | Location | Severity | Missing | Licence |
|---|---|---|---|---|---|---|---|
| Crashes 2020-2024, https://services1.arcgis.com/Ug5xGQbHsD8zuZzM/arcgis/rest/services/Crashes2020_2024/FeatureServer/0 (item fea7cdf5c08d482783e7bdf7fad4424b) | Atlanta Regional Commission (`TKotak_ARC`); GDOT AASHTOWare field names | 1,074,688 | 2020 192,822 · 2021 229,558 · 2022 219,555 · 2023 216,458 · 2024 216,295 | Latitude/Longitude 100% in sample; road + intersecting road 90.5% | crash KABCO: `(K) Fatal Injury` … `(O) No Injury`, `Unknown` 10,895 | date, time, report number, collision type, light, weather, people, vehicles | **none stated** (licenceInfo empty) |
| MARTACountyCrashes_2023, https://services1.arcgis.com/Ug5xGQbHsD8zuZzM/arcgis/rest/services/MARTACountyCrashes_2023/FeatureServer/0 | ARC | 103,137 | 2023 | lat/lon; Collision_ID, Date, Time, manner, light, surface | KABCO | other years; carries names and ages (PII) | none stated |
| COA_2022AllCrashes (ARC org) | City of Atlanta via ARC | not measured | 2022 | not measured | not measured | | none stated |

Counties in the ARC layer (rows): Fulton 262,892 · DeKalb 183,339 · Gwinnett 143,709 · Cobb 124,738 · Clayton 68,912 ·
Henry 46,588 · Cherokee 32,587 · Forsyth 29,858 · Douglas 28,000 · Coweta 21,447 · Carroll 19,698 · Paulding 18,934 ·
Rockdale 17,777 · Fayette 17,664 · Newton 16,075 · Barrow 14,671 · Walton 12,620 · Spalding 10,260 · Dawson 4,918 ·
Meriwether 1.

Why no pack from the ARC layer: CrashIQ's study needs a crash date (window, day/time charts, before/after); the layer
gives `Crash_Year` only. Writing `YYYY-01-01` would be invented data. It also covers 19 of 159 counties and has no
licence. If ARC adds dates and a licence, it becomes a good metro-Atlanta reader (one ArcGIS query per county box).

## 3. Placement sample, the California way (`placement_sample.py`, `placement_sample.json`)

2,000 random Fulton County 2024 crashes from the ARC layer (seed 2026). GPS hidden, placed from
`Roadway (From Crash Report)` + `Intersecting Roadway` on TIGER/Line 2024 (13121) with `locate.place`.

| Measure | Value |
|---|---|
| GPS present and inside Georgia | 100.0% |
| Road + intersecting road both given | 90.45% |
| Placed by name (any tier but review) | 64.45% of all, 71.25% of pairs |
| Tier gate (`exact` / `unique_pair`) | 61.75% of all |
| Within 250 ft of the hidden point, tier gate | 74.5% (Wilson 95% low 72.0%) |
| `Gate().auto` | 0%: every road in a TIGER-only network is `tiger_road`, and `tiger_only_auto` is off. With OSM the share would be higher (not measured). |
| House-address share | 0% (no address field) |

The 74.5% is against the layer's own point, which GDOT may itself have snapped to its route network; it is not
checked against the officer's GPS.

What breaks in the street names (wrapped in the script, not shared code):
- `Ga120`, `Sr 5`, `I- 285 W` → pre-split to `GA 120`, `SR 5`, `I 285`.
- Bare route numbers: `285`, `400`, `400 & 285` (I-285, GA 400). Not resolvable without knowing the route type; left unplaced.
- Ramps: `400 On Rp & Northridge Rd`.
- Big multi-leg intersections: `GA 120 & GA 9`, `I 85 & SR 400` meet in more than one place.
- 9.5% have `(none)` as the intersecting road.

## 4. Cities
Atlanta: no city crash feed beyond the ARC layers above (Atlanta DPW publishes a High Injury Network, not crashes).

## 5. Methods (costs, rates)
Not collected: no pack. GDOT's crash-data request form offers "Accident Rates", which suggests a GDOT rate method
exists; not checked.

## What the user needs to do
1. Ask GDOT (Crash Reporting Unit / GEARS, 866-495-4206, or Office of Traffic Safety & Design) for a statewide
   AASHTOWare Safety (GEARS) crash export, crash + vehicle + person, with written permission to use it inside a paid tool.
   The request form's disclaimer ("not to be sold to anyone") needs a written carve-out.
2. Or ask ARC for a licence on "Crashes 2020-2024" and for the crash date and time fields.
3. With an export in hand: map it with `ga-column-map.json`.

## What we didn't check
- The vendor dashboard's internal API (deliberately not used).
- Accuracy against officer GPS (only against the layer's point).
- GDOT costs and rates.
