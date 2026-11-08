# Oregon (st=or): crash sources, placement sample, importer (2026-11-07)

Written by Hermes for the states brief of 2026-11-07. All numbers measured live on 2026-11-07 unless marked. Scratch
files (not committed): `~/.hermes/cache/scratch/states/or/`.

**Bucket: A\*** — open, record-level, statewide, GPS on ~99%, KABCO per person, crash/vehicle/person tables linked by
`CRASH_ID`, no login. The one catch: **no licence text for paid use** (only a disclaimer that expects re-release).

## 1. Sources

### 1a. ODOT Crash Data System (CDS), statewide, all public roads — the source
Owner: ODOT Crash Analysis & Reporting (CAR) Unit. Page: https://www.oregon.gov/odot/Data/Pages/Crash.aspx
("Ten years of crash data is maintained at all times. Vehicle crashes include those coded for city streets, county
roads and state highways.")

Three open products of the same data:

| Product | URL | What | Years |
|---|---|---|---|
| Decode Database (Access .mdb in a zip) | https://www.oregon.gov/odot/Data/Crash%20Data%20Products/Statewide_Crashes_2024_DecodeDB.zip (19.8 MB, posted 2026-04-07) | CRASH, VHCL, PARTIC, CRASH_KEY_XREF + 40 lookup tables | 2015-2024 one zip per year; plus `Statewide_Crashes_2025_DecodeDB.zip` = *Preliminary Statewide Fatal and Serious Injury Crashes 2025* (3,576 crashes, K and A only) |
| Geodatabase | `…/Statewide_Crashes_2024.gdb.zip` (14.0 MB, 2026-04-08) | crash points | 2015-2024 |
| ArcGIS MapServer layer (OTSDE) | https://gis.odot.state.or.us/arcgis1006/rest/services/agol/OTSDE_Crash/MapServer/0 | crash level, 137 fields, `KABCO`, lat/lon, maxRecordCount 10,000 | 2019-2024 |

File list from the site's own API:
`https://www.oregon.gov/odot/Data/_api/web/GetFolderByServerRelativeUrl('/odot/Data/Crash%20Data%20Products')/Files`.
Spec: Decode-DB-Fields-Formats.xlsx, CDS-ReadMe.pdf, Decode-DB-Introduction.pdf, CDS Code Manual
(https://www.oregon.gov/odot/Data/documents/CDS_Code_Manual.pdf), Crash Data Disclaimers (rev. 4-2026).

**Rows per year (ArcGIS layer, `outStatistics` count by `CRASH_YR_NO`)**: 2019 50,128 · 2020 38,141 · 2021 45,295 ·
2022 45,070 · 2023 46,762 · 2024 48,414 (total 273,810). Latest crash date 2024-12-31. The 2024 decode DB CRASH table
has the same 48,414 rows (PARTIC 96,971, VHCL 87,702; 2 crashes have no PARTIC row).

**GPS**: `UNLOCT_FLG = 0` (located) 2024: 47,832 of 48,414 = **98.8%** (2019-2023: 98.2-98.5%). Unlocated crashes
carry ODOT's *default* coordinate (Default_Unlocateable_Coords.xlsx), which the reader drops. Note: ODOT itself codes
the location from the report (CAR technicians, Code Manual), so the "GPS" is ODOT's geocode, not an officer's GPS.

**Street names** (2024 statewide, layer): `ST_FULL_NM` present on 37,900 (78%), `ISECT_ST_FULL_NM` on 32,888 (68%).
State-highway crashes (22,086 with `HWY_NO`) carry highway number + milepoint (`MP_NO`) instead of / beside names.
Distance from the intersection in feet (`FROM_ISECT_DSTNC_QTY`) and its compass direction (`CMPSS_DIR_CD`, decode DB
only). No house numbers anywhere in the crash record.

**Severity**: KABCO. Layer `KABCO` 2019-2024: K 3,045 · A 14,120 · B 60,627 · C 69,475 · O 126,543
(`HIGHEST_INJ_SVRTY_DESC`: "Fatal Injury (K)", "Suspected Serious Injury (A)", "Suspected Minor Injury Crash (B)",
"Possible Injury Crash (C)", "No Apparent Injury/PDO Crash (O)"). Decode DB `PARTIC.INJ_SVRTY_CD`: 1 K, 2 A, 3 B, 4 C,
9 no apparent injury, 5 died before the crash, 7 no injury age 0-4 (retired). 2024 statewide crash severity computed
from persons: K 489 · A 3,048 · B 12,840 · C 9,409 · O 22,628. **Person-derived severity equals ODOT's crash KABCO on
all 8,874 Multnomah 2024 crashes** (code check, scratch run).

**Keys**: `CRASH_ID` joins CRASH, VHCL (`VHCL_ID`) and PARTIC (`PARTIC_ID`); `CRASH_KEY_XREF` lists all three.

**Access**: open download / open REST, no login, no terms to click.

**Licence for a paid product: unclear.** No licence statement on the page, the files, or the layer
(`copyrightText`: "Geographic Information Services (GIS) Unit, Oregon Department of Transportation (ODOT)"). The
Crash Data Disclaimers PDF (https://www.oregon.gov/odot/Data/documents/Crash_Data_Disclaimers.pdf, rev. 4-2026) says:
"The ODOT CAR Unit releases crash data to local and federal governments, private consultants, engineering firms,
universities, law enforcement agencies, and the public. As a result of this data sharing, ODOT makes no guarantee, and
expressly disclaims liability, regarding the content, usage, and interpretation of crash data re-released by our
customers." Re-release is expected, but nothing grants commercial use. Ask CAR for a written OK
(ODOTTDSCrashRequestGroup@odot.oregon.gov).

Data caveats from the same PDF: Oregon is a **self-reporting state** (ORS 811.720); on average 60% of report packets
2020-2024 had a police report; PDO reporting threshold **$2,500** since 2018-01-01; since 2015 pedestrian/bicycle crashes
are at least "possible injury"; since 2016 PDO vehicle/participant records are limited to two vehicles/drivers.
Release lag: about 15-18 months (2024 data posted April 2026).

### 1b. Major cities
No city publishes its own record-level crash feed; every city layer found is a copy of ODOT CDS:

| City | Source | URL | Notes |
|---|---|---|---|
| Portland | ODOT CDS (PBOT: "ODOT is the custodian of official crash records"; https://www.portland.gov/transportation/vision-zero/vision-zero-dashboard) | — | 2024: 7,182 crashes with `CITY_SECT_NM` Portland*, 135 unlocated (98.1% GPS). City open data has only High Crash Streets / Intersections (network lines, https://www.portlandmaps.com/od/rest/services/COP_OpenData_Transportation/MapServer/1428, /1429) and PBOT `PedestrianFatalCrashes` (102 rows, https://services.arcgis.com/quVN97tn06YNGj9s/arcgis/rest/services/PedestrianFatalCrashes/FeatureServer/0) |
| Portland region | Oregon Metro "Greater Portland 10 Year Crash Data" (ODOT CDS copy, 3 counties) | https://services2.arcgis.com/McQ0OlIABe29rJJy/arcgis/rest/services/Crashes_TenYear_Current_NEW/FeatureServer | item last modified 2022-02-14; stale; no licence |
| Salem | ODOT CDS (2024: 2,585 crashes, 26 unlocated); SKATS COG copy "SKATSCrashes_2024_forOnlineMaps" | https://services2.arcgis.com/89BLPQl3PdPQE7iy/arcgis/rest/services/SKATSCrashes_2024_forOnlineMaps/FeatureServer | copy, not measured |
| Eugene | ODOT CDS (2024: 1,657 crashes, 20 unlocated) | — | no city feed found |
| Bend | ODOT CDS (2024: 1,078 crashes, 2 unlocated) | — | no city feed found (only a consultant's TSAP EPDO layer) |

City counts: `returnCountOnly` on the ODOT layer, `CITY_SECT_NM LIKE '<city>%'`, 2024.

### 1c. Address points
- **Oregon Address Points** (statewide, from the 9-1-1 PSAPs; Oregon DAS/OEM): 1,942,377 points, all 36 counties
  (Multnomah 276,533), https://services8.arcgis.com/8PAo5HGmvRMlF2eU/arcgis/rest/services/Oregon_Address_Points/FeatureServer/0
  (item 36a8e51b74cf4053ae2273f95006fc61, modified 2026-01-16). Licence: "Publicly shared under ORS 276A.509"; GEOHub
  terms (https://geohub.oregon.gov/pages/terms-of-use): "Written release agreements … are not required and will not be
  issued … Use of the data, including for any commercial purpose, must not violate applicable laws"; GEO FAQ: "Is your
  data in the public domain? Yes." → **ok for paid use**.
- OpenAddresses `sources/us/or/` has 57 sources; `statewide.json` points at the same Oregon Address Points layer.
- NAD for Oregon: not measured (the NAD view rejected `State='OR'` queries with HTTP 400 / timed out).
- **Not needed for placement**: ODOT crash records carry no house numbers (0 of the 2,000 sample).

## 2. Placement sample (the California way)

Script: `research_notes/or-2026-11-07/or_placement_sample.py`. Area: Multnomah County (Portland), 2024, decode DB;
2,000 crashes drawn at random (seed 20261107) from the county's 8,874. Network: Census TIGER/Line 2024 EDGES +
FEATNAMES for 41051 via `tiger.elements` (TIGER only, no OSM). GPS hidden; `locate.place` with no aliases, no address
index; ODOT's distance + compass direction passed as `offset_ft` / `offset_dir`.

| Measure | Result |
|---|---|
| Sample | 2,000 of 8,874 Multnomah 2024 crashes |
| GPS present and plausible (located, inside Oregon) | 1,973 of 2,000 (98.7%) |
| Both street names (primary + intersecting) | 1,942 of 2,000 (97.1%) |
| House address in the record | 0 (ODOT has no house-number field) |
| Freeway crashes (FC interstate / freeway) | 480 of 2,000 (24.0%) |

Hidden-GPS test on the 1,941 crashes with GPS and both names (ODOT names pre-split, see below):

| | All | City streets / roads | Freeways |
|---|---|---|---|
| Crashes | 1,941 | 1,492 | 449 |
| Placed from names (any tier) | 1,208 of 1,941 (62.2%) | 1,205 of 1,492 (80.8%) | 3 of 449 (0.7%) |
| Auto-placed under `Gate()` | 1,173 of 1,941 (60.4%) | 1,170 of 1,492 (78.4%) | 3 of 449 (0.7%) |
| Auto-placed within 250 ft of ODOT's point | 1,133 of 1,173 (96.6%), Wilson 95% low 95.4% | 1,130 of 1,170 (96.6%), low 95.4% | 3 of 3 |

Tiers (pre-split): exact 1,172, review 733, relaxed 23, near 5, verified_typo 4, fuzzy 3, unique_pair 1. Exact tier: 1,132 of 1,172 within 250 ft (low 95.4%).
Review reasons: no intersection of the two named streets 710; exact 17; fuzzy 3; relaxed 3.
Raw ODOT names (no pre-split): placed 1,165 of 1,941 (60.0%), auto 1,137 of 1,941 (58.6%), auto within 250 ft 96.7% (low 95.5%).

**No-GPS crashes it would add**: all 156 unlocated Multnomah 2024 crashes (not a sample);
5 have both street names; placed 0
(review: missing street name 151; no intersection of the two named streets 5). **Names add nothing
here**: ODOT already places 98.8% itself, and what it can't place usually names only one road.

Notes:
- `Gate()` on a TIGER-only network: `tiger.elements` doesn't tag ways `crashiq:source=tiger`, so the TIGER-only rule
  (#229) never fires and auto = the exact + unique_pair tiers. With the app's OSM + TIGER union the share may differ.
- The truth is ODOT's own geocode (technicians code the location from the report), not an officer's GPS.
- The exact tier reaches 96.6% (low 95.4%) within 250 ft, below California's 98% bar for auto-placement.
  Not diagnosed; candidates: ODOT measures distance from the intersection along its own road layer; TIGER geometry.
- Freeways (449 of the 1,941 tested, 23%) are not placeable from names: ODOT writes the highway name and ramp codes
  ("BANFIELD FY" + "WB EF 181ST AVE C3", "NB EX JANTZN BCH C1", "EAST PORTLAND FY"), but every state-highway crash has
  `HWY_NO` + `MP_NO`, so a milepoint tier (like the Caltrans postmile tier) is the way.

What broke in the names, and what the shared code would need (`names.py`; pre-split here in the sample script only):
- Slash pairs, one street with two names: "NE 207TH AV/FAIRVW PKWY", "NAITO/FRONT", "MLK/UNION", "39TH AV/CESAR CHAVEZ"
  → split on "/", try each.
- ODOT's 20-character abbreviations: "AV", "FY" (freeway), "BEAV-HILLSDALE HY", "HIST COLUMBIA RVR HY", "FAIRVW",
  "PTLD", "KILWRTH", "JANTZN BCH" → an Oregon alias table.
- Ramp and connection codes in a street field: "<dir> <EX|EN|EF> <name> C<n>" ("SB EX 82/KILWRTH C1"), "… RMP",
  "… N APP" (bridge approach), "COL BLVD-COL WAY CN" → treat as a freeway/ramp reference, not a street.
- Bridges as streets ("HAWTHORNE BRIDGE", "ROSS ISLAND BRIDGE", "SW MOR/BRG ALDER ST RMP") → bridge aliases.
- Cross street without its quadrant ("172ND AVE" for NE 172nd Ave in Gresham) → the relaxed tier already allows it.


## 3. Importer

`backend/crashiq/sources/or_odot.py` (standalone, not wired):
- `read_decode(CRASH.csv, PARTIC.csv)`: the decode DB tables exported to CSV (e.g. `mdb-export <mdb> CRASH`), streamed.
  Every crash with `persons` (KABCO letter per participant) and `severity` in `KABCUO`.
- `fetch_layer(where)`: the OTSDE ArcGIS layer, paged by object id with POST (id lists are too long for GET), crash
  level only (`odot_kabco`, no persons).
- `crash_record(row)`: one CDS CRASH row → the shared crash shape (`crash_id`, `date`, `year`, `hour`, `lat`, `lon`,
  `primary_road`, `secondary_road`, `offset_ft`, `offset_dir`, `city`, `county`, `collision_type`, `killed`, `injured`,
  `lighting`, `weather`, `surface`, `hit_run`, `is_freeway`) plus Oregon's `route`, `highway_no`, `milepoint`,
  `unlocated`. Unlocated crashes get no coordinates. `is_freeway` = functional class 01/02/11/12.
- Tests: `tests/test_source_or.py` (offline), fixture `tests/fixtures/or_odot/` (196 KB: 40 real Multnomah 2024 crashes
  as decode-DB CSV + the recorded layer responses for the same crashes; recorder `tests/fixtures/make_or_odot.py`).
  The test checks the two ODOT products agree crash by crash (severity, date, hour, names, GPS, collision type).

Not done: lighting/weather/surface stay in the decode DB's short codes ("DLIT", "CLR") vs the layer's words
("Daylight", "Clear"); only collision type is mapped to one vocabulary.

### What wiring needs (state-pack seam, #19)
1. A way to read the yearly decode .mdb: either `mdbtools` on the server (`mdb-export`) or a pure-Python reader
   (`access-parser`, used for the scratch export), or the ArcGIS layer per study area (2019-2024 only, no persons).
2. Per-year cache of the 10 decode zips (~20 MB each) and a refresh when ODOT posts a new year (spring).
3. Severity map = `INJ_KABCO`; crash severity from persons (already matches ODOT's KABCO).
4. A milepoint tier for state-highway crashes: ODOT's `HWY_NO` + `MP_NO` against ODOT's LRS/milepoint layer (the
   Oregon equivalent of the Caltrans postmile tier; not built, not measured).
5. Oregon method tables (rates, costs, calibration): see `or-methods.md`.

## 4. Methods
See `or-methods.md` (APM Ch. 4 rates per MEV/MVMT, Crash Rate Table II, critical rate, SPIS, crash costs, HSM
calibration factors, CRF Manual, differences from California).

## What we didn't check
- Licence for paid use of CDS data: no written answer from ODOT.
- NAD coverage of Oregon (query failed); the geodatabase product (not opened; no GDAL here).
- Placement in any county other than Multnomah; placement with OSM + TIGER (the app's union network).
- ODOT's LRS milepoint layer and how many freeway crashes a milepoint tier would place.
- Whether the ArcGIS layer keeps its 2019-2024 window when 2025 is published.
