# Nebraska: NDOT NTIP crash map, statewide (2026-11-08)

Written by Hermes. Every number measured on 2026-11-08 from the URLs named here, unless dated otherwise.

## 1. Source

- **Nebraska Transportation Information Portal (NTIP)** crash map, Nebraska Department of Transportation,
  https://ntip2021.nebraska.gov/NTIP2021/Map (linked from https://dot.nebraska.gov/safety/crash/). No login. The
  map's form posts to `/NTIP2021/Map/Crashes` with `fromDate`/`toDate` (MM/DD/YYYY, 1/1/2021 to now), a lat/long box
  and filters, and returns every matching crash as JSON (no row cap seen: 36,842 for all of 2024 in one answer).
  It is the web map's own endpoint, not a published API.
- One row per crash: `k` crash key, `a`/`o` lat/long, `s` severity, `l` location sentence, `d` date, `t` time,
  `w` weather list, `y` weekday, `c` county, `r` alcohol (`Yes`/`No`); `m` (multi-vehicle) and `f` (first harmful
  event) came back empty on all 12,202 Omaha 2024 rows. No people, vehicles, light, surface, road class or report
  number. Pedestrian, bicycle, motorcycle and road-class are form filters only, so the reader asks once per filter.
- Severity codes: 01 Fatal (K), 02 Suspected Serious Injury (A), 03 Visible Injury (B), 04 Possible Injury (C),
  05 Property Damage Only (O), 06 Non-Reportable (left out), 96 Not Stated (left out).
- Statewide (map's own counts): 2024: 36,842 crashes, all with a point: K 228, A 996, B 5,030, C 2,813, O 21,708,
  non-reportable 6,067. 2025: 35,634: K 211, A 967, B 4,940, C 2,509, O 21,389, non-reportable 5,618. A 2021
  statewide query failed (no answer); 2021 corridor-size queries work. The 2026-11-02 screen counted 36,958 for 2024,
  so rows change after posting.
- Filters look incomplete for pedestrians and bicycles: the Omaha box for 2024 returns 21 pedestrian and 3 bicycle
  crashes, against 153 motorcycle and 1,894 freeway/expressway crashes. Not checked against NDOT's annual counts.
- Location sentences: `INT-72ND STREET (5037) & DODGE STREET (006)`, `LEAVENWORTH STREET (5044) E OF 60TH STREET
  (5043)`, `I-80 (080) EB RAMP TO KENNEDY FREEWAY (075)`, `204TH STREET (006) S OF W CENTER ROAD (275) NEAR OMAHA`.
  The reader drops the codes, splits on `&` / `<dir> OF` / `NEAR`, keeps the direction, and writes `N-133` as `NE 133` (OSM's ref).

## 2. Licence

The map shows: "CONFIDENTIAL INFORMATION: The safety and crash data information contained in this document is
confidential, protected and/or privileged information. Federal Law, 23 U.S.C. §407, prohibits the production of
this document or its contents in discovery or its use in evidence in a State or Federal Court. The State of Nebraska
has not waived any privilege it may assert as provided by that law through the dissemination of this document and
has not authorized further distribution of this document or its contents to anyone other than the original
recipient." Verdict for a paid product: **no, not without NDOT's written permission**. NDOT's open data site
(https://ndotdata.nebraska.gov/, CKAN) has 8 datasets and none on crashes.

## 3. Reader

`backend/crashiq/sources/ne_ntip.py`: 5 posts per corridor box and year (all crashes, then pedestrian, bicycle,
motorcycle, interstate + other freeways/expressways), cached per box and year. Status **reader_only** because of §2.

## 4. Placement sample (`placement_sample.py`, `placement_sample.json`)

Douglas County (31055), 2024, 2,000 random reportable crashes (seed 2026) from an Omaha box:

- GPS present and plausible: **100%**.
- With two street names: 95.2%.
- GPS hidden, TIGER/Line 2024 network, `locate.place`: placed 84.8% of all (89.1% of pairs); auto-placed under the
  default gate's tiers (`tiger_only_auto=True`) 84.1% of all; within 250 ft of the hidden GPS **82.6%** (Wilson 95%
  low 80.7%).
- What breaks: local names TIGER lacks (`NORTH FREEWAY`, `W DODGE EXPRESSWAY`), ramps (`WB RAMP TO 168TH STREET`).
- House addresses: not needed (100% GPS); not measured.

## 5. City feeds

Lincoln publishes yearly crash layers (https://opendata.lincoln.ne.gov/, 2025 and 2026 seen; fields not checked).
Omaha's Vision Zero layer has 414 rows only. Neither fills a gap the statewide map leaves; not read.

## 6. End-to-end (`e2e_result.json`, server on port 8104)

The pack is `reader_only`, so Setup refuses an NE study; the run used `serve_active.py` (a test harness that flips
NE to active in memory; not shipped) and passed years 2021-2025 explicitly (shared-fixes.md §3).
Dodge Street (US 6), Omaha, line (41.2597, -96.0195) west to (41.2597, -96.0365), through 72nd Street, 0.89 mi,
2021-2025: pulled 427 (163 non-reportable left out of 590), counted **362** (K 0, A 13,
B 51, C 68, U 0, O 230), excluded 65, unplaced 0, 0 contract errors.
Cost: not priced (NDOT's costs are per person). Findings shown 1. PDF 54,264 bytes,
Excel 33,671 bytes. The cold pull took about 2-3 minutes a year (5 posts a year to a slow server);
1070 s in all.

## 7. Status

`reader_only`. User action: ask NDOT (Traffic Safety, Highway Safety Office) for written permission to use NTIP crash
data in a paid product, or for a bulk extract with reuse terms.
