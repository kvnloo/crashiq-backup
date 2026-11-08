# New York crash data: sources, placement sample, importers (Hermes, 2026-11-07)

Branch `state/ny`. Every number below was queried live on 2026-11-07 (PST) unless marked otherwise; raw outputs are in
`data/` next to this file. Earlier notes: `research_notes/ny-2026-11-02/ny-import-check.md` (verified and extended here).

**Bucket: C** (statewide public table, location only by reference marker) **+ NYC city feed (A) + CLEAR export (D).**

## 1. Sources

### 1a. NYS DMV crash cases, statewide (data.ny.gov `e8ky-4vqe`)
- URL: https://data.ny.gov/resource/e8ky-4vqe.json ; about: https://data.ny.gov/d/e8ky-4vqe. Rows updated 2026-01-21.
  "Four Year Window": 2021–2024 only; max(date) = 2024-12-31 (2025 not posted).
- Rows/year: 2021 372,159 · 2022 390,855 · 2023 381,290 · 2024 380,819.
- Columns: year, accident_descriptor, time, date, day_of_week, police_report, lighting_conditions, municipality,
  collision_type_descriptor, county_name, road_descriptor, weather_conditions, traffic_control_device,
  road_surface_conditions, dot_reference_marker_location, pedestrian_bicyclist_action, event_descriptor,
  number_of_vehicles_involved. **No GPS, no street names, no case number.**
- Reference marker present: 2021 125,089 (33.6%) · 2022 223,354 (57.1%, unexplained spike) · 2023 169,761 (44.5%) ·
  2024 135,683 (35.6%); 2024 in NYC counties 9,488, outside NYC 126,195.
- Severity (crash): accident_descriptor only. 2024: Fatal 1,026; Injury 38,114; Property Damage & Injury 77,122;
  Property Damage 264,557. **Not KABCO**: CrashIQ maps Fatal→K, injury→U, PD→O.
- Persons `ir4y-sesj` (2024 897,323 rows): injury_severity Killed 1,090 / Severe 13,133 / Moderate 20,199 / Minor
  118,066 / Injured with Unkn Severity 7,230 / Uninjured 737,605 (= K/A/B/C/U). Keys: case_individual_id,
  case_vehicle_id; vehicles `xe9x-a24f` share case_vehicle_id. **Neither table has a key back to the case**, so
  person KABCO can't be tied to a crash.
- Licence: OPEN-NY Terms of Use (https://data.ny.gov/api/views/77gx-ii52/files/ef0c1840-ad54-4240-92fd-6397c49fde46?filename=OPEN-NY_20Terms_20of_20Use.pdf):
  "use our government information however you wish, in private sector projects …" and the terms "do not contain
  restrictions requiring members of the public to use attribution". → **ok** for paid use.

### 1b. NYSDOT reference markers (the join)
- https://gisportalny.dot.ny.gov/hostingny/rest/services/Roadways/Roadway/FeatureServer/0 — 185,384 points, public,
  fields Panel, ROUTE_ID, MEASURE, FROM_DATE, TO_DATE. Panel = 12 characters, route right-justified; the crash table
  left-strips it, so `panel = rm.rjust(12)` (`9 84041008` → `  9 84041008`; NYC style `278IX6M13057` already 12).
- Licence: none stated on the layer (no copyright text). Public NYSDOT service; paid use **unclear**.

### 1c. NYC Motor Vehicle Collisions (NYC Open Data `h9gi-nx95` crashes, `f55k-p6yu` persons, `bm4k-52h4` vehicles)
- URL: https://data.cityofnewyork.us/resource/h9gi-nx95.json ; rows updated 2026-11-06; max crash_date 2026-11-03;
  2,303,506 rows since 2012-07-01.
- Per year (plausible GPS = inside 40.4–41.0 N, 73.6–74.3 W):

  | year | crashes | GPS | on + cross street | off-street (house address) | no GPS | no GPS with on+cross | no GPS with address |
  |---|---|---|---|---|---|---|---|
  | 2021 | 110,558 | 91.3% | 46.2% | 26.9% | 9,662 | 4,365 | 1,277 |
  | 2022 | 103,888 | 89.6% | 47.0% | 27.2% | 10,807 | 4,907 | 1,742 |
  | 2023 | 96,608 | 92.1% | 48.5% | 27.7% | 7,591 | 3,413 | 851 |
  | 2024 | 91,316 | 91.7% | 51.6% | 28.3% | 7,619 | 2,514 | 932 |
  | 2025 | 85,559 | 96.9% | 59.5% | 30.8% | 2,641 | 602 | 1,961 |
  | 2026 (to 11-03) | 70,720 | 96.9% | 53.6% | 32.2% | 2,177 | 384 | 1,721 |
- Keys: `collision_id` (now a 32-hex string, e.g. `6acbca94…`) links persons and vehicles. Measured June 2025: 7,486
  crashes, 25,908 persons; 7,450 crashes (99.5%) have person rows, 100% of person rows link, all 3,289 injured crashes
  have an injured person row.
- Severity: persons `person_injury` = Injured / Killed / Unspecified (2025: 49,641 / 229 / 242,255). `complaint`
  (e.g. "Fracture - Distorted - Dislocation" 861, "Severe Bleeding" 223, "Amputation" 15) hints at A-level but is not a
  KABCO field. **Not KABCO** → K / U / O.
- Licence: NYC Open Data FAQ (https://www.nyc.gov/opendata/get-started/FAQs): "Open Data belongs to all New Yorkers.
  There are no restrictions on the use of Open Data." Dataset licence field is blank. → **ok**.

### 1d. CLEAR (NYSDOT) — gated
- Crash Analysis Toolbox (https://www.dot.ny.gov/divisions/operating/osss/highway/crash-analysis-toolbox): CLEAR access
  "is available to State and local government employees and their consultants performing safety analyses"; everyone
  else FOIL. FOIL gives "Crash data exports, Crash level … Excel spreadsheet and GIS shapefile", plus vehicle- and
  person-level exports ("person type, injury severity …"), 2012–present, all public roads.
- No data dictionary is published. The export layout was rebuilt from two NYSDOT exports that are posted publicly:
  the "NYSDOT Accident Data Spreadsheet" (NY DPS case file Appendix 16-B,
  https://documents.dps.ny.gov/public/Common/ViewDoc.aspx?DocRefId=%7BB0793CF9-89AB-415D-AB4E-FC6C77A25F90%7D) and its
  shapefile/DBF form (Town of Gardiner, http://gardinerdems4586.live-website.com/wp-content/uploads/2021/06/Int_Route-44-Route-7.xlsx,
  34 crashes 2015–2019 joined to road inventory and a KABCO column). ALIS "Simple Query Reports"
  (https://www.dot.ny.gov/divisions/operating/osss/highway-repository/SimpleQuery_Reports.pdf) confirms: Comp X/Y in
  **UTM zone 18**, "Number of Serious Injuries ('A')", On Street, Cross Street, Reference Marker.
- Crash fields: Case Num, Case Year, County, Comp Muni, Muni Type, Comp Ref Marker, At Intersection, Comp X, Comp Y,
  Accd Date, Accd Time, Severity (FATAL / INJURY / PROPERTY DAMAGE AND INJURY / PROPERTY DAMAGE / NON-REPORTABLE),
  Num Of Injuries, Num Serious Injuries, Num Of Fatalities, Num Of Vehicles, Accd Type, Collision Type, Traffic Control,
  Light Condition, Weather, Road Surf Cond, Ped Loc, Ped Action, vehicle 1/2 type/direction/factor/age/pre-crash action,
  Day_Of_Week, On Street, Closest Cross Street, Parking Lot Ind.
- KABCO: K and A are counts in the crash row; B/C split only in the person export (layout not seen). Both samples are
  ALIS-era (2015–2019); a CLEAR-era export may rename columns.
- Licence for paid use: CLEAR data goes to agencies' consultants for agency work; using it inside a paid product is a
  question for NYSDOT → **unclear**. FOIL copies are public records.

### 1e. Other cities
| city | source | what it is | years | GPS | licence |
|---|---|---|---|---|---|
| Buffalo | https://data.buffalony.gov/resource/6at3-hpb5.json (Received Traffic Incident Calls) | 911 crash **calls**, not crash reports ("Not every call results …" in the description); accident_type ACCIDENT/INJURY, PROPERTY DAMAGE ONLY, SKYWAY/33/198; address like `PERRY ST @ MICHIGAN AV` or `1209 HERTEL AV` | 2006–2026 (max 2026-11-07); 2025 10,174 rows | 2025 92.3% (9,392) | dataset licence "Public Domain U.S. Government" (USGOV_WORKS) |
| Buffalo | cjvi-pdpv "Accident with Injury by Intersection" | a filtered view of the same calls | — | — | same |
| Rochester | ROC Vision Zero dashboard (https://www.cityofrochester.gov/departments/department-environmental-services-des/roc-vision-zero-dashboard, Oct 2026) | dashboard only; no crash layer on data.cityofrochester.gov or the city's ArcGIS org (services2 yoz1ZtATTCokO9nU) | — | — | not found |
| Syracuse | data.syr.gov | no crash dataset found (searched crash / collision / accident / traffic) | — | — | — |
| Albany | data.albanyny.gov does not resolve; no city crash portal found | — | — | — | — |
Rochester, Syracuse and Albany crashes are in the DMV table (municipality only, plus markers on state highways) and in CLEAR.

### 1f. Address points
- **NYS SAM Address Points** (NYS ITS), statewide, https://nysgeohub.ny.gov/arcgis/rest/services/Address/NYS_Address_Points/MapServer/0
  (Kings 308,540 · Erie 535,294 · Monroe 405,333 · Onondaga 235,002 · Albany 189,399 · New York 63,240 points; NYC
  points come from NYC LION). Licence text is a disclaimer only ("as is", no grant) → paid use **unclear**; NY is a
  USDOT NAD partner, so the same points should be in NAD (public domain).
- **USDOT NAD** feature service (`State='NY'` queries) timed out after ~55 s with HTTP 400 on every query today, so NY
  NAD coverage was **not measured**.

## 2. Placement measured

### 2a. Statewide reference-marker join (`tests/statewide/ny_refmarker_sample.py`)
- Seeded random **500** 2024 crashes with a marker (20 chunks of 25 at random offsets of 135,683): **490 matched
  (98.0%, Wilson 95% low 96.4%)**; **488 of 490 (99.6%, low 98.5%) lie inside the crash's own county** (Census
  cb_2024 county polygons). Unmatched examples: ` 17K83011201`, `155 11011007`, `490I43022091`, `907MX5M14045`.
- Accuracy needs truth the DMV table lacks. NYC check: the 9,488 NYC-county 2024 marker crashes, 8,928 matched (94.1%),
  each linked to the one NYC open-data crash with the same date, minute, severity class and borough: 6,294 unique
  links (905 ambiguous), 5,845 with NYC GPS: **median 5 ft; 83.7% within 250 ft (low 82.8%)**, 90.6% within 528 ft,
  93.3% within 1,320 ft.
- **Caveat:** a 5 ft median means NYPD's published point for these crashes is itself derived from the same marker, so
  this checks the join and the link, not where the crash happened. By design a marker is the nearest 0.1-mi post:
  ±0.05 mi (264 ft) along the route, side and lane unknown, no intersection.
- What it adds statewide: 2024 outside NYC, 126,195 of 291,895 crashes carry a marker; at 98.0% that is about
  123,671 crashes (42.4%) placeable. **The other ~58% outside NYC (local and county roads) have only a municipality.**

### 2b. NYC street-name locator, GPS hidden (`tests/statewide/ny_nyc_locator_sample.py`)
Network: Census TIGER/Line 2024 EDGES+FEATNAMES of the five NYC counties (36005, 36047, 36061, 36081, 36085) via
`tiger.elements`; no OSM. House addresses: NYS SAM points for the five counties (610,074 points fetched for the
house numbers in play). Gate = `locate.Gate()` (auto tiers exact, unique_pair; `address` is not an auto tier).

| sample (seeded 2,000 with GPS) | 2025 citywide | 2024 citywide | 2025 Brooklyn | 2024 Brooklyn |
|---|---|---|---|---|
| exact | 1,146 | 991 | 1,257 | 1,209 |
| address (SAM) | 394 | 408 | 488 | 557 |
| other tiers | 11 | 10 | 9 | 11 |
| review | 449 | 591 | 246 | 223 |
| placed, any tier | 77.5% | 70.5% | 87.7% | 88.8% |
| **auto under Gate()** | **57.4%** | **49.6%** | 63.1% | 60.5% |
| auto within 250 ft of hidden GPS | **99.2% (low 98.5%)** | 99.6% (low 99.0%) | 99.7% (low 99.2%) | 100.0% (low 99.7%) |
| address tier within 250 ft | 98.7% (low 97.1%) | 86.8% (low 83.1%) | 100% (low 99.2%) | 93.9% (low 91.6%) |

- Review reasons 2025 citywide: only one street named (highway crashes: "BELT PARKWAY", "GRAND CENTRAL PARKWAY") 394
  (19.7%); streets don't meet 33; meet in more than one place 14; address not found 7.
- **Crashes with no GPS** (whole year, no truth): 2025: 2,641 → 189 auto (7.2%), 993 address, 1,232 placed by any tier
  (46.6%; 1.44% of all 2025 crashes). 2024: 7,619 → 1,524 auto (20.0%), 593 address, 2,263 placed (29.7%; 2.48% of
  all 2024 crashes).
- Same caveat as 2a: NYPD's GPS for street-pair and address crashes is likely geocoded from those names (NYC LION), so
  99% agreement is agreement with the city's geocoder, not with an officer's GPS.

### 2c. What breaks in the street names (fixes the shared code would need; not made)
1. Bare numbered streets: NYPD writes `E 26 ST`, `4508 2 AVE`, `WEST 28 STREET`; TIGER/SAM write `E 26th St`, `2nd Ave`.
   `names.street_key` keeps `26`, so nothing matches. Wrapped in the script (`ordinals()`); fix belongs in `names.py`.
2. House addresses with padded spaces (`1501      WESTCHESTER AVENUE`): collapsed in `ny_nyc.crash_record`.
3. Highway crashes name only the road (19.7% of 2025 sample): need NY's freeway logic (no reference street).
4. `tiger.elements` leaves ways untagged, so `Gate()` treats TIGER as OSM (`tiger_only_auto` is not applied); a TIGER-only
   network auto-places more than the app would with OSM+TIGER. One bad example: `GRAND CENTRAL PARKWAY | I 678`
   placed 16,897 ft off (exact tier, interchange).
5. `tiger.elements` numbers shape points −1, −2 … per county, so two counties merged into one network share fake node
   ids; the script shifts them per county. A multi-county network in the app needs the same.
6. Reference markers (statewide) are a new location method: panel padding (`rjust(12)`), retired panels (TO_DATE),
   ±0.05 mi along route.

## 3. Importers (standalone, not wired)
- `backend/crashiq/sources/ny_nyc.py` — NYC crashes + persons by date window, cached; KABCUO severity (K/U/O; person
  K/U); house address into `secondary_road` for the address tier; county FIPS from borough.
- `backend/crashiq/sources/ny_dmv.py` — statewide DMV cases + `marker_points()` join (current panel preferred over a
  retired one); `collision_id` = Socrata row id (the table has no case number; regenerated when DMV republishes).
- `backend/crashiq/sources/ny_clear.py` — CLEAR/ALIS crash-level export (CSV/XLSX) reader: column map for both layouts,
  exact-header-first resolution (DBF names collide: `COMP_MUNI` vs `COMP_MUNI_`), UTM 18N → lat/lon (Snyder), KABCUO
  from a KABCO column when present else K/A/U/O from counts, `non_reportable` flag.
- Tests: `tests/test_source_ny.py` (18, offline). Fixtures `tests/fixtures/ny/`: recorded NYC day (40 crashes, 147
  persons), recorded DMV sample (40 cases + marker answer), two synthetic CLEAR exports (spreadsheet, DBF).
- Wiring needed (issue #19): a source registry entry per NY source; `crashes.py` to accept `severity` precomputed and
  `killed/injured = None` (DMV); a marker location provenance (`location_method = reference_marker`, ±264 ft); NYC
  freeway handling; persons → party/IWP shape; ordinals fix in `names.py`; multi-county TIGER ids.

## 4. User actions
1. Get one CLEAR crash-level export (and the person-level one) for one county, one year, from a NYSDOT/agency contact
   or by FOIL (Crash Analysis Toolbox page, "Freedom of Information Law (FOIL) Requests"), so `ny_clear` can be checked
   against a CLEAR-era layout and person KABCO (B/C) can be mapped.
2. Ask NYSDOT (dot.sm.clear@dot.ny.gov) whether CLEAR exports may be used inside a paid tool by a consultant user.
3. Decide whether DMV statewide crashes with only a municipality (≈58% outside NYC) are shown at all (count-only by
   municipality) or left out.

## 5. Not checked
- NAD coverage for NY (service timed out); SAM licence for paid use.
- Accuracy of marker placement against officer GPS (no public truth); the NYC check is agreement only.
- Why 2022 has 57% marker share.
- NYC vehicles table contents; DMV violation table (abfj-y7uq).
- OSM network for NYC (TIGER only).
