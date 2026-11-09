# Florida crash data: sources, placement sample, importers (checked 2026-11-07)

**Bucket: D for the statewide located data (Signal Four Analytics), with an A\* open fallback (FLHSMV Crash Facts:
GPS, no street names) and open S4 copies from MPOs/counties (A\*, licence unclear).**

All counts below were measured by code on 2026-11-07 (scripts and outputs in this folder and in
`~/.hermes/cache/scratch/states/fl/`). "Not measured" means not measured.

## 1. Sources

### 1.1 FLHSMV "Crash Facts" aggregated crash data (statewide, open download)
- Page: https://www.flhsmv.gov/crash-facts/ — file "Crash Data Q1 2026": https://www.flhsmv.gov/wp-content/uploads/CrashData%20Q1.zip (261,055,969 bytes, last-modified 11 Jun 2026; one '|'-delimited CSV `CrashFacts_20260611.csv`, 3,300,275,609 bytes). Dictionary: https://www.flhsmv.gov/wp-content/uploads/Automated%20Crash%20Facts%20Report%20Dict.xlsx
- Page text: "updated on a quarterly basis and encompasses the preceding three full years, as well as all completed months within the current calendar year"; "No personally identifying information is included"; numbers "may change between snapshots"; "Normalization typically occurs after 12 months."
- One row per person or vehicle (60 columns): crash part (key, codeable flag, form type, agency type, date-time, county, **lat/long**, road system, intersection type, first harmful event, light/weather/surface, manner of collision, **maximum severity**), vehicle part (key, hit-and-run, body type, maneuver, trafficway, traffic control, CMV, posted speed), person part (key, type, **injury severity**, age, restraint, alcohol/drugs, non-motorist type/location/action).
- Measured (streamed with `profile_flhsmv.py`; 5,806,390 rows, 2,300,506 crashes; latest crash 2026-04-11 23:58):

  | Year | Crashes | With lat/long | In Florida box | Codeable |
  |---|---|---|---|---|
  | 2023 | 717,474 | 513,892 (71.6%) | 512,922 | 395,471 |
  | 2024 | 702,930 | 519,274 (73.9%) | 518,309 | 381,616 |
  | 2025 | 687,313 | 514,659 (74.9%) | 513,807 | 367,029 |
  | 2026 (Jan–Mar + 11 days) | 192,789 | 148,103 (76.8%) | 147,911 | 101,645 |

- Maximum severity, 2025: None 506,336; Possible 93,908; Non-incapacitating 53,156; Incapacitating 10,797; Fatal (within 30 days) 2,771; blank 20,345 (3.0%). KABCO per FDOT's crosswalk (Crash Data Guidance PDF p. 5): Fatal=K, Incapacitating=A, Non-incapacitating=B, Possible=C, None=O.
- Form type (all years): Long 1,533,206; Short 663,683; Update 94,112; Short Form Update 9,505. Road system: Local 745,583; State 423,569; County 358,998; Parking Lot 317,377; Interstate 195,220; U.S. 177,183; Turnpike/Toll 41,230.
- **No street names, no report number.** Only Crash Key (internal). So crashes without lat/long (~25%) cannot be placed by any CrashIQ method, and a crash can't be joined to an S4 export by report number.
- Licence: none stated. The site footer says "© Copyright 2014 – 2026 ... All Rights Reserved" and the disclaimer (https://www.flhsmv.gov/disclaimer/) is a warranty disclaimer only. Florida public-records law (Ch. 119) applies; no explicit grant for paid use. **Verdict: unclear** (likely fine for a public-records dataset; ask FLHSMV in writing).
- Statute: FS 316.066(2)(a) makes reports confidential for 60 days; this file has no personal data and is quarterly, so it doesn't conflict. FDOT's safety data also carry the 23 USC 148(h)(4) / 409 notice (HSIP Guidelines 2021, p. i): data compiled for safety programs "shall not be subject to discovery or admitted into evidence" in damages actions. That limits court use, not product use, but the product should show the notice.

### 1.2 Signal Four Analytics (S4, UF GeoPlan) — FDOT's crash database of record (gated)
- FDOT: "Access: Restricted to authorized users, can be granted for FDOT staff, consultants, governmental agencies and Universities, subject to approval by FDOT" (https://www.fdot.gov/safety/safetyengineering/crash-data-systems-and-mapping). FDOT's 2024 S4 training deck says FLHSMV data "can be shared after 60 days with parties applying for access for 'permissible uses' as defined in 18 U.S. Code s. 2721(b)" (https://fdotwww.blob.core.windows.net/sitefinity/docs/default-source/design/training/transportationsymposium/2024-june/2024nov-thu02-signal4analytics.pdf). Every FDOT safety manual names S4 as the required source (fl-methods.md).
- Export layout: the public **S4 Data Dictionary** (https://signal4analytics.com/assets/files/S4_Data_Dictionary.pdf) lists the Event elements E1–E119 (Report Number, Crash Date and Time, On Street/Road/Highway, Street Address Number, Latitude/Longitude (officer), Feet from Intersection, Direction from Intersection, From Intersection of, Milepost Number, Road System Identifier, S4 Crash Severity / Severity Detail, injury counts by level) and Mapped elements (M5 location type, **M9/M10 S4 Latitude/Longitude** = S4's mapped point), plus Vehicle, Driver, Passenger, Non-Motorist tables keyed by Report Number.
- Severity: E68 detail None / Possible / Non-Incapacitating / Incapacitating / Fatal (within 30 days) / Non-Traffic Fatality ("not reported as fatalities"). → O / C / B / A / K / O.
- **Bucket D.** The reader `fl_s4.py` reads an S4 Event export (CSV) by these names; the same reader reads the open copies below.

### 1.3 Open S4 copies republished by MPOs, counties and cities (ArcGIS, no login)
All have the S4 column names (or close variants). None states a licence; they are S4 data republished by agencies, so paid-product use is **unclear** (the S4 access terms, not the republisher, probably govern). Counts measured with ArcGIS `returnCountOnly`/`outStatistics` on 2026-11-07:

| Layer (owner) | URL | Rows | Years | GPS | Street + cross street | Severity |
|---|---|---|---|---|---|---|
| Signal 4 Crash Events (Palm Beach MPO) | https://services5.arcgis.com/79IoFXBn9ZeqmVlC/arcgis/rest/services/pal_crash_event/FeatureServer/0 | 268,619 | 2019 44,416; 2020 34,564; 2021 44,608; 2022 46,788; 2023 48,890; 2024 49,353 | 100% (S4 point) | 222,048 (82.7%); + house no. 45,721 | detail (KABCO) |
| MetroPlan Orlando Crash Data "2018_2022" (MetroPlan Orlando) | https://services3.arcgis.com/0gEhw9JctymdZD3f/arcgis/rest/services/MetroPlan_Orlando_Crash_Data_2018_2022/FeatureServer/0 | 526,438 | 2018–2025 (2025: 67,507) | 100% | 478,446 (90.9%) | detail |
| Cleaned Crash Data 2014–2024 (City of Orlando GIS user) | https://services5.arcgis.com/mMuoPCaIYD4wEgDl/arcgis/rest/services/Cleaned_Crash_Data_2014_2024/FeatureServer/0 | 113,318 | 2014–2024 (~9–12k/yr) | layer geometry on all; officer LATITUDE 17% | 100,383 (88.6%) | detail |
| Final_Crashes_10172025 (same Orlando user) | https://services5.arcgis.com/mMuoPCaIYD4wEgDl/arcgis/rest/services/Final_Crashes_10172025/FeatureServer/0 | 52,607 | 2020–2024 | geometry; officer 39% | 47,788 | detail |
| Crash_Data_Hillsborough, All_Crashes (Hillsborough County; "Data originated from Signal4 via UF") | https://services.arcgis.com/apTfC6SUmnNfnxuF/arcgis/rest/services/Crash_Data_Hillsborough/FeatureServer/7 | 244,317 | not in a field (item updated 2023-07-19) | 100% | 232,732 | mixed coded labels, 34,475 blank |
| Signal4 Crashes Hillsborough 2020–2024 (HDR consultant account) | https://services.arcgis.com/04HiymDgLlsbhaV4/arcgis/rest/services/Signal4_Crashes_Hillsborough_2020_2024/FeatureServer/1 | 197,798 | 2020–2024 | 70.7% (officer LATITUDE) | 185,196 | simplified (Fatality / Serious / Injury / No Injury) |
| Traffic_Crash_RoadData, Duval/Jacksonville (account "leronev") | https://services1.arcgis.com/NXfNVaFp7QMxnE3j/arcgis/rest/services/Traffic_Crash_RoadData/FeatureServer/0 | 268,198 | 2019–2026 (2025: 37,441) | 99.7% | on-street only (no cross-street field) | simplified |
| KSI Crashes 2019–2023 (Miami-Dade County, "sourced from Signal4") | https://services.arcgis.com/8Pc9XBTAsYuxx9Ny/arcgis/rest/services/KSI_Crash_Events_Public/FeatureServer/0 | 9,468 | 2019–2025 | 99.6% | none | K/A only |
| Serious Injury and Fatal Crashes (City of Tampa) | https://services1.arcgis.com/IbNXlmt2RVVRCZ6M/arcgis/rest/services/Serious_Injury_and_Fatal_Crashes/FeatureServer/0 | 1,497 | 2021–2026 | 100% | on-street only | K/A only |

- Palm Beach MPO layer licence field: "NO WARRANTIES ... The user of this application and data assumes all responsibility" (warranty disclaimer, no grant). Miami-Dade: "provides this data for use 'as is' ... for illustration purposes only". Others: blank.
- The Palm Beach copy has **no report number** (only OBJECTID), so it can't be joined to S4 person/vehicle tables; person KABCO comes from the event's injury counts.
- **No Socrata crash table** was found on any Florida city portal (Socrata discovery API, query "crash", 2026-11-07). FDOT's open-data hub (gis-fdot.opendata.arcgis.com, search "crash") has only old layers: non-motorist KSI 2011–2019, bike/ped typing 2010–2015, 2013/2014 crash-rate layers, CMV crashes 2019–2024 (36,732, injury+ only), District 2 ped/bike 2018–2022.
- FDOT's public `gis.fdot.gov` ArcGIS server (`Crashes_All`, `sso/ssogis`) returned **502 Bad Gateway** on 2026-11-07 (not measured).

## 2. Placement sample (the California way)
- **Sample:** 2,000 crashes drawn at random (seed 20261107) from the 49,353 Palm Beach County 2024 crashes in the Palm Beach MPO S4 layer. Script: `fl_placement_sample.py`; output: `fl_placement_sample.json`. Network: Census TIGER/Line 2024 EDGES + FEATNAMES for county 12099 via `tiger.elements` (one county-wide network). House addresses: Palm Beach County "Situs Addresses" (https://services1.arcgis.com/ZWOoUZbtaYePLlPw/arcgis/rest/services/Situs%20Addresses/FeatureServer/0, 801,871 points, "Public Domain" per OpenAddresses `sources/us/fl/palm_beach.json`); 114,823 points fetched for the 154 streets the sample's house-address crashes name.
- **GPS present and plausible:** 2,000 / 2,000 (100%; S4's mapped point, inside Florida, none 0/0).
- **Street names:** street + cross street 1,643 (82.2%); house number on the street, no cross street, 318 (15.9%); either 1,961 (98.0%). The rest name only a mile marker or one street.
- **S4's point hidden, CrashIQ's locator run:**

  | | Placed | Share of 2,000 |
  |---|---|---|
  | Shared code as is (raw FL names) | 1,124 | 56.2% |
  | With the Florida name pre-split below + house addresses | 1,533 | 76.7% |
  | — exact | 1,131 | 56.6% |
  | — unique_pair | 178 | 8.9% |
  | — address (county address points) | 188 | 9.4% |
  | — relaxed / near / verified_typo / fuzzy | 12 / 7 / 8 / 9 | 1.8% |
  | Review (not placed) | 467 | 23.4% |
  | **Auto-placed under `Gate()`** (exact + unique_pair) | **1,309** | **65.5%** |

  Review reasons: the two streets never meet on TIGER 234; address not on the county list 119; a missing street name (e.g. cross street "MM78") 59; the streets meet in more than one place 55.
- **Accuracy against S4's hidden point (within 250 ft; Wilson 95% lower bound):**
  - all auto-placed: 999 / 1,309 = **76.3%** (low 73.9%); median error of all placed 50 ft.
  - auto-placed, not on a freeway: 990 / 1,084 = **91.3%** (low 89.5%); neither street a freeway, interchange or ramp: 984 / 1,057 = **93.1% (low 91.4%)**.
  - auto-placed on Interstate / Turnpike: 9 / 225 = **4.0%**. Example: "S/B INTERSTATE 95 (STATE ROAD 9)" & "STATE ROAD 806 (ATLANTIC AVE)" lands 1,943 ft from S4's point; freeway crashes are on the mainline between interchanges, and TIGER has no shared node at a grade-separated crossing.
  - by reported offset (auto): none 86.4%; ≤ 250 ft 89.8%; 250–1,000 ft 68.4%; > 1,000 ft 13.6%. The intersection node alone (offset ignored) is within 250 ft 63.7% of the time, so the offset helps.
  - address tier: 135 / 188 = 71.8% (low 65.0%).
  - **Caveat:** the "truth" is S4's mapped point, not independent police GPS. FDOT: Signal Four is "updated within 24 hours of crash occurrence, manual location verification not performed systematically" (Crash Data Guidance v18, PDF p. 5). Some misses are S4's: "LYONS RD" & "STRIBLING WAY", 1,077 ft south, sits 51 ft from the intersection in S4, so S4 didn't apply the offset.
- **No-GPS crashes it would add:** 0 here (S4 maps every crash in this layer). In the FLHSMV open file, 25% of crashes lack GPS but there are no street names, so the locator adds 0. The locator matters for an S4 export without the mapped table (the HDR Hillsborough copy has only the officer's lat/long, 70.7%), and as a check on S4's point.
- **What breaks (fixes the shared code would need; done here in the script only):**
  1. `STATE ROAD 806` / `STATE RD 806` / `ST RD` don't key as `SR 806` (TIGER "State Hwy 806" does; TIGER "State Rd 7" keys as `STATE RD 7`). Normalize both sides.
  2. `CR 809A` vs TIGER "Co Rd 809A" (`CR 809A` ≠ `CO RD 809A`).
  3. Route plus local name in one field: "SR 806 (E ATLANTIC AVE)", "INTERSTATE 95 (STATE ROAD 9)", "W YAMATO RD (SR 794)"; and "STATE ROAD 808 GLADES ROAD" (route, then name). Try each name.
  4. Direction of travel and markers inside names: "I-95 NB", "S/B INTERSTATE 95", "NORTHBOUND", "SR 91 FLORIDAS TPKE SB MM 75", "EXIT 97", cross street "MM78".
  5. Florida's Turnpike spellings ("FLORIDAS TPKE", "FLORIDAS TURNPIKE", "STATE ROAD 91") vs TIGER "Florida's Tpke" / "State Hwy 91".
  6. A pair with the same core ("W ATLANTIC AVE" & "ATLANTIC AVE") was auto-placed as unique_pair 32,626 ft away; it should go to review.
  7. Freeway and interchange crashes need the freeway method (CA's `freeway_offset`, with FDOT RCI route/milepost geometry), not a street pair.
  8. One county-wide network lets a pair resolve in the wrong town (W Lantana Rd & I-95, 41,886 ft off); S4 gives CITY_NAME, so city-bounded networks (as in the CA runs) should help. Not measured.
  9. S4 keeps the house number in its own column (STREET_ADDRESS_NUMBER); the importer composes "1423 N DIXIE HWY" for `_house_address`. The address tier isn't in `Gate().auto_tiers`, so it never auto-places here.
- **NAD:** Florida isn't a statewide NAD partner; the NAD count query for State='FL' failed (HTTP 400, not measured). OpenAddresses lists 75 Florida sources (counties plus cities), e.g. Palm Beach (public domain). Licence per county not checked beyond Palm Beach.


## 3. Importers built (standalone, not wired)
- `backend/crashiq/sources/fl_s4.py`: S4 Event rows → shared crash shape. `read_csv(path)` for a user's S4 export, `read_features(features)` / `fetch_layer(url, where)` for the open ArcGIS copies (paged by object id). Columns matched on letters only across the spellings seen (REPORT_NUMBER / "Report Number", ROAD_SYSTEM_IDENTIFER / IDENTIFIER, 31-character truncations, Hillsborough CamelCase, District 2 "Crash_Street"). GPS: S4 mapped point (M9/M10) first, officer lat/long second, Florida box check, 0/0 = none. Severity: detail → KABCO; simplified "Injury" → U; never milder than the worst injury count. Person KABCO from the injury counts. A house-number report with no cross street becomes `secondary_road = "1423 N DIXIE HWY"`, the form `locate._house_address` reads. ArcGIS dates are read as wall-clock (the Palm Beach layer's earliest value is 2019-01-01 00:15 "UTC").
- `backend/crashiq/sources/fl_flhsmv.py`: streams the Crash Facts zip (no extraction), filters by county/years, groups rows per Crash Key → one crash with person KABCO, killed/injured, hit-and-run, ped/bike, codeable, form type. `severity` is None when every row is blank (3% of crashes).
- Fixtures (`tests/fixtures/fl/`, 216 KB total): 100 recorded Palm Beach 2024 S4 events (trimmed columns), 96 recorded FLHSMV Palm Beach 2025 crashes (233 rows), and a 4-row S4 export CSV built from the dictionary's element names (synthetic: the real S4 CSV header spelling is unverified). `tests/test_source_fl.py`: 7 tests, offline.
- **Wiring needed (issue #19 seam):** register both as FL sources; pick S4 export (user upload) first, open S4 copy for the MPO areas, FLHSMV for GPS-only statewide; a state box for `plausible` (here `fl_s4.FL_LAT/FL_LON`); FL county names→codes; S4 person tables (Driver/Passenger/Non-Motorist by Report Number) if the user's export includes them; road-system "Interstate"/"Turnpike/Toll" → freeway.

## 4. What the user must do
1. **S4 access** (needed for any FDOT-grade Florida study): request an S4 account through an FDOT project manager or District Safety office (FDOT AARF process; https://www.fdot.gov/safety/safetyengineering/crash-data-systems-and-mapping). Then download one sample: **Palm Beach County, 2024, Event table CSV (and the Driver/Passenger/Non-Motorist tables if offered)** so the reader is checked against a real export header.
2. **Licence:** email FLHSMV (Crash Statistics, 850-617-3105) to confirm the Crash Facts file may be shown in a paid product; ask Palm Beach MPO / MetroPlan Orlando whether their S4 layers may be used commercially (or whether S4 terms forbid it).
3. Decide whether Florida starts as "bring your S4 export" only (recommended), or also ships the open MPO copies for Palm Beach / Orlando region.

## 5. Not checked
- FDOT `gis.fdot.gov` crash services (502 on the day). FDOT ssogis currency.
- NAD for Florida: the NAD layer's count query for State='FL' returned HTTP 400 twice; not measured. Palm Beach used the county's own address points instead.
- S4 person tables and the real S4 CSV header; Hillsborough County layer year coverage; the Jacksonville layer's owner (account "leronev", not confirmed as the City).
- Whether the Orlando city layers' geometry is S4's point or the city's own geocode.
