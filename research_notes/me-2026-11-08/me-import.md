# Maine (ME): statewide pack, 2026-11-08

Written by Hermes. Every number was measured live on 2026-11-08 unless a line says otherwise.

## 1. Source
- **MaineDOT Crash Locations - 10 Years Complete**, ArcGIS Online item `b8dd5e49520d4b7495ad8aa3e547b255` (owner MaineDOT.IT, access public), layer
  `https://services1.arcgis.com/RbMX0mRVOFNTdLzd/arcgis/rest/services/Crashes_Attributes_10_Year_and_Current_Year_Test_View/FeatureServer/44`.
  This is the data behind the Maine Public Crash Query Tool (https://mdotapps.maine.gov/MaineCrashPublic/). maxRecordCount 2000, query by OBJECTID pages, no login.
- Item text: "Dataset is derived using RLM (Route Log Mile) … updated weekly on Sunday. Last refreshed on 2026-10-26."
- 359,187 rows, ACCIDENT_DATE 2016-01-01 to 2026-10-22. Rows per year: 2016 33,302, 2017 34,972, 2018 35,186, 2019 35,249, 2020 28,752, 2021 32,649, 2022 34,018, 2023 33,705, 2024 32,728, 2025 35,083, 2026 23,543.
- One row per crash, 112 fields. Severity `INJURY_LEVEL`: K 1,651 / A 6,808 / B 29,215 / C 48,313 / PD 273,200 (all years). Counts `NO_OF_K/A/B/C_INJ` agree: 0 rows with PD and any injured person, 0 K rows with no killed person.
- Location: `LATITUDE`/`LONGITUDE` on all but 4 rows (2 in 2020, 2 in 2021). `LOCATION_TYPE` NODE 105,881 / ELEMENT 253,306; `DOT_LOC_TYPE` = rlm on all.
- **No street names.** `PRIMARY_ROUTE_NAME` is a route code: Portland 2024 top values `US 302` 288, `ST RTE 26` 149, `RD INV 05 60621` 121 (a road-inventory id for a local street), `INT 295 SB` 52. No cross street. Cumberland 2024: 7,818 crashes, 3,006 (38.4%) on `RD INV` roads, 2,799 (35.8%) at a node.
- No unit or person tables. Driver actions of units 1 and 2 sit on the crash row.
- MaineDOT user notes (https://mdotapps.maine.gov/MaineCrashPublic/MaineCrashPublicQueryTool_UserNotes.pdf): "Crash counts only include those crashes coded to Maine Public Roads. Those that occur in parking lots, driveways, private roads are not included."
- County: `COUNTY_CODE` 01…31 is the FIPS county code (05 Cumberland = 23005); all 16 match the Census names.

### Licence
The item's licenseInfo (MEGIS disclaimer): "Users must assume responsibility in determining the usability of this data for their purposes. … please check sources, scale, accuracy, currentness …". No open licence and no commercial-use grant found. **Verdict: unclear** for a paid product. That makes the bucket **A\*** (open, but the licence is unclear), not A as the 2026-11-02 screen said.

## 2. Placement, the California way
- GPS: Cumberland County 2024, 7,818 of 7,818 (100%) inside Maine. Statewide, 4 of 359,187 have no point.
- The street-name locator test (hide GPS, place from names) **can't run**: there are no street names to place from. There are also no no-GPS crashes worth rescuing.
- The point is MaineDOT's own Route Log Mile placement, so it sits on the route's centreline; there is no independent truth to measure it against.
- House addresses: none in the layer.

## 3. Reader and pack
- `backend/crashiq/sources/me_mainedot.py`, `backend/crashiq/statepacks/me.py`, `data/reference/methods_me.json`, `data/reference/county_boxes_me.json`, `tests/test_source_me.py` (fixture `tests/fixtures/me_mainedot_crashes.json`, 38 live rows, 123 KB).
- `primary_road` is left blank. The core's GPS check drops a crash that "names another street" (`assign._names`): `RD INV 05 60621` would read as another street, and `ST RTE 26` doesn't match OSM's `ME 26`. The route code is kept as `route`.
- `is_freeway` = Interstate routes (`INT …`). The layer has no road class (a shortcut, commented in the code).
- Crash types: only the unambiguous ones map to CCRS words (Pedestrians, Rollover, Object in Road). `Rear End / Sideswipe`, `Head-on / Sideswipe` and `Intersection Movement` merge CCRS types, so they keep Maine's words.
- Status **active**: no login, record level with a point, and the end-to-end check below passes.

## 4. End-to-end (live, port 8109, 2026-11-08)
Forest Avenue, Portland, US 302 milepoints 0.1 to 1.1: 0.92 mi, window 2020-2024.
- Pulled 775, counted **525** (excluded 250: outside the buffer 130, outside the study limits 120; unplaced 0).
- K/A/B/C/U/O = 0/5/37/76/0/407.
- Crash cost: none (Maine costs `missing`). Findings shown 8, rejected 0.
- PDF 85.5 KB, Excel 40.4 KB, 104 s.

## 5. What we didn't check
- Licence for paid use (needs MaineDOT's written OK).
- Whether ramps are coded to the Interstate or as `RD INV` (it matters for freeway exclusion near interchanges).
- City feeds: Portland's GPCOG layer is derived from the state tool, so it wasn't read.
