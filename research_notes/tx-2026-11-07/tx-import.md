# Texas import (Hermes, 2026-11-07)

Bucket **B** (free registration). Earlier note: `research_notes/tx-2026-11-02/tx-import-check.md` (verified and
extended here). Machine-readable: `tx-summary.json`; placement numbers: `tx-placement-result.json` (written by
`tx_placement_sample.py`); manuals: `tx-methods.md`. All numbers measured 2026-11-07.

## 1. Sources

### TxDOT CRIS Public Extract (statewide; the source to build on)
- Spec: "2018 and Greater, Public File Extract Specification", dated 06/13/25,
  https://www.txdot.gov/content/dam/docs/division/trf/crash-records/public-extract-file-specification.xlsx (re-downloaded today).
  Files: crash (≈190 columns), unit, person, primaryperson, charges, damages, endorsements, restrictions, lookup.
  `Crash_ID` links all of them. KABCO: `Crash_Sev_ID` / `Prsn_Injry_Sev_ID` 4 K, 1 A, 2 B, 3 C, 5 O, 0 unknown.
- Two location sets on every crash row: officer (`Rpt_Latitude/Longitude`, `Rpt_Street_Pfx/Name/Sfx`, `Rpt_Block_Num`,
  `Rpt_Sec_*` intersecting road, `Rpt_Rdwy_Sys_ID` + `Rpt_Hwy_Num`, `Rpt_Ref_Mark_Nbr`, offset amount + unit + direction
  "from intersection or reference marker") and TxDOT locator (`Latitude/Longitude`, `Located_Fl`, `Hwy_Sys/Nbr/Sfx`,
  `Control/Section/Milepoint`, `Dfo`, `Ref_Mark_Nbr/Displ`, `Street_Name/Nbr`, `_2` equivalents, `Onsys_Fl`), plus
  AADT and road inventory for on-system crashes.
- Access (CRIS Automated Interface User Guide v29, https://www.txdot.gov/content/dam/docs/division/trf/crash-records/automated-interface-guide-for-public-and-standard-extracts-v29.pdf):
  self-register at https://cris.txdot.gov (p. 8–9); crash years 2014 to current (p. 7); a request's end date must be
  within one year of its begin date (p. 18); filter by county/city/agency (p. 17); CSV or XML (p. 16, 21); a
  password-protected zip arrives by email in about 24 h (p. 19–21); accounts unused for 30 days are deleted (p. 8).
- Licence for a paid product: **unclear**. TxDOT says the public extract "is available to the public upon request"
  (https://www.txdot.gov/data-maps/crash-reports-records/crash-data-analysis-statistics.html); release is governed by
  Transportation Code §550.065. No licence or redistribution terms found. Ask TRF (user action).
- Statewide rows per year, GPS share, street-name share: **not measured** (needs the extract).

### Open copies of CRIS data (no login)
| Source | URL | Years | Rows | GPS | Street names | Licence |
|---|---|---|---|---|---|---|
| Dallas County GIS "2025 traffic accidents_no duplicates" (CRIS Query output, one row per crash) | https://services3.arcgis.com/zqe2kwz79KUqUvxC/arcgis/rest/services/2025_traffic_accidents_no_duplicates/FeatureServer/0 | 2025 | 47,628 | 44,066 (92.5%) | primary 100%, + intersecting 18,192 (38.2%) | none stated: unclear |
| Austin "Crash Report Data - Crash Level Records" | https://data.austintexas.gov/d/y2wy-tgr5 | 2010–2026 (latest 2026-10-23) | 2021 13,201; 2022 13,659; 2023 13,035; 2024 12,080; 2025 12,012 | 100% 2021–2026: **filtered to located crashes, not a statewide rate** | `rpt_street_name` 100%, `rpt_block_num` 10,376/12,012 (2025); no cross-street column (`address_display` shows "X & Y" for some) | "Public Domain" in the dataset metadata; terms ask for attribution (https://data.austintexas.gov/stories/s/ranj-cccq): ok with attribution |
| San Antonio SS4A HIN Dashboard Data, Crash Data | https://services.arcgis.com/g1fRTDLeMgspWrYp/arcgis/rest/services/SS4A_HIN_Dashboard_Data/FeatureServer/2 | 2021–2025 | 11,231 / 11,678 / 11,579 / 11,986 / 11,192 (K/A/B/C only, no O) | first 2,000 rows all have geometry; full share not measured | one `street_name` field (locator style, "IH0410") | "open to the public according to the City of San Antonio Open Data Policy", as-is: unclear |
| City of Dallas "DallasCrash2019_events" | https://services2.arcgis.com/rwnOSbfKSwyTBcwN/arcgis/rest/services/DallasCrashData/FeatureServer/0 | 2019 | 40,765 | first 1,000 rows: 943 with geometry | `Rpt_Street_Name` 40,666; `Rpt_Block_Num` 39,217; no cross street | "only for research purposes and not for commercial uses": **no** |
| Houston | data.houstontx.gov (CKAN search crash/accident/collision: nothing), COH GIS https://mycity2.houstontx.gov/gisweb02/rest/services/HoustonMap/Transportation/MapServer | – | – | – | only Vision Zero High Injury Network 2018/2022 segments | – |
| Fort Worth | https://data.fortworthtexas.gov/datasets/cfw-current-traffic-accidents/about | live only | 13 at search time | – | a live 5-minute "current accidents" feed and the HIN layer; no historical table | CC BY 4.0 (hub page) |

Also open, not measured: Midland AllCrashes 2021–2025 (52,177 person-rows), Corpus Christi MPO 2014–Jun 2024
(111,807), Laredo 2015–2020 (36,092), a TxDOT/Toole Pharr-District bike/ped layer that is a raw CRIS extract
(1,566 rows; used only to confirm real value formats: dates `MM/DD/YYYY`, times `02:50 PM`, flags `Y/N`, locator
highways `IH0035`, reported `LOOP 410`, units `M`/`F`).

Dallas County 2025 without GPS (3,562): 3,007 are NON TRAFFICWAY (parking lots, private property: every one of those
lacks GPS); 286 interstate, 134 US/state highway, 68 city street, 63 tollway, 4 county road. On trafficways the GPS
share is 44,066 / 44,621 = 98.8%. This copy keeps unlocated crashes, so unlike Austin it isn't filtered, but it is one
county.

## 2. Placement sample (CrashIQ's own locator)

Dallas County 2025, 2,000 crashes drawn at random (seed 20261107) from the 18,070 that have a primary street, an
intersecting street and GPS. GPS hidden; TIGER/Line 2024 EDGES + FEATNAMES for 48113 through `tiger.elements`;
`locate.place`; `Gate()` (exact, unique_pair, freeway_offset).

| | n | auto-placed | within 250 ft of hidden GPS | Wilson 95% low |
|---|---|---|---|---|
| All | 2,000 | 1,567 (78.4%) | 1,377 / 1,567 (87.9%) | 86.2% |
| City streets | 1,375 | 1,150 (83.6%) | 1,095 (95.2%) | 93.8% |
| US & state highways | 330 | 245 (74.2%) | 183 (74.7%) | 68.9% |
| Interstates | 276 | 170 (61.6%) | 98 (57.6%) | 50.1% |

Tiers: exact 1,508, unique_pair 59, relaxed 11, verified_typo 4, near 3, fuzzy 3, review 412 (268 "no intersection of
the two named streets", 140 "meet in more than one place", 4 relaxed ambiguous).
No-GPS crashes it would add: 122 of the 3,562 have both names; 40 auto-placed = **0.08% of all crashes**. Almost
everything without GPS is a parking-lot crash with nothing to place.

Caveats:
- The "truth" is TxDOT's locator point, which is itself often made from the report's street names (in the raw
  Pharr-District extract 1,354 of 1,566 crashes had no officer GPS), so accuracy partly measures agreement with
  TxDOT's geocoder.
- This copy has no offset distance or at-intersection flag, so mid-block crashes are scored at the corner. The real
  extract has both (`Rpt_Ref_Mark_Offset_Amt`, `At_Intrsct_Fl`); highway numbers should improve with them.
- House addresses: **not measured**. The copy's `Street_Number` is the TxDOT locator's (0 of 3,562 no-GPS crashes have
  one). The extract's officer `Rpt_Block_Num` is a hundred-block. NAD (Texas is a statewide partner): the NAD feature
  service returned HTTP 400 to every query today.

What broke, and the shared-code fixes it needs (wrapped in `tx_placement_sample.py`, shared code untouched):
1. TxDOT highway codes `IH0035E`, `SH0183`, `US0075`, `SL0012`, `SS0348`, `FM1382`, `TL…`: `names.ROUTE` knows none of
   IH/SH/SL/SS/FM/RM/BI/BU/CR/TOLL; rewritten to TIGER's "I- 35 E", "State Hwy 183", "US Hwy 75", "State Loop 12".
2. `street_key("I- 35 E")` and `"I-35W"` both give `I 35`: I-35E and I-35W are different freeways in DFW. ROUTE needs
   the letter suffix.
3. `TLWY` (Dallas North Tollway) is not a suffix; rewritten to TOLLWAY.
4. Placeholders "N/A", "NOT REPORTED", "NO DATA" as street names: dropped.
5. The extract's officer highway when no street is named ("IH 35E" from `Rpt_Rdwy_Sys_ID` + `Rpt_Hwy_Num`) needs (1).
6. Highway crashes need TxDOT reference markers or DFO (control-section-milepoint) placement, the Texas analogue of the
   Caltrans postmile module. Not built.

## 3. Importer (built; login-gated source, so against the spec)
- `backend/crashiq/sources/tx_cris.py`: `read_extract(folder)` reads an unzipped extract folder (any number of yearly
  requests), joins crash + unit + person + primaryperson on `Crash_ID`, decodes collision/light/weather/surface/city/
  county through the lookup file, and returns the shared keys (`collision_id`, `datetime`, `lat`, `lon`,
  `primary_road`, `secondary_road`, `offset_ft`, `offset_dir`, `city_name`, `county_code`, `killed`, `injured`,
  `collision_type`, `lighting`, `weather`, `surface`, `is_freeway`) plus both location sets, per-person KABCO and
  `severity` in KABCUO (U = CRIS "unknown" or injured with no level).
- Fixture `tests/fixtures/tx_cris/` (6 synthetic crashes, ~9 KB) generated by `tests/fixtures/make_tx_cris_fixture.py`
  with the spec's exact headers; `tests/test_source_tx.py` (8 tests, offline, pass).
- Not wired. Wiring needs (#19): register the source in the state pack; Texas `plausible()` bounds; CRIS county numbers
  (1–254 alphabetical, Dallas = 57) to FIPS (48113); names.py Texas routes and I-35E/W; a reference-marker/DFO locator;
  Texas crash costs and rate tables (`tx-methods.md`); NAD registry entries for Texas.
- Guesses to confirm on the first real file: the lookup file's `ColumnName` values (spec doesn't list them), whether
  the CSV time is "14:50:00" or "02:50 PM" (both handled), and the unit/direction short codes (`F`/`FT`, `N`/`NORTH`).

## 4. What the user does (after registering)
See `user_actions` in `tx-summary.json`: Dallas County, CSV, one request per year 2025, 2024, 2023, 2022, 2021; unzip
with the extract password into `~/.hermes/cache/scratch/states/tx/cris/<county>_<year>/`; optional Travis and Harris
2025; email TRF_CRASH@txdot.gov about paid-product use. Then:
`PYTHONPATH=backend ~/Desktop/Crash/.venv/bin/python -c "from crashiq.sources import tx_cris; print(len(tx_cris.read_extract('$HOME/.hermes/cache/scratch/states/tx/cris/dallas_2025')))"`
