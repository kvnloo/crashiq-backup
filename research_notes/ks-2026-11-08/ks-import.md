# Kansas: statewide crash data for CrashIQ (Hermes, 2026-11-08)

Bucket (verified live): **A\*** — open, record-level, GPS on every published row, KABCO from per-crash counts; the catch is the licence (no open grant) and no street names.
The 2026-11-02 screen called it A; it was right on access and GPS, but it missed that the layer has no street fields.

## 1. Source: KDOT "Crashes in Kansas" (KanPlan ArcGIS)
- Layer: https://kanplan.ksdot.gov/arcgis_web_adaptor/rest/services/Transportation/Accidents/FeatureServer/0 (item https://www.arcgis.com/home/item.html?id=b79862ee9eaa46fa87d8afb8191b3834, owner KanDOT). No login. maxRecordCount 25,000.
- 607,257 rows on 2026-11-08; latest crash 2026-10-29. Rows per year (`ACC_YEAR`): 2016 62,899 · 2017 61,170 · 2018 63,422 · 2019 63,363 · 2020 50,523 · 2021 54,574 · 2022 56,122 · 2023 56,826 · 2024 55,685 · 2025 55,827 · 2026 26,366 (partial) · no date 480.
- **Only located crashes are published** (item snippet: "Crashes are shown only when the crash location could be estimated"). Against KDOT's own totals: 2023 56,826 of 59,865 (94.9%, 2023 Crash Facts p. 1 summary); 2024 55,685 of 61,495 (90.6%, NHTSA Kansas FY25 Annual Report). The rest need an open-records request.
- GPS: 607,257 of 607,257 have `LATITUDE`/`LONGITUDE` inside Kansas (0 null/zero, 0 outside 36.9–40.1 N, 94.5–102.1 W). Point source: `KHUB_LAT` 417,112, `DASC_LAT` 190,145.
- Street names: **none**. No street, cross street, address or milepost field. `ON_ROAD_TYPE` (Local Route 388,820 · US Highway 90,305 · Interstate 72,509 · State Highway 52,336 · other/blank 3,287), `STATE_SYSTEM_IND` (Y 223,867 / N 383,390), `TURNPIKE_INVOLVED` (Y 4,900).
- Severity: `ACC_SEVERITY` FATAL 3,851 / INJURY 136,663 / PDO 466,743; per-crash counts `FATALITIES` (K), `DISABLING_INJURIES` (A), `NON_INCAPACITATING_INJURIES` (B), `POSSIBLE_INJURIES` (C). `MOST_SERIOUS_INJURY` F/D/I/P/N/U. Checked: every INJURY crash has a D, I or P person, and every crash with all four counts 0 is PDO, so the reader's KABCO from the counts agrees with KDOT on all rows (no U needed in practice).
- Other fields used: date parts, `ACC_HOUR`, `ACC_COUNTY` (all 105 names match the Census county names), `ACC_CITY`, `CWOV_FHE_ACC_TYPE` (manner of vehicle-vehicle collision), `ACCIDENT_CLASS_FHE_DESC`, light, weather, ped/bike/motorcycle/large-truck flags, speed limit, `REPORT_IMAGE_LINK`.
- Not in the layer: person and vehicle tables (no road-user movements), surface condition (only rain/snow flags), cause codes (only circumstance flags such as speed, alcohol, distraction, which the reader doesn't map yet).
- Key: `ACCIDENT_KEY` (e.g. `20240115231`), one row per crash.

### Licence
- Item `licenseInfo`, quoted: "This material may be protected from discovery and admission into evidence in litigation pursuant to 23 USC 407. KDOT is not responsible for the accuracy of crash data contained in crash reports. KDOT makes no warranties … Further Terms of Use can be reviewed at: KDOT Website Terms of Use Policy".
- KDOT Website Terms of Use (updated 2024-05-09, https://www.ksdot.gov/about/publications-and-reports/kdot-website-terms-of-use), quoted: "You may not reproduce, distribute, or use any content from this website without explicit permission from KDOT." and "Any person … who reuses, publishes, or communicates the information available from this website shall be solely liable …".
- Verdict for paid use: **unclear, leaning no without KDOT's written OK** (the terms are written for the website; the layer points to them).

## 2. Placement sample (Wichita, 2024)
- 2,000 random Wichita 2024 crashes (of 8,853): GPS present and plausible 2,000 (100%). Source `KHUB` 1,855 / `DASC` 145. Road type: Local 1,670, Interstate 154, US 99, State 75, Ramp 2.
- Points pile at intersections: the busiest point holds 38 crashes in the year; 611 of 8,853 (6.9%) sit on points with 10 or more crashes, so KDOT snaps many crashes to an intersection node.
- **Name placement can't be tested**: the layer has no street names, so there is nothing to place with TIGER and no hidden-GPS check. Not measured: within-250 ft accuracy.
- What CrashIQ's methods would add: nothing from this layer (every published row already has a point; the ~5–9% unlocated crashes aren't published at all).
- House addresses: n/a for the same reason (no address text).

## 3. City feed (recorded, not used)
- Wichita "Traffic Accidents" (https://gismaps.wichita.gov/ageweb/rest/services/OpenData/TrafficAccidents/FeatureServer, yearly layers 2018–2026): 11,210 rows in 2024 with GPS, `LOCATION`, `CROSS_STREET`, `INTERSECTION`, offence text; **no severity and no KDOT key**, so it can't fill KDOT's gaps (can't be joined or counted by KABCO). No licence text on the layer. Not used.

## 4. Reader and pack
- `backend/crashiq/sources/ks_kdot.py` (`fetch_contract`): box + years query, paged by OBJECTID (2,000), raw JSON cache per query. KABCO from counts; Interstate, ramp and Turnpike crashes are freeway. CCRS words for collision type and light.
- `backend/crashiq/statepacks/ks.py`: `status="active"`, first year 2016, KDOT notice as `legal`.
- Tests: `tests/test_source_ks.py` on `tests/fixtures/ks_kdot_crashes.json` (35 live rows, 28 KB).

## 5. End-to-end (live, port 8107, 2026-11-08)
N Rock Rd, Wichita, Central Ave to 13th St N (1.01 mi, 10 study intersections), 2020–2024:
- pulled 390 rows, 2 beyond the margin, 388 kept, 0 contract errors; **counted 233** (155 outside the study area).
- K/A/B/C/U/O = 1/1/26/46/0/159; KSI 2.
- Cost: none (KDOT costs per person, see methods). 9 findings shown, 0 rejected.
- PDF 47.5 KB, Excel 35.7 KB, 141 s (one Overpass 502 retry). Raw result: `e2e_result.json`.

## What we didn't check
- Whether the freeway rule misses Wichita's freeway-built US/K routes (Kellogg US-54, K-96): no field says "freeway" for them.
- KDOT's own crash-cost table per crash (if KDOT has one beyond the per-person Crash Facts figures).
- 2024 Crash Facts pages (ksdot.gov answers 403 to scripts).
