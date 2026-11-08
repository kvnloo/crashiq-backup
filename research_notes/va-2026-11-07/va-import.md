# Virginia (VA): crash sources, placement sample, importer (2026-11-07)

Written by Hermes for the user's "start the other states" request. Every number was measured on 2026-11-07 against
the live source named next to it unless marked otherwise. Methods, rates and costs are in `va-methods.md`.

**Bucket: A\*** — open, record-level, VDOT GPS on 99.995% of crashes, crash-level KABCO, ArcGIS API, no login.
The one catch is the licence: no open licence, and the portal text says VDOT's data files are "for use in performing
the official business of the Commonwealth of Virginia" and binds users to DPPA and DMV dissemination rules. Legal
review before paid use.

## 1. Sources

### 1a. VDOT "Full Crash" (best source; importer built)
- Item: https://www.arcgis.com/home/item.html?id=101101cecac34f28b38c0846e847bd0b (title "Full Crash", item modified
  2026-11-05). Catalog: https://data.virginia.gov/dataset/full-crash (dcat_modified 2026-04-20).
- Layer 0 `CrashData_Basic` (points, 72 fields):
  https://services.arcgis.com/p5v98VHDX9Atv3l7/arcgis/rest/services/Full_Crash/FeatureServer/0 — **1,175,583 rows**.
  Layer 1 `CrashData_Details` (table, 61 fields): same 1,175,583 rows, **one row per crash** (first driver, vehicle,
  passenger, pedestrian and bicyclist only), joined on `DOCUMENT_NBR`.
- Rows per year (CRASH_YEAR): 2017 127,375; 2018 131,848; 2019 128,172; 2020 105,600; 2021 118,498; 2022 122,434;
  2023 127,597; 2024 129,244; 2025 115,858; 2026 68,957 (CRASH_DT max 2026-08-31; "most recent data … preliminary").
  2025 looks short of a full year (VDOT 2024 = 129,244); not explained.
- **Complete, not just the located crashes:** 2024's 129,244 equals DMV's *2024 Virginia Traffic Crash Facts* total
  ("129,244 crashes", https://www.dmv.virginia.gov/sites/default/files/documents/VA-traffic-crash-2024.pdf).
- **GPS:** LAT/LON null on 61 of 1,175,583 (99.995% present); 0 outside Virginia's box. VDOT places crashes on its
  road network (RNS): `RTE_NM`, `RNS_MP` (milepost), `NODE` + `OFFSET` (Richmond 2024: 3,579 of 5,478 have a node).
- **Severity: KABCO.** CRASH_SEVERITY all years: K 7,947; A 56,787; B 238,601; C 102,568; O 769,680. Counts per crash:
  K_PEOPLE, A_PEOPLE, B_PEOPLE, C_PEOPLE, PERSONS_INJURED. On 17,527 Richmond + Fairfax 2024 crashes, the most severe
  count matched CRASH_SEVERITY on every one.
- **Street names:** one free-text field, `ROUTE_OR_STREET_NM` (never empty). No cross-street field. In 2,000-crash
  2024 samples: house-number text ("4300 COMMERCE ROAD", "3700 BLK BELT BLVD") 19.3% Richmond / 4.1% Fairfax; an
  intersection written into the one field ("ARLINGTON BLVD / JAGUAR TRAIL", "RT244/BRADDOCK RD") 1.0% / 19.8%.
  One value is Excel-mangled statewide ("Jan-95", i.e. 1-95).
- Codes are numbers (COLLISION_TYPE "1" …). There's no public code list on the layer; I measured the decode by joining
  16,693 of 18,099 Richmond + Fairfax 2024 crashes to the DMV datathon table (1b), which has the text: every code of
  COLLISION_TYPE, WEATHER, LIGHT, SURFACE, INTERSECTION_TYPE, RELATION_TO_ROADWAY and TRAFFIC_CONTROL_TYPE mapped to
  one text 100% of the time (`code_maps.json`, `xtab.py`).
- Jurisdiction codes (0–339) decode from VDOT's VA_Jurisdictions layer
  (https://services.arcgis.com/p5v98VHDX9Atv3l7/arcgis/rest/services/VA_Jurisdictions/FeatureServer/0): 324 codes;
  only code 141 (867 crashes) is missing. Fairfax County = 29 (FIPS 51059), Richmond City = 127 (51760).
- **Terms** (item description and licenseInfo, quoted): "Per data sharing use agreement with DMV, VDOT publishes the
  non-privileged crash data …"; "under Title 23 United State Code – Section 407, this crash information cannot be used
  in discovery or as evidence …"; "All users shall comply with … (1) the Federal Drivers Privacy Protection Act …
  (2) the Government Data Collection and Dissemination Practices Act … (5) any successor rules … adopted by DMV with
  regard to disclosure or dissemination"; "VDOT's digital data files are for use in performing the official business
  of the Commonwealth of Virginia. VDOT Divisions set all policy on the allowable uses of this data."
  → **licence_paid_use: unclear.** No commercial ban, no grant either; the "official business" line is the risk.

### 1b. DMV "Crash Data and Details" (2025 Datathon tables)
- https://data.virginia.gov/dataset/crash-data-virginia-department-of-motor-vehicles — CSV crash table (246.6 MB,
  2025-03-10), plus vehicle (276.8 MB), driver (157.6 MB), pedestrian/passenger tables and a data dictionary (DOCX).
  Licence field: "License not specified".
- 379,234 crashes, years 2022–2024 only (2022 122,434 = VDOT's 2022 count; 2023 127,596; 2024 129,204). Static.
- GPS 99.998%; `RouteName` 99.99%; **`SecondaryLocation` (cross street) 46.5%** (2024: 61,393 of 129,204), set
  almost only on "At Intersection" crashes. Keys: anonymized `Crash_UID` → `Vehicle_UID` → `Driver_UID`
  (no DOCUMENT_NBR, so no join to 1a except by date/time/GPS).
- Severity: CrashType Fatal / Injury / Property Damage at crash level; person InjuryType per row. Not KABCO at crash
  level.
- Used here only for the street-name placement test and to decode 1a's codes. Not imported (stale, unlicensed).

### 1c. Other state layers
- LRS Road Intersections (node coordinates, "SDE_VDOT_INTERSECTION_W_XY"): https://data.virginia.gov/dataset/lrs-road-intersections
  — would turn `NODE` + `OFFSET` into a point; not tested (GPS is already there).
- VDOT Crash Analysis Tool / Power BI and the "Virginia Crash Map" (item ef9957cd10964a7286d2f9df5b85e833): dashboards
  over the same TREDS data; not a separate download.

### 1d. Address points
- **VGIN Virginia Address Points** (statewide, local-government sourced):
  https://vginmaps.vdem.virginia.gov/arcgis/rest/services/VA_Base_Layers/VA_Address_Points/FeatureServer/0 —
  3,881,020 points; Richmond (FIPS 51760) 92,028; Fairfax (51059) 377,532. Licence: "The VGIN base map vector layers are
  open and public datasets and operate under the Creative Commons Zero (CC0) data license"
  (https://vgin.vdem.virginia.gov/pages/base-mapping). **ok for paid use.**
- NAD feature service: Virginia points exist (150,478 in a Richmond box), but every attribute query returned HTTP 400
  ("Invalid query parameters") — only OBJECTID and geometry come back. VGIN is the better source anyway.

## 2. Major cities

| City | Source | URL | Rows / years | GPS | Notes | Licence |
|---|---|---|---|---|---|---|
| Virginia Beach | VBPD "Police Traffic Crash Reports" | https://services2.arcgis.com/CyVvlIiUfRBmMQuu/arcgis/rest/services/Police_Traffic_Crash_Reports_view/FeatureServer/0 | 14,438; 2023 4,471, 2024 4,537, 2025 3,808, 2026 1,622 (to 2026-10-30) | 0% (table, no geometry) | Main_Street + Nearest_Street (97.9%), CASE_Number; no severity; fewer rows than VDOT has for VB | not specified (unclear) |
| Norfolk | "Traffic Crashes" (Socrata w6gf-9gws), copy of VDOT data | https://data.norfolk.gov/resource/w6gf-9gws.json | 43,760; 2016–2026-05-31 (~4,000/yr) | 100% | document_number, KABCO counts, one street field | not specified (unclear) |
| Arlington | "VDOT_Arlington_Crash_Data_Public", VDOT copy + county fields (INTERSECTION_NAME, HIN) | https://arlgis.arlingtonva.us/arcgis/rest/services/Project_Services/VDOT_Arlington_Crash_Data_Public/FeatureServer/0 | 30,114; 2013–2026 | 99.8% (57 missing) | adds 2013–2016 | not checked |
| Richmond | none found (VDOT only) | — | — | — | — | — |
| Fairfax County | none found (police open-data site has no crash table found) | https://www.fairfaxcounty.gov/police/fcpodabout | — | — | — | — |
| Alexandria | Vision Zero dashboard / viewer only | https://www.alexandriava.gov/VisionZero | — | — | not a download | — |

The city feeds are copies of, or weaker than, VDOT Full Crash; none needs its own importer.

## 3. Placement sample (the California way)

Script: `placement_sample.py` (+ `dmv_scan.py`, `vdot_pull.py`, `vgin_pull.py`); results `placement_sample.json`.
TIGER/Line 2024 EDGES + FEATNAMES for 51760 and 51059 via `tiger.elements` → `osm.Network`; `locate.place`; gate
`locate.Gate()` (auto tiers exact, unique_pair, freeway_offset). 2,000 random 2024 crashes per area (seed 2026).

**A. GPS:** 100.0% present and plausible in both samples (both sources). Statewide 99.995%.

**B. Street-pair locator, GPS hidden** (DMV datathon RouteName + SecondaryLocation):

| | Richmond City | Fairfax County |
|---|---|---|
| crashes with a street pair | 62.7% | 44.7% |
| placed by any tier (of all 2,000) | 59.2% | 35.8% |
| tiers | unique_pair 687, exact 458, verified_typo 23, near 8, relaxed 5, fuzzy 2, review 71 | exact 675, verified_typo 17, near 14, fuzzy 4, unique_pair 4, relaxed 1, review 179 |
| auto-placed under Gate() (of all) | 57.3% (91.3% of pairs) | 34.0% (76.0% of pairs) |
| auto within 250 ft of hidden GPS | 97.5%, Wilson low 96.4% | 95.9%, Wilson low 94.1% |

Caveat: SecondaryLocation looks VDOT-derived from the located point (clean RNS names, no offset), so this is easier
than an officer's text. Both areas fall short of the 98% exact-tier bar; misses are mostly ramps ("I-95 RAMP &
COMMERCE RD", 8,734 ft).

**C. Officer text** (VDOT `ROUTE_OR_STREET_NM`, the only street text in the live source):
- Pair written in the one field, pre-split on "/", "&", " AND ", " AT ": Fairfax 395 crashes (19.8%): auto 44.6% of
  pairs, within 250 ft 83.5% (low 77.3%); Richmond 20 crashes (1.0%): 15 auto, all within 250 ft (low 79.6%).
- House number on VGIN points (`locate.AddressIndex`, tier "address", not an auto tier): Richmond 385 crashes
  (19.3%), 81.0% found, 64.1% within 250 ft (low 58.6%), 78.9% within 400 ft; Fairfax 82 (4.1%), 81.7% found, 64.2%
  within 250 ft, 73.1% within 400 ft. Many reports write a block ("3700 BLK"), so 250 ft is a hard bar.

**D. What it adds:** no-GPS crashes statewide are 61 of 1,175,583. Of those, 2 have a pair in the field
("58E/Southampton Pkwy", "460/GENERAL MAHONE BLVD"), 4 a house number ("1628 SCOTTSVILLE RD") and none a milepost, so
CrashIQ's methods could add **at most 6 crashes (0.0005%)** (not run on these 6). Virginia's
placement problem is solved by VDOT; the locator matters only as a cross-check on VDOT's point.

**What broke and what shared code would need** (no shared code changed):
1. One field for the whole location; pairs need splitting on "/", "&", " AND ", " AT " (Fairfax writes
   "RT 644 / FRANCONIA RD / JAPONICA STREET"). `names`/`locate` would need a pair splitter.
2. Direction and lane words: "SB I 95", "I-495 NORTH EXPRESS", "NB", "FRFX". A bound-word stripper.
3. Route codes: "US-60E", "VA-147W", "SR-7100N", "SC-617S (FAIRFAX COUNTY)", "UR-7538W (CITY OF RICHMOND)",
   "RT244", "I66". The script retried with "US HWY 60" / "STATE RTE 147"; that rescued 122 Richmond and 52 Fairfax.
4. VA abbreviations `names.street_key` doesn't know: "TPIKE"/"TPK" (Turnpike), "HWAY" (Highway), "PKWAY"
   (Parkway). They fell to verified_typo/fuzzy (review) instead of exact.
5. Mile markers in the street field: "SB 95 AT 75MM", "NB 95 AT EXIT 78" → the freeway/milepost path, not the pair
   locator.
6. Cross streets "ACCESS", "ALLEY", "… RAMP", "… SERVICE RD" never match TIGER.
7. Block addresses ("3700 BLK BELT BLVD") are block-level, not a house.

## 4. Importer

`backend/crashiq/sources/va_vdot.py` (standalone, no login): `fetch(where, cache_dir)` pages the Full Crash layer by
OBJECTID (2,000 per page, `User-Agent: CrashIQ/0.1`), caches raw JSON per `where`, and `crash_record()` maps to the
shared keys (`collision_id`, `datetime`, `lat`/`lon` (None outside Virginia, `bad_coords`), `primary_road`,
`secondary_road` = None, `sec_distance`/`sec_direction` = None, `city_name`, `county_code` (VDOT code),
`county_fips`, `killed`, `injured`, `collision_type`, `lighting`, `weather`, `surface`, `is_freeway` (functional
class INT/OFE), `person_kabco` (one entry per K/A/B/C person from the counts), `severity` in KABCUO, plus `route`,
`milepost`, `node`, `node_offset`, mode flags). Fixture `tests/fixtures/va_vdot_full_crash.json` (36 live rows,
60 KB); `tests/test_source_va.py`, 7 tests, offline.

**Wiring needed (issue #19, not done):** register the source in the state pack; pick a `where` per study area
(PHYSICAL_JURIS or a geometry envelope); severity map is already KABCO; person rows come from counts only (Details
has the first person of each kind, not every person); decode tables to the pack; map Virginia's functional class to
CrashIQ's road types; legal notices (407, DPPA) in exports.

## 5. Blockers
- Licence for paid use unclear (1a terms).
- No public cross-street field; person-level detail only for the first driver / passenger / pedestrian.
- 2025 rows look short (115,858 vs 129,244 in 2024).

## 6. What the user must do
- Ask VDOT (Traffic Operations Division, Highway Safety; contact on the item) or DMV Highway Safety Office whether a
  paid engineering tool may use the Virginia Roads Full Crash data, given the "official business of the Commonwealth"
  line and DPPA terms. Ask whether a complete person/vehicle table is available.
- No account or download needed for the data itself.

## 7. Not checked
LRS node join; the Power BI Crash Summary Book; Arlington's and Virginia Beach's portal terms; why 2025 is short;
Details-layer columns beyond the first person; 2017–2023 placement (only 2024 sampled).
