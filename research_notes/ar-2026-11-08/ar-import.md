# Arkansas: crash data for CrashIQ (Hermes, 2026-11-08)

Every number below was measured live on 2026-11-08 unless marked. Scripts: `ar_pull.py` (sample + fixture);
county-prefix check in `county_prefix.json`; end-to-end result in `e2e_result.json`.

## 1. Sources

### 1a. ARDOT Arkansas Crash Analytics Tool (ACAT) layer: the source used
- Layer: https://gis.ardot.gov/referenced/rest/services/TPP_TrafficSafety/NotForOfficialUse/FeatureServer/20
  (public ArcGIS FeatureServer behind the ACAT dashboard
  https://gis.ardot.gov/portal/apps/dashboards/3ae35f942fa340888abd27f26d405558; item 52c1d278ef314f0e83de0436f5257884,
  modified 2026-09-28). No login. maxRecordCount 2000.
- What it is (FHWA GIS webinar 44, https://www.gis.fhwa.dot.gov/webinars/webinar44_Using_GIS_for_Data_Dashboards_ACAT.aspx):
  ASP eCrash reports, shared with ARDOT under an MOU, "cleaned" by ARDOT Traffic Safety, located on ARNOLD (ARDOT's
  all-road LRS), capped at five years.
- Rows: 401,279 crashes. Per year: 2021 81,037 · 2022 79,220 · 2023 81,907 · 2024 81,032 · 2025 78,083.
  Dates 2021-01-01 to 2025-12-31. `StateCaseNumber` unique (group-by having count > 1 returned none).
- Location: Latitude/Longitude on 399,812 (99.63%); 1,467 have none, all inside Arkansas's box (0 outside).
  `AH_RoadID` (county x road x section x direction) + `AH_Logmile` on 399,322.
- Road systems: City Street 171,278 · State Highway 99,525 · US Highway 77,018 · Interstate 48,659 · Unknown 4,373 ·
  Frontage 304 · Ramp 122.
- Severity: KABCO text, crash level: K 2,837 · A 11,173 · B 39,542 · C 43,950 · O 303,777.
  People: only `NumFatalities` and `NumSerInj` (no B/C/injured count). No person, vehicle or unit table.
- Other fields: CrashManner (9 values), LightingConditions, RoadwaySurfaceConidtion (sic), RoadSystem, Rural/Urban,
  yes/no flags (speed, work zone, roadway departure, intersection, unrestrained, impaired, non-motorist, CMV,
  motorcycle), NonMotoristType (Pedestrian 2,618, Bicyclist 1,153, Scooter 108, ...), City, County, Agency, MPO.
  **No weather field. No officer street text.**
- Street names: the road name exists only inside `AH_RoadID` with spaces removed (`60xNRODNEYPARHAMRDx102xA`);
  `IntersectingStreetName` is on 161,507 statewide (40.2%), and in Pulaski 2025 on 38.9%, of which 31.6 points have
  spaces ("N RODNEY PARHAM RD") and 7.4 points don't ("KAVANAUGHBLVD"). Neither form reaches CrashIQ's street keys,
  so the reader leaves both road fields empty (see shared-fixes.md).
- Counties: `County` is the name ("Pulaski"), sometimes a neighbouring state's county for border crashes
  ("Bowie County" 484, Texarkana). ARDOT's road-id county number is alphabetical 1-75 **except St. Francis = 68**
  (sorted after Sharp); Census FIPS order puts St. Francis before Saline. Checked on 200 rows for each of the 75
  counties: the road-id number named the county on 75/75. The reader takes the road id's county first.
- Time: `CrashDate` is the local date and time as UTC epoch ms; its America/Chicago time equals `CrashTime` on
  15,030/15,030 Pulaski 2025 rows. `CrashTime` is "4:45 PM" before 2025 and "19:15:00" in 2025.

### Licence
No licence on the layer or the dashboard item. The item text, quoted (licenseInfo of 3ae35f942fa340888abd27f26d405558,
also the layer item's description):
> The data contained in the web-based dashboard is not an official record for crash statistics or what transpired in
> a crash. If a user is interested in an official copy of a crash report or crash statistics, please contact Arkansas
> State Police. … Users are advised that their use of any ARDOT GIS Data is at their own risk. Under federal law,
> this information is not subject to discovery and cannot be admitted into evidence … (see 23 USC, Section 409).

Verdict for a paid product: **unclear** (no grant, no prohibition). The service name is "NotForOfficialUse"; FHWA's
2019 webinar said the data "cannot be downloaded", the REST layer now can be. It could change without notice.

### 1b. Arkansas State Police eCrash: no open data
ASP sells single reports ($10 involved / $25 not involved, https://crashreports.ark.org/,
https://dps.arkansas.gov/law-enforcement/arkansas-state-police/services-programs/crash-records/). No record-level
open dataset was found. ACAT is the public face of the same eCrash data.

### 1c. Cities
No city open-data crash feed found for Little Rock, Fort Smith, Fayetteville or Springdale (2026-11-02 screen; not
re-searched). Not needed: the state layer already has GPS everywhere.

## 2. Placement sample (Pulaski County, 2025, every row: n = 15,030)
- GPS present and inside Arkansas: 15,030/15,030 (100%). Statewide 99.63%.
- Hidden-GPS locator test: **not run**. There is no primary street text a locator can read (the road is coded in the
  road id without spaces), so the California method has nothing to place from. The 1,467 crashes with no GPS
  statewide have no road id either (sampled), so they can't be rescued; they are 0.37% of all crashes.
- House addresses: none in the layer.
- So: placed share = GPS share = 99.63% statewide; within-250 ft accuracy not measured (no independent truth).

## 3. Reader and pack
- `backend/crashiq/sources/ar_ardot.py`: `fetch_contract(box, county_fips, years, cache_dir)` queries the box and
  years, pages by OBJECTID (2000), caches raw JSON per query, returns contract crashes.
- `backend/crashiq/statepacks/ar.py`: `PACK`, status **active**, first year 2021, `final_lag_months=10` (ARDOT posts
  the whole year; at 18 the default window would be 2020-2024 and fail validation, since the layer starts in 2021).
- Severity: CrashSeverity's letter as given. Killed = max(NumFatalities, 1 if K); injured = max(NumSerInj, 1 if
  A/B/C): a floor, said in the pack's data notes. One K crash in Pulaski 2025 had NumFatalities = 0.
- Mode flags: ped (Pedestrian, wheelchair, Skater), bike (Bicyclist, other cyclist), escooter (Scooter),
  motorcycle (MotorcycleRelated), heavy_truck (CMVRelated: commercial vehicle, a proxy).
- Freeway: RoadSystem Interstate or Ramp.
- Tests: `tests/test_source_ar.py` (8 tests) on `tests/fixtures/ar_ardot_acat.json` (51 live rows, 58 KB).

## 4. End-to-end (live, port 8108, 2026-11-08)
S University Ave, W 12th St to Asher Ave, Little Rock (OSM "South University Avenue", 1.55 mi, 3 study
intersections), default window 2021-2025:
- 1,220 rows read, 46 beyond the margin, 0 contract errors, 1,174 kept.
- Counted 263: K 0 · A 3 · B 24 · C 36 · U 0 · O 200 (KSI 3). Excluded 911 (outside buffer 726, outside study
  limits 185: geometry only).
- Crash cost $8,641,000 (ARDOT HSIP Process 2022, App. E, 2020 dollars). 6 findings shown, 0 rejected.
- PDF 36,568 bytes, Excel 34,499 bytes, 102 s. PDF carries the ARDOT notice; no California wording found in it.

## 5. User actions
- Decide whether a paid product may show ARDOT's ACAT data (no licence; ask ARDOT Traffic Safety Section,
  https://ardot.gov/divisions/planning/traffic-safety/, for written permission).
- Optional: ask ARDOT for its statewide average crash rates by roadway type (the Traffic Safety section computes them;
  not published in the HSIP Process document).

## What we didn't check
- Whether the 2025 year is complete (78,083 vs ~81k in other years; dates run to 12-31).
- Accuracy of ARDOT's points against the reports (no independent truth).
- Little Rock open data for a city crash feed (not re-searched today).
