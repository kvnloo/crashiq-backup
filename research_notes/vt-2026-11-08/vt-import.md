# Vermont: crash data for CrashIQ (Hermes, 2026-11-08)

Every number was measured live on 2026-11-08 unless marked. Scripts: `placement_sample.py` (result in
`placement_sample.json`); year counts from the layer's `returnCountOnly` queries; end-to-end in `e2e_result.json`.

## 1. Source: VTrans CrashPQT (the layer behind the Public Crash Data Query Tool)
- Layer: https://services1.arcgis.com/NXmBVyW5TaiCXqFs/arcgis/rest/services/CrashPQT/FeatureServer/0
  (tool: https://apps.vtrans.vermont.gov/CrashPublicQueryTool/). Public ArcGIS, no login, maxRecordCount 2000.
- One row per crash report, 2010 to now; latest ACCIDENTDATE 2026-11-06 (updated near-daily).
- Rows per year (all / no point / no InjuryType = non-reportable / with a cross street and a severity):

  | year | rows | no point | non-reportable | cross street |
  |---|---|---|---|---|
  | 2020 | 10,549 | 554 | 3,753 | 6,374 |
  | 2021 | 10,533 | 322 | 3,507 | 6,629 |
  | 2022 | 8,433 | 119 | 1,013 | 6,811 |
  | 2023 | 7,177 | 85 | 116 | 6,178 |
  | 2024 | 7,064 | 83 | 113 | 5,967 |
  | 2025 | 7,636 | 187 | 139 | 6,391 |

  The drop from ~10,500 to ~7,100 a year is almost all non-reportable rows (an address and nothing else) leaving the
  layer after 2022; reportable crashes are steady at ~6,950-7,500.
- Location: LATITUDE/LONGITUDE on 98.8% of 2024 rows (VTrans' HOWMAPPED: LRS, XY, geocode or officer lat/long). Officer
  street (`STREETADDRESS`, e.g. "US-7 Shelburne Rd", "28 Killington Ave.") and cross street (`INTERSECTIONWITH`).
- Severity: **not KABCO**. `InjuryType` = Fatal / Injury / Property Damage Only. No people counts, no person, vehicle or
  unit table. The pack reads K, U ("injury, level not reported") and O, and sets `severity_note`.
- Other fields: DirOfCollision (VTrans words, mapped to CCRS words where it is one type), DayNight (no street-light
  detail), Weather, SurfaceCondition, Involving (Pedestrian / Bicycle / Motorcycle / Heavy Truck / Animal ...),
  Impairment (not mapped yet), AOTROUTE + AOTACTUALMILEPOINT (999.99 = none), RoadGroup.
- Time: ACCIDENTDATE is the local wall-clock time stored as if UTC (earliest row 2010-01-01 00:00 "UTC").
- County: town id `<county 1-14 alphabetical><2-digit town>` (0403 Burlington) maps to FIPS 2n-1 (50007 Chittenden);
  some rows drop the leading zero (403), handled.

### Licence
No open licence on the layer or the tool. The tool's disclaimer, quoted:
> Errors or Omissions may occur in the data or queries. Only non-personal data is included for analysis in this tool.
> Users assume responsibility for the queries they create. This data is exempt from discovery or admission under
> 23 U.S.C. 409.

Verdict for a paid product: **unclear** (no grant, no prohibition).

### Cities
No Burlington crash open data found in the 2026-11-02 screen (not re-searched): the state layer already covers it.

## 2. Placement sample (Chittenden County, 2025, 2,000 random reportable crashes, seed 2026)
GPS hidden, street pairs placed on a TIGER/Line 2024 network (tl_2024_50007) with `locate.place`:
- GPS present and inside Vermont: 99.7%.
- Street pair (street + cross street): 84.6%; house address with no cross street: 7.1%.
- Placed from names: 33.7% of all (39.8% of pairs). Tiers: exact 613, relaxed 30, verified_typo 18, near 7, fuzzy 5,
  unique_pair 1; review 1,018.
- Auto-placed under the gate's tiers: 30.7% (36.3% of pairs). Within 250 ft of VTrans' point: **78.7%**
  (Wilson 95% low 75.3%).
  Plain `Gate()` auto-places 0 here because a TIGER-only network marks every placement `tiger_road`; the score uses
  `Gate(tiger_only_auto=True)`.
- Why it is low: the cross street is often not a street ("Parking Lot Of Beverage Warehouse", "Goss Dodge Chrysler",
  "Billings Hall", "Exit 15 NB Exit Ramp", "I-89 N MM 70"), and the street often carries a house number with a cross
  street ("434-446 US Route 7 S & Cornelia Court"). Misses > 250 ft are at big junctions ("Dorset St & Williston Road"
  425 ft, "Williston Rd & I89 S On Ramp" 809 ft): VTrans' own point is often LRS- or address-geocoded, so part of the
  gap may be VTrans' point, not the locator.
- House addresses: NAD's feature service returned HTTP 400 on every query on 2026-11-08, so address-point coverage
  for Vermont was **not measured** (VCGI's E911 address points are a lead).
- What it adds: only crashes with no point need the locator, ~1.2-2.5% a year statewide. On the test corridor 58 of
  659 pulled crashes had no point.

## 3. Importer
`backend/crashiq/sources/vt_vtrans.py`: `fetch_contract(box, county_fips, years, cache_dir)` reads crashes with a
point in the box plus no-point crashes of the corridor's counties; non-reportable rows (no InjuryType) are counted in
`cleaning.no_severity_not_read` and not read. Plug-in `statepacks/vt.py`, `status="active"`. Test:
`tests/test_source_vt.py` on a 40-row live fixture (39 KB).

## 4. End to end (port 8105, 2026-11-08)
Shelburne Rd (US 7), South Burlington, Imperial Dr to Home Ave, 1.0 mi, 2020-2024: pulled 659, counted 449
(excluded 210, unplaced 0); K 4, A/B/C 0, U 54, O 391. Four fatal crashes, checked against the layer: 2020-09-04
(Baldwin Ave), 2020-12-14 pedestrian, 2023-09-25 pedestrian, 2024-11-11 bicycle (all at Fayette Rd). No cost column
(VTrans has no per-crash costs). Findings shown 8. PDF 72,517 bytes, Excel 40,801 bytes, 75 s.

## 5. What we didn't check
- Address-point placement (NAD down); OSM+TIGER network placement as the app builds it (sample used TIGER only).
- Whether VTrans' point or the locator is wrong on the > 250 ft misses.
- VTrans' Impairment field mapping (DUI rows blank).
