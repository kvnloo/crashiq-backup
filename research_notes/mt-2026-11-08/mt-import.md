# Montana: MDT Public Crash Information (statewide pack, 2026-11-08)

Written by Hermes. Every number below was read live on 2026-11-08 unless marked otherwise.

## Bucket: A* (open, record-level, GPS, KABCO; catch: no licence grant and thin attributes)

The 2026-11-02 screen said A. Verified: the data is open, record-level, statewide and GPS-placed, with crash KABCO.
It is A* because there is no licence for reuse (MDT's terms are "as-is … planning purposes only") and the layer has
no street names, report number, time of day or people.

## 1. Source

**MDT Public Crash Information**, ArcGIS MapServer, no login:
`https://gis.mtmdt.us/server/rest/services/MDTGIS/Public_Crash_Information/MapServer/0`
(item `https://www.arcgis.com/home/item.html?id=13d4ffddc9cd4eadb7e8d41c342573f8`, "MDT Public Crash Information
from 2016-2025"; the layer's own description still says 2020-2024). maxRecordCount 2,000; pages by OBJECTID with
`orderByFields` + `resultRecordCount`; `outSR=4326` returns WGS84; a WGS84 envelope query (`inSR=4326`) works.

Columns (all of them): OBJECTID, ROUTE_ID (MDT corridor, e.g. `C001004A`), RP (reference point, `001+0.791`),
CITY_NAME, COUNTY, CRASH_DATE (date only), COL_TYPE, CRASH_SEVERITY, WEATHER, SURF_COND, LIGHT_COND, X_COORD/Y_COORD
(Montana State Plane, metres), Shape.

| Year | Rows |
|---|---|
| 2016 | 22,111 |
| 2017 | 23,747 |
| 2018 | 22,911 |
| 2019 | 22,650 |
| 2020 | 20,866 |
| 2021 | 22,904 |
| 2022 | 22,311 |
| 2023 | 20,531 |
| 2024 | 20,338 |
| 2025 | 21,047 |
| 2026 | 0 |

Total 219,418. 2 rows have no date, county, route or attributes (their point is near 67.6 N, i.e. junk); the reader
drops them.

- **GPS:** 219,416 of 219,418 rows have a point. The point is MDT's own placement from ROUTE_ID + RP (every row has a
  route; 597 distinct ROUTE_IDs in Yellowstone County 2025 alone, so local streets are on MDT's all-roads LRS too).
- **Street names:** none in the crash layer. MDT's Routes service (`MDTGIS/Routes/MapServer` layers 0 on-system,
  1 off-system, 2 interstate ramps) names each ROUTE_ID segment (`ROUTE_NAME` = `GRAND AVE`, `SIGN_ROUTE` = `US-2`),
  so names could be joined by route + RP; not built (GPS crashes don't need it in CrashIQ's pull).
- **Severity (crash level):** Fatal crash 1,848 · Suspected Serious Injury 6,180 · Suspected Minor Injury 23,341 ·
  Possible injury crash 19,646 · No apparent Injury (PDO) 160,391 · Unknown 8,009 · null 3. K/A/B/C/O as given;
  Unknown → U (as WSDOT's Unknown; user decision pending).
- **Keys:** no crash report number; OBJECTID only (may change when MDT republishes). No person or vehicle table, no
  killed/injured counts.
- **Collision type** has 32 values (Rear-End 39,224, Fixed Object 41,416, Wild Animal 31,626, Right Angle 27,792,
  Roll Over 20,452, Pedestrian 1,848, Bicycle 1,277 …).
- **Freeway:** 29,594 crashes on interstate mainline ROUTE_IDs (C000015/090/094/115/315 A and D). The reader flags
  mainline and the 923 interstate-ramp ROUTE_IDs from MDT's Routes service
  (`data/reference/mt_interstate_routes.json`).
- **Licence (paid use: unclear).** Item licenseInfo, quoted: "This data set is provided "as-is" without warranty of
  any kind. This data should be used for planning purposes only. The Montana Department of Transportation makes no
  representations or warranties whatsoever with respect to the accuracy or completeness of this data set and assumes
  no responsibility for the suitability of this data set for a particular purpose; and MDT will not be liable for any
  damages incurred as a result of errors in this data set." No grant or ban on commercial use. accessInformation:
  "Montana Department of Transportation".
- Also on the server: `MDTGIS/Public_Crash_Information_Animals` (not read). MDT's crash data page
  (`mdt.mt.gov/publications/datastats/crashdata.aspx`) returned "Page not served" on 2026-11-08.

City feeds: none found; the state layer already places 100%, so none are needed.

## 2. Placement sample (the California way)

`placement_sample.py` → `placement_sample.json`: every Yellowstone County crash of 2025 (Billings, Laurel), n = 3,291.

- GPS present and plausible (inside Montana): **3,291 / 3,291 (100%)**; all inside the county's box.
- Street-name placement (hide GPS, TIGER + `locate.place`): **not applicable**: the layer has no street names or
  house addresses, so there is nothing for the locator to read. House-address share: 0 (none in the data).
- 1,459 crashes (44%) share their exact point with another crash: MDT places a crash at its route reference point, so
  crashes coded to one intersection stack on one point. Accuracy of MDT's point against the true spot: not measured
  (no other truth in public data).

## 3. Reader and pack

- `backend/crashiq/sources/mt_mdt.py`: `fetch_contract(box, county_fips, years, cache_dir)` queries the WGS84 envelope
  and the years, pages by OBJECTID, caches raw JSON, returns contract crashes (`packs.check_crash` passes).
  County FIPS from the county name (all 56 MDT names match Census). Collision type and light mapped to CCRS words where
  one exists; others keep MDT's words in capitals.
- `backend/crashiq/statepacks/mt.py`: `status="active"`, first year 2016, MDT's licence text as `legal`, data notes for
  what's missing.
- Years: the reader says years outside 2016-2025 are missing (shortcut: widen when MDT adds 2026).

## 4. End-to-end (live, port 8110, 2026-11-08)

Grand Avenue, Billings, west Billings, longitude -108.6006 to -108.5794 (line `[[45.7841,-108.6006],[45.7841,-108.5794]]`), 1.02 mi,
default window 2020-2024 (AADT 13,250-15,849 on MDT's Routes layer).

- Reader rows 154; contract errors 0; 1 beyond the margin; 153 kept.
- Profile: **131 counted** (22 outside the study ends): K 1, A 1, B 11, C 44, U 13, O 61. KSI 2.
- Crash cost: none (MT costs are a research figure, not printed). Findings screen: 4 shown, 0 rejected.
- Export: PDF 42,156 bytes, Excel 36,056 bytes. Run time 156 s.

## Shared-code fixes

None needed: GPS crashes go through `pull_reader` as they are.
