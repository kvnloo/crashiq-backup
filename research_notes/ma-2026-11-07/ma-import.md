# Massachusetts: crash sources, placement sample, importer (Hermes, 2026-11-07)

**Bucket: A\*** — open, statewide, record-level, GPS on 95–97% of crashes, KABCO, crash ↔ person ↔ vehicle linked on
`CRASH_NUMB`, ArcGIS REST with no login. **One catch:** the paid-use licence. Closed years 2002–2019 say
"public domain … can be used by anyone for any purpose"; 2020–2026 carry only MassDOT's disclaimer, which also says
open years "should not be used for analysis". Second catch: **Boston is under-reported** in the state data.

All counts below were queried live on 2026-11-07 (PST) by code (`stats.py`, `tests/statewide/ma_placement.py`);
none were computed by hand.

## 1. MassDOT IMPACT open data (statewide)

- Hub: https://massdot-impact-crashes-vhb.opendata.arcgis.com/ (items "2002 Crashes" … "2026 Crashes", search API
  `api/search/v1/collections/all/items?q=crashes`).
- Services (maxRecordCount 2000, query + extract, no token):
  - 2021, 2022, 2024, 2025, 2026: `https://gis.crashdata.dot.mass.gov/arcgis/rest/services/MassDOT/MASSDOT_ODP_OPEN_<year>/FeatureServer` (layers 0 Crash, 1 Vehicle, 2 Person)
  - 2023: `…/MASSDOT_ODP_OPEN_2023v/FeatureServer`
  - 2020: `https://gis.massdot.state.ma.us/arcgis/rest/services/Roads/CrashClosedYears/FeatureServer` (0 Crash, 1 Person, 2 Vehicle)
  - 2002–2019: `https://gis.massdot.state.ma.us/arcgis/rest/services/CrashClosedYear/CrashClosedYear<year>/FeatureServer` (0 Crash, 1 Person, 2 Vehicle). 2015–2017 returned "Unable to complete operation" to statistics queries today; not measured.
- **Reliability:** on 2026-11-07 the open-year server returned 503 for ~10 min (22:50 PST) and, at 23:07, `count = 0`
  for every query on 2025 for some minutes, then recovered. The importer retries; a live pull must check the count.

### Rows per year, GPS, street names (crash layer)

| Year | Crashes | IS_GEOCODED=Yes | LAT/LON inside MA | RDWY named | RDWY + (cross street or house no.) | house no. |
|---|---|---|---|---|---|---|
| 2018 | 142,272 | 95.8% | 95.8% | 99.9% | 55.3% | 47.3% |
| 2019 | 140,939 | 94.8% | 94.4% | 99.9% | 53.8% | 47.1% |
| 2020 | 100,516 | 96.4% | 96.4% | 99.8% | 55.7% | 48.8% |
| 2021 | 125,212 | 95.6% | 95.6% | 99.8% | 57.2% | 47.9% |
| 2022 | 134,472 | 96.5% | 96.5% | 99.8% | 55.6% | 48.3% |
| 2023 | 135,326 | 96.2% | 96.2% | 94.4% | 53.0% | 48.3% |
| 2024 | 135,406 | 96.3% | 96.3% | 91.3% | 54.5% | 49.8% |
| 2025 | 130,896 | 97.3% | 97.3% | 95.9% | 58.6% | 50.7% |
| 2026 (to 2026-11-06 14:49) | 103,495 | 93.1% | 93.0% | 93.5% | 57.7% | 52.2% |

"Cross street" here counts only `NEAR_INT_RDWY`; most intersection crashes write both streets in `RDWY`
("Columbus Ave Rte N  / Dimock St Rte N"), so the real street-pair share is higher (in the sample: 947 pairs + 819
house addresses = 88.3% of 2,000).

### Columns (2025 crash layer, 124 fields)
Key: `CRASH_NUMB` (crash), `RMV_DOC_IDS`, `CRASH_RPT_IDS`. Time: `CRASH_DATE_TEXT` ("12 02 2025"), `CRASH_TIME_2`
("9:51 AM"), `CRASH_DATETIME` (epoch ms, local time stored as UTC; 2020 and earlier `CRASH_DATE`). Location: `LAT`,
`LON`, `X`, `Y` (MA state plane), `IS_GEOCODED`, `GEOCODING_METHOD_NAME` (At Address, At Intersection, Operator
Designated, Mile Marker, Exit Number, Off Intersection, Rotary, Landmark), `RDWY`, `NEAR_INT_RDWY`,
`DIST_DIRC_FROM_INT` ("15 feet N  of"), `STREET_NUMB`, `MM_RTE`/`MILEMARKER`, `EXIT_RTE`/`EXIT_NUMB`, `LANDMARK`,
`CITY_TOWN_NAME`, `CNTY_NAME`, `DISTRICT_NUM`, `RPA_ABBR`. Severity: `MAX_INJR_SVRTY_CL`, `CRASH_SEVERITY_DESCR`,
`NUMB_FATAL_INJR`, `NUMB_NONFATAL_INJR`. Conditions: `MANR_COLL_DESCR`, `AMBNT_LIGHT_DESCR`, `WEATH_COND_DESCR`,
`ROAD_SURF_COND_DESCR`, `RDWY_JNCT_TYPE_DESCR`, `TRAF_CNTRL_DEVC_TYPE_DESCR`, `HIT_RUN_DESCR`,
`NON_MTRST_TYPE_CL`, `VEHC_CONFIG_CL`, `DRVR_CNTRB_CIRC_CL`, … Joined road inventory: `AADT`, `AADT_YEAR`,
`F_CLASS`, `NUM_LANES`, `SPEED_LIM`, `MED_TYPE`, `STREETNAME`, `JURISDICTN`, … No narrative, no diagram.
Person layer adds `PERS_NUMB`, `VEHC_UNIT_NUMB`, `PERS_TYPE`, `INJY_STAT_DESCR`, `AGE`, `SEX_DESCR`, … (2020: 222,919
person rows, 180,320 vehicle rows).

### Severity (KABCO): `MAX_INJR_SVRTY_CL`, 2025
No Apparent Injury (O) 95,263 · Suspected Minor Injury (B) 19,156 · Possible Injury (C) 8,693 · Not reported 3,404 ·
Suspected Serious Injury (A) 2,271 · Unknown 1,262 · Fatal injury (K) 336 · Not Applicable 182 · Reported but invalid 182 ·
null 105 · Deceased not caused by crash 42. Before 2019 the words differ ("Non-fatal injury - Incapacitating" = A,
"- Non-incapacitating" = B, "- Possible" = C, "No injury" = O; 2019 holds both). The importer maps both.
Persons link to crashes completely: all 2,000 sample crashes had person rows (4,493 persons).

### Licence (paid product)
- 2002–2019 (Hub `licenseInfo`, e.g. item 7732a8d84ced44df939a7230ebbd1b78, "2019 Crashes"): "This data is in the
  public domain and therefore can be used by anyone for any purpose. MassDOT shall not be held liable for any errors…"
  → **ok**.
- 2020–2026 (items 2213b771… 2020, d464ead0… 2021, e1a73bbd… 2022, eb133084… 2023, f88f60b5… 2025; 2024 and 2026
  blank): disclaimer only — "MassDOT makes no representation as to the accuracy… not an official record… any crash
  records or data provided for the years after 2020 are subject to change… open years' of crash data are for
  informational purposes only and should not be used for analysis… (see 23 USC, Section 407 [sic; 409])". No grant,
  no restriction on reuse → **unclear**. Ask MassDOT in writing.
- 23 USC 409 applies (not admissible as evidence) — CrashIQ exports should carry the notice.

### Boston is thin in IMPACT
2025: Boston 5,668 crashes (89.4% geocoded) vs Worcester 5,302, Springfield 2,974, Cambridge 1,388; 2019: Boston 4,421 vs
Worcester 5,220. Suffolk county is 7,394 of 130,896 (5.6%) while Middlesex is 26,102. The licence text says "The City
of Boston Police Department may be contacted directly … for crash data pertaining to the City of Boston", and the RSA
Guidelines (Oct 2024, p.5) note "some municipalities may not report all their crashes to the RMV". So Boston studies
need a BPD source.

## 2. Major cities

| City | Source | Rows / year | GPS | Severity | Licence |
|---|---|---|---|---|---|
| Boston | Vision Zero Crash Records, data.boston.gov `e4bfe397-6bfc-49c5-9367-c879fac7401d` (EMS-dispatched crashes) | 2015 4,098 … 2024 3,459, 2025 3,411, 2026 to 10-01 2,641 | 100% | none (mode ped/bike/mv only) | ODC PDDL (public domain) |
| Cambridge | "Police Department Crash Data - Updated" data.cambridgema.gov `gb5w-yva3` (2015–2026-09-30; historical `ybny-g9cv` 2010–2016) | 2024 1,690, 2025 1,605 | 58.1% (2025: 933) | per person, words ≈ KABCO ("SUSPECTED SERIOUS INJURY") for p1/p2 | ODC PDDL |
| Somerville | "Police Data: Crashes" data.somervillema.gov `mtik-28va` (2018–2026-10-04) | 2025 397 | 100% | counts by KABCO class | ODbL (share-alike — check before paid use) |
| Worcester | none found (opendata.worcesterma.gov hub search "crash": only a Vision Zero StoryMap) | — | — | — | use IMPACT (5,302 in 2025, 97.7% GPS) |
| Springfield | none found (springfield-ma.gov/police/data: operator-report form and a dashboard, no records) | — | — | — | use IMPACT (2,974 in 2025, 98.7% GPS) |

Boston VZ has no severity, no crash id link to IMPACT, and only street + cross streets for "Street"-type rows (1,653 of
3,411 in 2025 have street and xstreet1). It's a GPS layer, not a study source.

## 3. Address points
- **MassGIS Master Address Data** (statewide, weekly): FeatureServer
  `https://arcgisserver.digital.mass.gov/arcgisserver/rest/services/AGOL/MassGIS_Master_Address_Points/FeatureServer/0`,
  3,717,497 points, fields incl. `ADDRESS_NUMBER`, `STREET_NAME`, `STR_NAME_BASE`, `GEOGRAPHIC_TOWN`, `POINT_TYPE`.
  Licence (item c33281538f854507a90351760c3468fc): "This GIS web service is a public resource and may be used by anyone
  for their purposes… source credit should be stated as 'MassGIS (Bureau of Geographic Information), Commonwealth of
  Massachusetts EOTSS'" → **ok with attribution**.
  Page: https://www.mass.gov/info-details/massgis-data-master-address-data-statewide-address-points-for-geocoding
- NAD: MA is in the NAD view (first rows State=MA, Barnstable/Bourne; 58,991 points in a Boston box
  −71.10…−71.05, 42.35…42.37). MAD is the better source (it feeds NG911).

## 4. Placement sample (Middlesex 25017, IMPACT 2025, 2,000 random crashes, seed 20251107)

Method: `tests/statewide/ma_placement.py`. Crashes read by the new importer; GPS hidden; street pairs placed by
`locate.place` on a Census TIGER/Line 2024 network (`tiger.elements` on `tl_2024_25017_edges/featnames`) split **per
town** with `tl_2024_25_cousub` (Middlesex has 54 towns, many with their own MAIN ST & SCHOOL ST); house addresses by
`locate.AddressIndex` on MassGIS MAD points of the crash's town and street (138,576 points fetched). Default `Gate()`.

| Measure | Result |
|---|---|
| GPS present and inside MA | 1,970 / 2,000 = **98.5%** |
| Street pair (RDWY "A / B" or NEAR_INT_RDWY) | 947 (47.4%) |
| House address (STREET_NUMB + RDWY) | 819 (41.0%) |
| Neither (freeway mile marker / exit / landmark / blank) | 234 (11.7%) |
| **Street pairs, GPS hidden** (n 946): auto-placed under `Gate()` | 694 = **73.4%** (exact 693, unique_pair 1) |
| …within 250 ft of hidden GPS | 666/694 = **95.97%**, Wilson 95% low **94.2%** |
| Other tiers (suggestions): near 13, relaxed 4, verified_typo 5, fuzzy 3; review 227 | |
| **House addresses, GPS hidden** (n 817): placed on a MAD point | 781 = 95.6% |
| …within 250 ft | **82.6%**, Wilson low **79.8%** |
| All named crashes with GPS (n 1,763): placed automatically | 1,475 = 83.7%, within 250 ft 88.9% (low 87.2%) |
| By MassDOT geocode method — At Intersection (n 607) | auto 87.3%, within 250 ft 98.5% (low 97.1%) |
| — Operator Designated (officer map click; independent truth, n 269) | auto 43.5%, within 250 ft 85.5% (low 78.0%) |
| — At Address (n 842) | auto 94.9%, within 250 ft 82.9% (low 80.1%) |
| No-GPS crashes it would add | 30 without GPS; 27 have no street names; **1 auto-placed = +0.05%** of crashes |

Read: in Massachusetts GPS is already there, so the locator's job is a **second check on MassDOT's own geocode**, not
filling gaps. Caution: for "At Intersection" and "At Address", the hidden GPS was itself produced by MassDOT from the
same names, so agreement there is not independent accuracy. "Operator Designated" is the honest test, and street
pairs there place at 85.5% within 250 ft — below the 98% bar `exact` was approved on in California. Address points
miss 250 ft on rural frontage (MAD point = building centroid; MassDOT's "At Address" point is on the road).

### What broke (shared-code fixes needed; nothing shared was changed)
1. **Intersection in one field**: `RDWY` = "Washington St Rte W  / Lesher St Rte S"; three-way "LANDRY DR / BOSTON POST
   ROAD WEST / GLEN ST". Pre-split in `ma_impact.split_rdwy` (first two kept).
2. **"Rte <route> <heading>" tails**: "Chelsea St Rte 1 E", "MAIN STREET Rte SR28 N", "US1 N Rte". Stripped by the
   importer; `names.street_key` would read "RTE 1" as a route otherwise.
3. **Route in the house-number field**: `STREET_NUMB` "495" on "495 SB", "US1"; importer drops a number that the road
   names.
4. **Ramps and freeways** (most of the 227 reviews): "RAMP-RT 495 SB TO WEST MAIN ST EB", "RAMP-RTS 95 NB/128 NB TO RT 3
   NB", "INTERSTATE 95 NB CD ROAD", "128 NORTH HWY", "ROUTE 16 / ROUTE 93", "I95 S X 60TH". `names` needs MA ramp
   grammar ("RAMP-RT a TO b") and "RTS 95/128" dual routes; `freeway.py` would need MassDOT mile markers (`MM_RTE`,
   `MILEMARKER`) and exit numbers — MassDOT's mile-marker / LRS layer not checked.
5. **Same street, two spellings**: "LEXINGTON STREET / LEXINGTON ST" (a crash on one street); "WEST MAIN STREET / WEST
   MAIN ST" → review "no intersection".
6. **Town scoping**: the locator assumes one city network; MA needs the crash's town (`CITY_TOWN_NAME`) to pick the
   network. The harness does it with TIGER county subdivisions.
7. TIGER ways from `tiger.elements` are not tagged `crashiq:source=tiger`, so `Gate.tiger_only_auto` doesn't apply in
   this sample (TIGER stands in for OSM). With OSM + TIGER as in the app, some placements would become suggestions.

## 5. Importer
`backend/crashiq/sources/ma_impact.py` (not wired). `fetch(year, where, cache_dir)` → crash dicts with the CCRS keys
(`collision_id`, `datetime`, `date`, `hour`, `lat`, `lon`, `primary_road`, `secondary_road`, `sec_distance`/`offset_ft`,
`sec_direction`/`offset_dir`, `house_number`, `city_name`, `county_code`, `killed`, `injured`, `collision_type`,
`lighting`, `weather`, `surface`, `is_freeway`, `ped`, `bike`, `hit_run`, `aadt`, `functional_class`, mile marker /
exit / landmark, `geocode_method`) + `persons` (KABCO each) + `severity` in KABCUO. Pages by object id, 2,000 per
request, `User-Agent: CrashIQ/0.1`, retries 503s. Fixture `tests/fixtures/ma_impact_2025.json` (79 KB, 60 real 2025
Middlesex crashes + 149 persons); `tests/test_source_ma.py` (6 tests, offline).

Wiring needed (issue #19 seam): register the source per state; a town-scoped network choice (`CITY_TOWN_NAME`);
MA street-name rules above; MAD address points in `data/reference/address_points.json` (statewide, one entry); the
MA licence notice and 23 USC 409 text; vehicle layer if heavy-truck / motorcycle flags are needed (not read now;
`VEHC_CONFIG_CL` on the crash row has the vehicle types); a count check against the service before trusting a pull.

## Not checked
Licence for 2020+ beyond the Hub text (no MassDOT answer); 2015–2017 closed-year stats; MassDOT mile-marker layer;
vehicle layer contents; Boston PD data access; Worcester/Springfield beyond a hub search; OSM for MA (TIGER only).
