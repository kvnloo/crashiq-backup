# New Mexico: crash data for CrashIQ (Hermes, 2026-11-08)

Bucket **D statewide (verified)**, but with an open **county** feed: Bernalillo County (Albuquerque), every reported
crash 2020-2024. Pack `status="reader_only"`: it covers 1 of 33 counties and its reuse terms are unclear.

## 1. Statewide: gated (verified live 2026-11-08)
- NMDOT Traffic Records (https://www.dot.nm.gov/traffic-records-system/): "For crash data not already provided through
  UNM, interested parties may submit a data request by using the online data request form."
- UNM-GPS Traffic Research Unit (https://gps.unm.edu/tru/request-traffic-crash-data.html): "*UNM-GPS will not release
  traffic crash data directly to end users.*"
- ArcGIS Online, searched by owner (`owner:nmdot*`, `orgid:hOpd7wfnKm16p9D9` = NMDOT's org, "crash" and "safety"):
  only subsets: `VRU_crashes` (8,868 pedestrian/bicyclist crashes 2013-2023), `I40_Crashes_2016_to_2020`, HSIP network
  screening segments, HIN segments. No all-crash statewide layer. (Consultant copies exist, e.g. `BernCoCrashes2018_2022`
  by TDGmountainwest, `Hive_mockup_data` by Jacobs = dummy data; not agency releases.)
- The 2026-11-02 screen was right for the state; it missed the Albuquerque layer below.

## 2. Bernalillo County: open (the source of the reader)
| | |
|---|---|
| Layer | `Crashes Five Year 2020 - 2024`, item a7af61590f2c40eca4ac2db22f9af17e, owner jfoty_CABQ (City of Albuquerque org CWv1abTnC3urn4bV) |
| URL | https://services.arcgis.com/CWv1abTnC3urn4bV/arcgis/rest/services/Crashes_Five_Year_2020_2024/FeatureServer/0 |
| Description | "location and details of all reported crashes in Bernalillo County between 2020 and 2024 ... compiled by UNM's Geospatial and Population Studies group on behalf of NMDOT ... All data is provided AS IS from UNM/NMDOT and has not been modified." |
| Access | open, no login, `Query` capability, maxRecordCount 2000 |
| Rows | 75,460: 2020 13,916 · 2021 15,687 · 2022 14,774 · 2023 15,554 · 2024 15,529 |
| County | Bernalillo 75,459, Sandoval 1 |
| GPS | LAT/LON (and UTM) on all but 132 (99.8%) |
| Streets | PRIMARY_ST on all but 158; SECONDARY_ST on 86%; LANDMARK + DISTANCE_FROM_LANDMARK + DISTANCE_UNIT (FT/MI) + DIR_LANDMARK |
| Severity | SEVERITY (Fatal 547 / Injury 23,708 / PDO 51,205) + people counts KILLED, CLASSA, CLASSB, CLASSC, INJURED. No injury crash has zero class counts, no fatal crash has KILLED=0 |
| Key | REPORT_NUMBER: 75,456 distinct of 75,460 (4 repeated; the reader keeps the first) |
| Time | DATETIME is a true instant (local 3:43 PM MST arrives as 22:43 UTC); 1,281 rows (1.7%) have DATE but no time |
| Not there | persons, vehicles, road surface, contributing factors (CONTRIBUTING_FACTORS null on 2024) |
| Older years | the same org has `FiveYear_CrashData_2016_2020` and `FiveYear_Combined_2019_2023` (not read) |

Collision type: the old CLASSIFICATION/ANALYSIS pair is "Left Blank" on 95% of 2024 rows; the reader uses the first
harmful event (FHE, FHE_ANALYSIS, FHE_IMPACT: Front-to-Rear → REAR END, Front-to-Side → BROADSIDE, ...) instead.

Column names are a renaming of UNM's crash-level export (data dictionary Feb. 2026, `Database Field =`):
AStreet → PRIMARY_ST, BStreet → SECONDARY_ST, Landmark, Measurement → DISTANCE_FROM_LANDMARK, MeasurementUnit →
DISTANCE_UNIT, DirectionFromLandmark → DIR_LANDMARK, GIS_LAT/GIS_LONG → LAT/LON, Killed/ClassA/ClassB/ClassC/Injured,
UCRnumber → REPORT_NUMBER, Severity, FHE, FHEAnalysis, FHEImpact, Light → LIGHTING, Weather, GIS_Route → ROUTE_NAME,
GIS_Milepost → MILEPOST, PEDinv/PECinv/MCinv/TRKinv → *_INVOLVED. An NMDOT records-request export renamed this way
runs through `nm_cabq.contract_record` unchanged (not tested on a real export).

## 3. Licence for paid use: **unclear**
- Layer: no licenceInfo; description "provided AS IS from UNM/NMDOT".
- City ABQ Data disclaimer (https://www.cabq.gov/abq-data/abq-data-disclaimer-1): derivative applications must show
  "This site provides applications using data that has been modified for use from its original source, www.cabq.gov
  ... It is understood that the data provided at this site is being used at one's own risk." The City "may require a
  user of this data to terminate any and all display, distribution or other use".
- cabq.gov legal page: website content licensed "for non-commercial, personal, or educational purposes only".
- The layer isn't on the ABQ Data catalogue that was checked, and the data is UNM's/NMDOT's, so which terms bind is
  unclear. UNM's dictionary and NMDOT cite 23 U.S.C. 407/409 non-discovery.

## 4. Placement sample (the California way)
`placement_sample.py` → `placement_sample.json`. Bernalillo 2024, read through the reader: 15,528 crashes; GPS 99.93%;
street pair (secondary street or a street landmark) 95.65%. 2,000 random with both names, GPS hidden, TIGER/Line 2024
(35001):
- placed from names 76.4% (exact 1,421, review 472, relaxed 47, verified_typo 27, near 19, unique_pair 8, fuzzy 6)
- default `Gate()`: 0% auto (the network is TIGER-only); `Gate(tiger_only_auto=True)`: 71.5% auto, **91.7% within
  250 ft** (Wilson low 90.2%); all placed: 91.0% (low 89.4%)
- not placed: "no intersection of the two named streets" 435 (interstate + ramp text, `I 25 & AVENIDA CESAR CHAVEZ   SE`
  with runs of spaces, house numbers in the street `6600 ZUNI RD SE`), "streets meet in more than one place" 35
- no-GPS crashes it could add: 11 of 15,528 (9 with a pair). The GPS is already there; this is a cross-check.
- House addresses: not measured (UNM geocodes addresses with the NM E911 roadway basemap; the layer has none).

## 5. End to end (port 8102, NM flipped to active in memory by `serve_active.py`)
Central Ave (US 66 Hist), San Mateo to Louisiana, Albuquerque, 1.06 mi, 14 study intersections, 2020-2024:
1,079 rows read, 0 contract errors, 124 beyond the margin, **955 pulled, 779 counted**, 176 excluded, 0 unplaced.
K 11 / A 18 / B 65 / C 165 / U 0 / O 520. No cost (NMDOT costs unverified). 19 findings. PDF 94,034 B, Excel 39,011 B.
`e2e_result.json`. A first run found 61 crashes with no time dropped as undated; fixed (date from DATE) before this run.

## 6. User actions
1. Ask the City of Albuquerque (jfoty, DMD/Vision Zero GIS) and NMDOT Traffic Records whether a paid tool may load
   the Bernalillo layer, and what notice to show.
2. For the rest of the state: NMDOT crash data request form (https://www.dot.nm.gov/traffic-records-system/), asking
   for the crash-level export (UNM dictionary Feb. 2026) for the counties and years needed; the reader takes it once the
   columns are renamed as in §2.
3. Ask NMDOT HSIP (Jason.Coffey@dot.nm.gov) for its per-level crash costs and dollar year (the AASHTOWare figures are
   only on a vendor page).
4. Decide whether to offer NM as "Albuquerque only" (`status="active"`), knowing other counties show years missing.
