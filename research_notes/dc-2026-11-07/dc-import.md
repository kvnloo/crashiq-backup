# Washington DC (dc): crash sources, placement sample, importer (2026-11-07)

Written by Hermes. Every number below was pulled live on 2026-11-07 unless marked; scripts and raw outputs sit next to
this file (`dc_placement_sample.py`, `placement_sample.json`, `counts_by_year.json`).

**Bucket: A\*** (open, record-level, a point on every crash, person table linked, CC BY 4.0). The one catch: severity is
fatal / major / minor, so KABCO **B and C cannot be told apart**, and there is no collision type, lighting, weather or
road surface.

## 1. Sources

### 1.1 Crashes in DC (DDOT, from MPD's COBALT reports) — the source

| | |
|---|---|
| Crash layer | `https://maps2.dcgis.dc.gov/dcgis/rest/services/DCGIS_DATA/Public_Safety_WebMercator/MapServer/24` (ArcGIS item [70392a096a8e431381f1f692aaa06afd](https://www.arcgis.com/home/item.html?id=70392a096a8e431381f1f692aaa06afd); hub page https://opendata.dc.gov/datasets/DCGIS::crashes-in-dc) |
| Person table | `…/MapServer/25` "Crash Details" (item [70248b73c20f46b0a5ee895fc91d6222](https://www.arcgis.com/home/item.html?id=70248b73c20f46b0a5ee895fc91d6222)) |
| Rows | 356,985 crashes; 906,895 person rows (`returnCountOnly`, 2026-11-07) |
| Key | `CRIMEID` (crash) → many person rows (`CRIMEID`, `PERSONID`, `VEHICLEID`). Layer relationship id 3, one-to-many. `CCN` = MPD report number. On the 2,000-crash sample, 1,989 crashes had person rows (4,319 persons). |
| Access | Open ArcGIS REST, no login, `maxRecordCount` 1000, paged by OBJECTID |
| Updated | Nightly (item `modified` 2026-11-07 08:37 UTC); newest `REPORTDATE` 2026-11-05 15:25 UTC |
| Licence | **CC BY 4.0** on both items' `licenseInfo`: "This work is licensed under a Creative Commons Attribution 4.0 International License." (https://www.arcgis.com/sharing/rest/content/items/70392a096a8e431381f1f692aaa06afd?f=json). The general DC terms (https://dc.gov/page/terms-and-conditions-use-district-data) say CC0 "unless otherwise noted"; these items note CC BY 4.0, so **paid use is OK with attribution** ("District Department of Transportation / Open Data DC"). The 2026-11-02 screen said CC0: corrected here. |

**Columns (crash layer):** CRIMEID, CCN, REPORTDATE, ROUTEID, MEASURE, OFFSET, STREETSEGID, ROADWAYSEGID, FROMDATE,
TODATE, ADDRESS, LATITUDE, LONGITUDE, XCOORD, YCOORD, WARD, EVENTID, MAR_ADDRESS, MAR_SCORE, {MAJOR,MINOR,UNKNOWN}INJURIES_{BICYCLIST,DRIVER,PEDESTRIAN},
FATAL_{BICYCLIST,DRIVER,PEDESTRIAN}, {FATAL,MAJORINJURIES,MINORINJURIES,UNKNOWNINJURIES}{PASSENGER,OTHER}, TOTAL_VEHICLES,
TOTAL_BICYCLES, TOTAL_PEDESTRIANS, PEDESTRIANSIMPAIRED, BICYCLISTSIMPAIRED, DRIVERSIMPAIRED, TOTAL_TAXIS, TOTAL_GOVERNMENT,
SPEEDING_INVOLVED, NEARESTINTROUTEID, NEARESTINTSTREETNAME, OFFINTERSECTION, INTAPPROACHDIRECTION, LOCATIONERROR,
LASTUPDATEDATE, MPDLATITUDE, MPDLONGITUDE, MPDGEOX, MPDGEOY, MAR_ID, BLOCKKEY, SUBBLOCKKEY, CORRIDORID, NEARESTINTKEY, OBJECTID.

**Columns (person table):** CRIMEID, CCN, PERSONID, PERSONTYPE (Driver / Passenger / Other / Pedestrian / Bicyclist),
AGE, FATAL, MAJORINJURY, MINORINJURY (Y/N each), VEHICLEID, INVEHICLETYPE, TICKETISSUED, LICENSEPLATESTATE, IMPAIRED,
SPEEDING.

**Not published:** collision type (manner of collision), lighting, weather, road surface, contributing factor, road
class / freeway flag. DDOT's description lists only what's above.

**Rows per year and location fields** (`REPORTDATE` in UTC; `counts.py` queries, 2026-11-07). "MPD GPS in DC" =
MPDLATITUDE/MPDLONGITUDE inside 38.7–39.1 N, 77.2–76.85 W. 1,748 rows have a `REPORTDATE` before 2008 or missing (min is 1825-11-08).

| Year | Crashes | DDOT point | MPD GPS in DC | ADDRESS given | House-number address | Intersection (A & B) |
|---|---|---|---|---|---|---|
| 2008 | 2,658 | 100.0% | 1.1% | 100.0% | 92.4% | 6.4% |
| 2009 | 12,014 | 100.0% | 18.7% | 100.0% | 87.7% | 16.9% |
| 2010 | 12,141 | 100.0% | 1.2% | 100.0% | 91.2% | 8.6% |
| 2011 | 13,290 | 100.0% | 16.2% | 100.0% | 87.4% | 9.7% |
| 2012 | 16,754 | 100.0% | 59.6% | 100.0% | 83.6% | 16.3% |
| 2013 | 17,482 | 100.0% | 62.2% | 100.0% | 85.2% | 13.8% |
| 2014 | 19,391 | 100.0% | 43.2% | 100.0% | 84.4% | 1.4% |
| 2015 | 22,355 | 100.0% | 69.5% | 100.0% | 79.3% | 14.3% |
| 2016 | 26,572 | 100.0% | 99.7% | 99.9% | 79.1% | 18.2% |
| 2017 | 26,464 | 100.0% | 99.8% | 100.0% | 81.9% | 16.5% |
| 2018 | 26,558 | 100.0% | 99.9% | 99.9% | 82.7% | 15.2% |
| 2019 | 26,788 | 100.0% | 99.9% | 99.9% | 83.3% | 14.4% |
| 2020 | 18,314 | 100.0% | 99.9% | 100.0% | 83.6% | 13.7% |
| 2021 | 21,271 | 100.0% | 99.6% | 100.0% | 88.1% | 8.1% |
| 2022 | 18,906 | 100.0% | 98.6% | 100.0% | 86.2% | 12.3% |
| 2023 | 20,781 | 100.0% | 99.8% | 100.0% | 93.2% | 0.4% |
| 2024 | 20,257 | 100.0% | 99.6% | 100.0% | 93.4% | 0.9% |
| 2025 | 18,175 | 100.0% | 100.0% | 100.0% | 91.6% | 3.3% |
| 2026 (to 11-05) | 15,066 | 100.0% | 100.0% | 100.0% | 87.6% | 10.8% |

"House-number address" counts ADDRESS starting with a digit 1–9; "Intersection" counts ADDRESS containing `&` or ` AND `
(both SQL `LIKE`, so a few overlap). A full 5-year study (2021–2025) has 99,390 crashes.

**Why every crash has a point:** DDOT's wiki (https://ddotwiki.atlassian.net/wiki/spaces/GIS0225/pages/2053603429/Crash+Data,
updated 2025-03-10): "DDOT processes new crash reports each night and creates a mapped point for each crash, provided the
MPD has sufficient location info", and "any crashes that occur in the District on Federal Lands are investigated by the
US Park Police or other agencies, and are not recorded in this MPD crash data." So crashes MPD couldn't locate, and all
Park Police crashes (Rock Creek Pkwy, Suitland Pkwy, Anacostia Park, the Mall's park roads…), are **missing from the
source**, not unplaced. Their count was not measured.

**Severity.** DDOT gives fatal / major / minor (and "unknown" counts on the crash). MPD has coded injuries to MMUCC 4th
edition since COBALT in 2016 ("In 2016, the MPD changed the injury severity level coding in its new crash-reporting
system (COBALT) that captures injury data based on MMUCC 4th Edition", DC FY2022 Highway Safety Plan,
https://www.nhtsa.gov/sites/nhtsa.gov/files/2021-12/dc_fy22_hsp-tag_1.pdf). So fatal = K and major = A (suspected
serious) are exact; "minor" holds both B and C, and DDOT doesn't publish which. 2025 crash-level severity from the reader
on all 18,175 crashes: K 22, A 284, B(=minor) 4,304, U 0, O 13,565. On the sample's persons: FATAL Y 2, MAJORINJURY Y 27,
MINORINJURY Y 629 of 4,319.

**Time.** REPORTDATE is the crash time in UTC: converted to Eastern time, 2025 crashes peak at 15:00–17:00 (1,291 /
1,325 / 1,258) and bottom out at 05:00 (268). FROMDATE is later than REPORTDATE by a median 2.7 h (report entry, not
the crash). 674 of 18,175 (3.7%) sit at exactly local 00:00:00 (vs ~18 expected per minute): treated as "time not given".

**Units.** OFFINTERSECTION is metres: on 655 sample crashes placed at the TIGER intersection of the address street and
NEARESTINTSTREETNAME, distance to DDOT's point ÷ OFFINTERSECTION = 3.28 median (quartiles 3.27 / 3.28 / 3.86).

### 1.2 MAR Address Points (DC Master Address Repository)

`https://maps2.dcgis.dc.gov/dcgis/rest/services/DCGIS_DATA/Location_WebMercator/FeatureServer/0` (item
aa514416aaf74fdc94748f1e56e7cc8a), 144,451 points, fields include ADDRESS_NUMBER, STREET_NAME, STREET_TYPE, QUADRANT,
STATUS, LATITUDE, LONGITUDE. Open, no login. Licence on the item: **CC BY 4.0** ("This work is licensed under a Creative
Commons Attribution 4.0 International License"). 141,186 active points with a number were indexed for the sample.

**NAD:** the NAD view (`…/Address_Points_from_National_Address_Database_view/FeatureServer/0`) answered `where=1=1`
(99,226,272 points) but returned HTTP 400 for every filtered query (`State='DC'`, `County=…`, envelope) on 2026-11-07,
so DC's NAD coverage was **not measured**. MAR is DC's own authoritative list and is what MPD and DDOT geocode against,
so it's the right source anyway.

### 1.3 Other

- City feeds: DC is the city; no separate feed. Copies on arcgis.com by students and Esri staff are derivatives, ignored.
- DC's crash system is called TARAS in the 2025 HSIP report (p. 4); MPD's COBALT is the source system. No public raw
  export beyond the DDOT layers was found.

## 2. Placement sample (2,000 crashes, 2025)

Sample: `random.seed(2025); random.sample(all 18,175 rows reported in 2025, 2000)`. Street network: Census TIGER/Line 2024
EDGES + FEATNAMES for 11001 via `tiger.elements` (1,914 street keys, 11,635 intersections). Address points: MAR (§1.2)
in `locate.AddressIndex`. Gate: `locate.Gate()` (auto tiers exact, unique_pair, freeway_offset). Truth: MPD's own GPS.

| Measure | Result |
|---|---|
| GPS present and inside DC | MPD GPS 2,000 / 2,000 (100%); DDOT point 2,000 / 2,000 |
| ADDRESS form | house number 1,772 (88.6%); street only 152 (7.6%); intersection "A & B" 72 (3.6%); coordinates text 4 |
| Placed from the report's words, GPS hidden | 1,771 (88.6%): address 1,709, exact 56, fuzzy 6; review 229 |
| Auto-placed under `Gate()` | 56 (2.8%), all exact. The address tier isn't in `auto_tiers` |
| Within 250 ft of MPD GPS, all placed | 98.7% (1,748 / 1,771), Wilson 95% low 98.1% |
| — address tier | 98.8%, low 98.1%, median 0 ft (n 1,709) |
| — exact tier | 96.4%, low 87.9%, median 0 ft (n 56) |
| — fuzzy tier | 6 / 6, low 61.0% |
| No-GPS crashes it would add | **0**: 1 of 18,175 2025 crashes lacks MPD GPS; DDOT drops unlocatable crashes before publishing |

**The accuracy number is circular. Don't count it as proof.** 1,548 of 1,709 address placements (90.6%) land within 5 ft
of MPD's GPS, and 57 of 62 intersection placements within 30 ft. MPD's "GPS" is the MAR geocode of the typed address,
not a field fix. So the test shows CrashIQ reproduces MPD's point from the words (it reads DC's formats correctly).
It does not show the point is where the crash happened. DDOT's own snapped point sits a median 60 ft (p90 97 ft) from
MPD's.

**Street-only crashes (152, 7.6%)** are mostly freeways and circles ("INTERSTATE 695 INTERSTATE BN", "COLUMBUS CIRCLE
NE"). They have no cross street and go to review, but they still have a point.

**Secondary test, not independent:** address street × DDOT's NEARESTINTSTREETNAME (which DDOT derives from its own
point) on 1,566 crashes: exact 1,318, near 21, relaxed 3, verified_typo 1, review 223. Without applying the offset, 78.5%
land within 250 ft (low 76.2%, median 139 ft). This only shows TIGER and DDOT's street names line up.

### What broke in the shared code (fixed in the script, not in shared files)

1. **Quadrants.** `names.street_key("U STREET NW")` → core `U STREET NW`, suffix None; TIGER's `U St NW` → `U ST NW`.
   The trailing NW/NE/SW/SE hides the suffix, so ST ≠ STREET and nothing matches. The script moves the quadrant before
   the suffix (`U NW STREET` → core `U NW`, suffix ST) on both the crash and the TIGER names. Shared fix: treat a trailing
   quadrant as part of the name (never drop it: K St NW and K St SE are different streets).
2. **Lettered streets.** `street_key("N NW ST")` → core `NORTH NW` with a leading direction N. It matches only because both
   sides go through the same function. DC has N, S, E, W (and NW/NE…) Streets. Shared fix: a single letter followed by
   a quadrant is a street name, not a direction.
3. **House reader.** For 63 of 1,772 house addresses, `locate.place(…, addresses=…)` didn't return the address tier
   the direct `AddressIndex.lookup` gave, so the script calls the lookup itself.
4. **Intersection in one field.** "FLORIDA AVENUE NE & NEW YORK AVENUE NE\nWASHINGTON," has to be split on `&` and the
   city line dropped. The reader does that.
5. **Half addresses.** "16461/2 NEW JERSEY AVENUE NW" means 1646½. The reader parses it as 1646.
6. **Diagonal approach directions.** INTAPPROACHDIRECTION is Northwest / Southeast etc.; `locate.offset` only knows N/E/S/W.
7. **Address tier gate.** House addresses are 85% of DC crashes; the address tier would need the user's decision to
   auto-place, the same way NAD did in California (but see the circularity caveat).

## 3. Importer

`backend/crashiq/sources/dc_crashes.py`, standalone, stdlib only. `fetch(year)` pages the crash layer by OBJECTID and
pulls persons by `CRIMEID IN (…)` in batches of 100. `records(crash_rows, person_rows)` gives the shared crash shape:
`collision_id, report_number, datetime, date, year, hour, lat, lon, location_source (police_gps | ddot_geocode),
bad_coords, address, address_form, house_number, primary_road, secondary_road, secondary_from_ddot, sec_distance (ft),
sec_direction, city_name, county_code (11001), ward, killed, injured, collision_type/lighting/weather/surface (None),
is_freeway (by name), ped, bike, vehicles, speeding, impaired, persons[{person_id, vehicle_id, person_type, age,
vehicle_type, kabco, ticket, impaired, speeding}], severity (KABCUO)`.

- Test: `tests/test_source_dc.py` (7 tests, offline) on `tests/fixtures/dc_crashes_2025.json` (95 real 2025 crashes,
  204 persons, 214 KB).
- For a house address, the cross street is DDOT's derived nearest intersecting street (`secondary_from_ddot` = True).
- **Wiring the app needs** (issue #19, not done here): a state-pack entry for DC (source, attribution line "District
  Department of Transportation / Open Data DC, CC BY 4.0"); the quadrant and lettered-street fixes in `names.py`
  (§2); a severity map decision for "minor" (B, or a B/C class); hiding collision type / lighting / weather / surface
  tables for DC; `county_code` 11001 in place of CCRS county numbers; a freeway flag better than the name regex
  (DDOT route class via ROUTEID); and a note that Park Police crashes are absent.

## Blockers / caveats
- Severity B and C are merged ("minor"). KSI, fatal and serious-injury counts are exact; B/C splits and the costs
  built on them are not.
- No collision type, lighting, weather, surface or contributing factor: the corridor study's pattern tables (rear-end,
  night, wet) can't be filled for DC.
- Federal-land (US Park Police) crashes aren't in the data.
- Placement accuracy can't be checked independently: MPD's GPS is the geocoded address.

## Not measured
NAD coverage for DC (service rejected filters); the count of crashes DDOT drops as unlocatable; the share of Park
Police crashes; FARS comparison (2025 MPD layer has 22 deaths).
