# Washington (WA): crash sources, placement sample, importers (2026-11-07)

Written by Hermes (user 2026-11-07: start the other states). All numbers measured live on 2026-11-07 unless marked.
Machine-readable: `wa-summary.json`; placement output: `wa-placement-2025.json`; methods: `wa-methods.md`.

**Bucket: A\*.** Seattle is **A** (open, licensed for commercial use, points + street names + per-person KABCO).
Statewide WSDOT is **A\***: a public, undocumented JSON endpoint gives every crash with lat/lon and KABCO but no street
names and no licence; the full WSDOT export (street names, offsets, vehicles) is a free emailed request, so
statewide-with-names works as **D** (user brings the export). Readers for all three are built.

## 1. Sources

### 1.1 Seattle: SDOT Collisions All Years (+ Persons, Vehicles), City of Seattle ArcGIS
- Crashes: https://services.arcgis.com/ZOyb2t4B0UYuYNYH/arcgis/rest/services/SDOT_Collisions_All_Years_1/FeatureServer/0
  (catalog: https://data.seattle.gov/dataset/SDOT-Collisions-All-Years/sbqc-3j3m). 263,270 rows; "Daily Refresh";
  latest crash 2026-10-30, last modified 2026-11-05. Feature class SDOT.COLLSN_DET_PT, provided by SPD.
- Persons: `.../SDOT_Collisions_Persons/FeatureServer/0` (560,802 rows); Vehicles:
  `.../SDOT_Collisions_Vehicles/FeatureServer/0` (435,724). Both link on **COLDETKEY**.
- Rows per year (INCDATE): 2004 15,457 · 2010 11,958 · 2015 14,259 · 2019 11,236 · 2020 7,254 · 2021 8,170 ·
  2022 7,681 · 2023 7,369 · 2024 6,464 · **2025 5,763** · 2026 (to Oct 30) 3,575. Full list in the session log;
  every year 2004–2026 is present.
- Columns used: INCKEY, COLDETKEY, REPORTNO, STATUS, ADDRTYPE (I intersection / B block / A alley), INTKEY, LOCATION,
  INCDTTM, PERSONCOUNT, PEDCOUNT, PEDCYLCOUNT, VEHCOUNT, INJURIES (includes SERIOUSINJURIES), SERIOUSINJURIES,
  FATALITIES, JUNCTIONTYPE, ST_COLLISIONTYPE, SDOT_COLDESC, WEATHER, ROADCOND, LIGHTCOND, SOURCE (PTCR police /
  CVCR citizen), MAXSEVERITYCODE/DESC. Persons: ST_INJRY_CLSS(_DESC), ST_PARTCPNT_TYPE_DESC, ST_AGE.
- **Points:** 2025: 5,633 of 5,763 (97.7%) have a point. The point is SDOT's geocode, snapped "at the intersection
  or mid-block of a segment" (layer description), not the officer's GPS.
- **Street names:** 2025: 5,651 (98.1%) have LOCATION: "A AND B" (2,073, 36%) or "A BETWEEN B AND C" (3,578, 62%);
  alleys (112, 2%) have none. Example: `15TH AVE NW BETWEEN NW 85TH ST AND NW 87TH ST`.
- **Severity:** MAXSEVERITYCODE 2025: 1 PDO 3,914 · 2 Injury 1,588 · 3 Serious 221 · 4 Fatal 29 · blank 11
  (older years used 3 / 2b / 2 / 1 / 0). "Injury" doesn't say B or C. Persons give full KABCO: Dead at Scene / Dead
  on Arrival / Died at Hospital (K), Serious (A), Non Serious (Evident) (B), Possible (C), No Injury (O), Unknown.
  Persons exist for STATUS=Matched crashes only (4,343 of 5,763 in 2025).
- **Licence (paid use): OK.** City of Seattle Open Data Policy §E: "An open license on a dataset signifies there are
  no restrictions on copying, publishing, further distributing, modifying or using the data for a noncommercial or
  commercial purpose" (https://www.seattle.gov/documents/Departments/Tech/OpenData/COS_OpenDataPolicy.pdf). Terms of
  Use (https://data.seattle.gov/stories/s/Terms-of-Use/6ukr-wvup/): "Unless otherwise indicated, data on this site
  does not require specific attribution", and "To the extent the data consists of a list of individuals … it is not
  to be used for a commercial purpose." The persons layer (age, gender, injury per person, no names) is the one to
  check against that clause.

### 1.2 Statewide: WSDOT Crash Data Portal (public, no login)
- Portal: https://remoteapps.wsdot.wa.gov/highwaysafety/collision/data/portal/public/ ("10 full years, plus the
  current year"; https://wsdot.wa.gov/about/transportation-data/crash-data).
- The dashboard's own JavaScript calls `Api/CrashDataPortalService/GetPublicPortalData?rptCategory=Summary Reports&
  rptName=Total Crashes&locationType=City|County&locationName=…&reportStartDate=YYYY0101&reportEndDate=YYYY1231`,
  which returns **one JSON row per crash**: ColliRptNum, Jurisdiction (State Route / City Street / County Road /
  Miscellaneous Trafficway), RegionName, CountyName, CityName, FullDate, FullTime, MostSevereInjuryType, AgeGroup,
  InvolvedPersons, CrashStatePlaneX/Y, Latitude, Longitude. **No street names, no crash type, no persons/vehicles.**
- Statewide crashes per year (GetPublicPortalReportableCrashesByMonthAndYear): 2011 98,944 · 2015 117,062 ·
  2019 111,715 · 2020 86,377 · 2021 103,388 · 2022 103,462 · 2023 104,535 · 2024 104,308 · **2025 100,651** ·
  2026 (partial) 69,480. King County 2025: 30,467; Seattle 2025: 7,265.
- **GPS share 100%** in every pull: King County 2025 30,467/30,467, Spokane County 6,283/6,283, Okanogan County
  398/398; Seattle, Tacoma, Spokane, Bellevue, Vancouver cities 2025 all 100%. The row count equals the portal's
  reported total (Seattle 7,265 = 7,265), so no rows are dropped for lacking X/Y.
- Severity (KABCO, most severe per crash): Seattle 2025: No Apparent 4,724 · Suspected Minor 1,101 · Possible 1,006 ·
  Suspected Serious 239 · Unknown 164 · Dead at Scene 17 · Died in Hospital 11 · DOA 3.
- **Licence: unclear.** No licence or terms on the portal; every report page carries the 23 USC 148 / 407 notice. An
  undocumented endpoint behind a dashboard (skill pitfall): it can change, and nothing grants reuse in a paid product.

### 1.3 Statewide with street names: WSDOT export by request
- Request with DOT Form 780-032 (https://wsdot.wa.gov/sites/default/files/2026-04/Crash-Data-Request-Form_0.pdf) to
  crashanalysis@wsdot.wa.gov, or the Public Disclosure Request Center; FAQ: "no restrictions on who can request",
  about 10 days (research_notes/state-research-2026-10-18). Retention 15 full years + current; final each July.
- The layout is public through two republications that load it unchanged:
  - **City of Tacoma, "Vision Zero Crashes (Tacoma)"**
    https://services3.arcgis.com/SCwJH1pD8WSn5T5y/arcgis/rest/services/tacoma_vision_zero_crashes/FeatureServer/14:
    33,068 rows, 2016–2025 (2025: 2,940), limited-access highways removed, "Crash data is obtained from WSDOT".
  - **SRTC (Spokane Regional Transportation Council), "Crash Points 2021–2025"**
    https://services1.arcgis.com/Ub7Rr4y0UspW2NcJ/arcgis/rest/services/Crash_Points_2021_2025/FeatureServer/104:
    33,734 rows for Spokane County, 2021–2026; access info "WSDOT Crash Data and Reporting Branch"; no licence.
- Location columns: JURISDICTION, PRIMARY TRAFFICWAY, BLOCK NUMBER, MILEPOST, A/B, INTERSECTING TRAFFICWAY,
  DIST FROM REF POINT, MI or FT, COMP DIR FROM REF POINT, REFERENCE POINT NAME (+ county-road milepost, ARM for state
  routes). City streets: Tacoma 2025 city-street rows 1,367 primary + intersecting, 1,133 primary + reference point +
  distance + direction (the CCRS secondary + offset shape), 87.8% have a block number. State routes: route code
  (`005FD12892`, `509`) + milepost only.
- Severity: MOST SEVERE INJURY TYPE (KABCO words as the portal) + TOTAL FATALITIES / SERIOUS / MINOR (or EVIDENT) /
  POSSIBLE INJURIES. Vehicles 1–3 and their drivers are columns on the crash row (no separate keyed tables).
- Licence: unclear (WSDOT, §407 on every release). Tacoma's own page: "With no legal restrictions on use or reuse,
  you could really use the data available on Tacoma Open Data for just about anything"
  (https://tacoma.gov/services/tacoma-open-data-maps/), but the data is WSDOT's.

### 1.4 Legal notes
- **23 USC 407 / 148**: safety data "are not subject to discovery or admitted into evidence in a Federal or State
  court proceeding or considered for other purposes in any action for damages" (on every WSDOT release; FAQ
  https://wsdot.wa.gov/sites/default/files/2026-04/Crash-Data-FAQ-s.pdf). The Safety Analysis Guide (2024, printed
  p.9) requires the notice **in the footer of every page, table or graph** of safety analysis.
- **RCW 46.52.080** (https://app.leg.wa.gov/rcw/?cite=46.52.080): accident reports are "for the confidential use of"
  prosecutors, police, Licensing and WSP; officers disclose names, plates, date, time and location only to people
  "who may have a proper interest"; reports can't be used as evidence in a trial arising from the crash. This covers
  the police reports, not WSDOT's coded records; it is why no names or narratives are public.

### 1.5 Other cities
| City | Source | Records | Points | Licence |
|---|---|---|---|---|
| Tacoma | City of Tacoma (WSDOT layout), above | 2016–2025, 33,068 | 100% | "no legal restrictions" (city), WSDOT data |
| Spokane | SRTC (WSDOT layout), above | 2021–2026, 33,734 (county) | 33,731 | none stated |
| Bellevue | Vision Zero Collisions, KSI only https://services1.arcgis.com/EYzEZbDhXZjURPbP/arcgis/rest/services/Vision_Zero_Collisions_-_Serious_Injury_or_Fatality_KSI_view/FeatureServer/0 | 364 (2010-02 to 2025-12); serious injuries "moved near the closest intersections" | not measured | disclaimer only |
| Vancouver | "Motor Vehicle Crashes Summary Data by Year" https://services.arcgis.com/oNvpY90qsPDizwkN/arcgis/rest/services/CrashDataByMonthWSDOT/FeatureServer/0 | 6 summary rows, no records | — | — |
| Any city | WSDOT portal locationType=City | 2025: Seattle 7,265 · Tacoma 4,153 · Spokane 3,275 · Bellevue 2,817 · Vancouver 2,156 | 100% | unclear |

### 1.6 House addresses (NAD)
NAD feature service (https://services.arcgis.com/xOi1kZaI0eWDREZv/ArcGIS/rest/services/Address_Points_from_National_Address_Database_view/FeatureServer/0)
has points in all 9 test boxes (≈0.04° squares): Seattle 3,750 · Tacoma 13,488 · Spokane 3,941 · Vancouver 3,536 ·
Bellevue 2,570 · Yakima 7,843 · Wenatchee 7,354 · Bellingham 3,663 · Okanogan 974. A statewide count timed out (not
measured). Seattle crashes never give a house address (0%). WSDOT's BLOCK NUMBER could use NAD: not measured.

## 2. Placement sample (CrashIQ's own methods, GPS hidden)
Script: `tests/statewide/wa_placement.py` (shared code unchanged). Networks: TIGER/Line 2024 EDGES + FEATNAMES via
`tiger.elements` (King 53033, Pierce 53053), clipped to the city box. Gate = `Gate()` (exact, unique_pair,
freeway_offset auto). Truth = the hidden point. Wilson 95% lower bounds.

### 2.1 Seattle, SDOT 2025, random 2,000 (seed 20261107)
- Points present and inside WA: **1,962 / 2,000 = 98.1%**. Street names: 1,966 (98.3%).
- **Intersections** (714 with point + names): placed 93.6%, **auto 92.4%**, **99.55% within 250 ft** (low 98.7%).
  Tiers: exact 659, unique_pair 1, verified_typo 4, fuzzy 2, near 2, review 46.
- **Block crashes** (1,248), locator as is: placed 85.6%, auto 84.0%, but only **59.4% within 250 ft** (low 56.4%):
  the locator puts `A BETWEEN B AND C` on the corner A & B, SDOT draws it mid-block.
- **Block crashes, middle of A&B and A&C** (wrapper in the script): 1,003 placed (80.4%), auto 78.6%,
  **99.7% within 250 ft** (low 99.1%).
- **Combined** (intersections as is + blocks at mid-block): name-placed 85.2%, **auto 83.6%** (1,641 / 1,962),
  **99.64% within 250 ft** of placed (low 99.22%).
- No-GPS crashes: 38 of 2,000 (1.9%); 34 are alleys with no street text; 4 have names, 3 auto-placed (+0.15%).
  In Seattle names add little coverage (the city already gives points) but they **independently confirm the points**.
- SDOT vs WSDOT on the same report number (2025): 4,171 matched; 81.9% within 250 ft, median 60 ft. WSDOT has 7,265
  Seattle crashes (3,507 on state routes: I-5, SR 99, SR 520…), SDOT 5,763 (city streets, incl. 1,157 citizen
  reports).

### 2.2 Tacoma city streets, WSDOT layout 2025 (all 2,500 with point + names)
- Points 100%; names 99.9% of city-street rows; 1,115 give a distance + direction from a reference street.
- **Placed 95.8%, auto 94.9%, auto within 250 ft 98.3% (low 97.7%).** Tiers: exact 2,092, unique_pair 280, near 10,
  fuzzy 7, relaxed 4, verified_typo 1, review 106. This is the format statewide users would upload.

### 2.3 What broke, and what the shared code would need (not changed here)
1. **Block form "A BETWEEN B AND C"**: `locate.place` needs a third street (block end) and to place at the middle of
   the A&B–A&C block (done in the script; 59% → 99.7% within 250 ft).
2. **"M L KING JR WAY S"** vs TIGER "Martin Luther King Jr Way S": most Seattle intersection reviews (e.g. M L KING
   JR WAY S & S OTHELLO ST). Needs an alias M L KING → MARTIN LUTHER KING in `names`/aliases.
3. **SDOT roadway tags inside names** (BEACON ER AVE S, 62ND E AVE S, 8TH N AVE N, 2ND AV ET S, S INDUSTRIAL WB WAY):
   cleaned in `wa_sdot.clean_street` (source-specific; no shared change needed).
4. **Ramps, bridges, tunnel** ("130TH ST OFF RP", "1ST AV S BR NB", "SR99 TUNNEL SB", "WEST SEATTLE BR WB"): need the
   freeway/ramp logic with WA route names (SR99, I5 written without space).
5. **WSDOT export**: alley references ("ALLEY N OF S 21ST ST"), two names in one field ("S ORCHARD ST    ORCHARD ST
   W"), "AT ALLEY"; state-route rows need WSDOT's LRS (route + SRMP/ARM), not the street locator.
6. Key names: the locator reads `offset_ft` / `offset_dir`; the brief's crash shape says `sec_distance` /
   `sec_direction`. The readers emit `sec_distance` (feet) / `sec_direction`; wiring must map them.

## 3. Importers (not wired)
- `backend/crashiq/sources/wa_sdot.py`: `fetch(year, cache_dir)` (ArcGIS, paged by OBJECTID, crashes + persons),
  `build`, `crash_record`, `person_record`, `split_location`, `clean_street`. Crash severity: city code K/A/U/O; U
  ("injury") becomes B or C when persons say so; the city's code otherwise wins (2025: 790 U→B, 583 U→C; 31 PDO
  crashes with a "possible" person and 15 "injury" crashes with no injured person keep the city's code).
- `backend/crashiq/sources/wa_wsdot.py`: `export_record` (WSDOT export rows: Excel headers with spaces, ArcGIS
  underscores, 31-char truncations), `portal_record` + `fetch_portal(year, "County"|"City", name, cache_dir)`.
  WSDOT "Unknown" injury → U (user decision pending).
- Tests: `tests/test_source_wa.py` (7 tests, offline), fixtures `tests/fixtures/wa/` (70 KB, real 2025 rows).
- **Wiring needs (#19):** register WA sources per road type (city streets: SDOT in Seattle, export elsewhere; state
  routes: portal points or export + LRS); map `sec_distance`/`sec_direction` → `offset_ft`/`offset_dir`; the block
  midpoint; KSI-first findings; WA crash costs and no rate comparisons (see `wa-methods.md`); §407 footer on exports.

## 4. What you need to do
1. Ask WSDOT (crashanalysis@wsdot.wa.gov, 360-570-2420) in writing whether CrashIQ may load the portal records and
   users' requested exports in a paid tool, and what notice to show.
2. Request one export to test the reader: King County, 2025, all roads, "single row flat file", Excel (Form 780-032).
3. Decide how WSDOT "Unknown" injury counts (now U).

## 5. Not checked
County-road and state-route placement (LRS); NAD for block numbers; persons/vehicles for Tacoma beyond the crash row;
Everett, Kent, Yakima, Renton open data; the statewide NAD count; WSDOT's internal (SharePoint) crash costs.
