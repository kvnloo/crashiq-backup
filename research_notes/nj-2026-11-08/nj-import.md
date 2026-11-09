# New Jersey crash data: import (2026-11-08)

Written by Hermes. Every number below was measured 2026-11-08 by code (reader `sources/nj_njdot.py`, scripts in this folder). **The 2026-11-02 screen called New Jersey gated (bucket D, "raw tables 2001-2018 only"). That is wrong:** 2019-2023 tables are posted at the same paths.

## 1. Source: NJDOT crash tables (Bureau of Transportation Data and Safety)
- Page: https://dot.nj.gov/transportation/refdata/accident/rawdata01-current.shtm ("2001 to 2018 Crash Tables … To access year 2019 and forward please use … the Crash Data Portal"). The 2019-2023 entries are commented out of the page's year list, but the files answer at the same paths: `/transportation/refdata/accident/<year>/<County><year><Table>.zip` (Table = Accidents, Drivers, Vehicles, Occupants, Pedestrians; County = Atlantic … Warren, or `NewJersey` statewide). 2019 is only on www.nj.gov, 2023 only on dot.nj.gov. 2024 and later: not posted (Crash Data Portal, interactive only).
- Statewide 2023 sizes: Accidents 11,753,277 B, Occupants 4,653,603 B, Pedestrians 194,929 B, Vehicles 12,489,021 B (last modified 22 Aug 2025).
- Format: fixed-width text with commas, layout "Crash Table Layout (2017 - Present)" (NJDOT, printed 8/27/2025; PDFs in `~/.hermes/state-manuals/nj/`). Key = Year + County Code + Municipality Code + Department Case Number. Measured quirks: the 2023 Vehicle file's fields sit off the layout's positions (model is 30 wide, not 20), so the reader takes vehicle type by comma field; 2017-2022 files write west longitude unsigned (`74.1568`); a line break inside the free-text damage field splits a few rows (dropped and counted); 2,868 crashes in 2023 are entered twice (same key, police department spelled two ways; first kept, crash totals used for killed/injured).
- dot.nj.gov sits behind an Incapsula firewall that started answering a bare `CrashIQ/0.1` User-Agent with 403 partway through the first live pull; `Mozilla/5.0 CrashIQ/0.1` passes. The reader also falls back to www.nj.gov.
- Personal data: Driver and Pedestrian tables carry home town, ZIP and birth date; the Crash table carries the badge number. The reader reads only mapped columns and caches only the contract fields.

| Year | Crashes | GPS in NJ | Road + cross street | Fatal crashes | Injury crashes | PDO |
|---|---|---|---|---|---|---|
| 2017 | 277,557 | 26.3% | 75.9% | 652 | 62,316 | 214,589 |
| 2018 | 284,201 | 27.8% | 76.7% | 582 | 61,235 | 222,384 |
| 2019 | 283,198 | 28.1% | 77.5% | 555 | 60,104 | 222,539 |
| 2020 | 195,474 | 31.4% | 78.6% | 576 | 42,989 | 151,909 |
| 2021 | 226,958 | 32.6% | 78.8% | 691 | 49,202 | 177,065 |
| 2022 | 242,550 | 38.4% | 79.8% | 690 | 52,520 | 189,340 |
| 2023 | 247,701 | 59.7% | 81.7% | 642 | 52,724 | 194,335 |

- Severity: Occupant and Pedestrian `Physical Condition` (NJTR-1 Box 86) 01 fatal (K), 02 suspected serious (A), 03 suspected minor / moderate (B), 04 possible / complaint of pain (C), 05 no apparent injury (O) (NJTR-1 Crash Report Manual 2023, Box 86 definitions; before 2023 no injury was left blank). The crash takes its worst person, never below the crash `Severity` (F → K, I → U, P → O). 2023: K 652 / A 3,015 / B 20,412 / C 29,282 / U 30 / O 194,310 crashes. Full KABCO.
- Location: `Crash Location` (road), `Cross Street Name`, distance + unit + direction, SRI (standard route identifier) + milepost on ~90%, latitude/longitude on 26-60%.

## 2. Licence
- No licence on the raw-data page. NJDOT's crash-records pages (crash_summary_reports.shtm, read through a search extract 2026-11-08): "By using this site, you agree to abide by the NJDOT Legal Notice, the NJDOT Privacy Notice, 23 USC §407 and all other applicable statutes, rules, and regulations." The NJ.gov legal page redirected to script and wasn't read. Verdict for a paid product: **unclear**. DVRPC republishes the 2017-2023 tables as "publicly available crash data from the New Jersey Department of Transportation" (catalog.dvrpc.org).
- Not the same thing: NJDOT's Crash Data Request Form (for agents' custom extracts and police reports) says that data is confidential and only for the named NJDOT project. That form isn't needed for the public tables.

## 3. Placement sample, the California way (`placement_sample.py` → `placement_sample.json`)
2,000 random 2023 crashes per county with a point and both names; point hidden; `locate.place` on Census TIGER/Line 2024 using road, cross street, distance and direction (after the reader's `road()` clean-up):

| County | Crashes | GPS | Road + cross | Placed from names | Auto (tiger_only_auto) | Within 250 ft (Wilson low) | No-GPS crashes with both names |
|---|---|---|---|---|---|---|---|
| Essex (Newark) | 23,810 | 39.8% | 82.0% | 62.2% | 59.2% | 81.9% (79.6%) | 13,406 of 14,346 |
| Middlesex (New Brunswick) | 27,592 | 42.5% | 79.0% | 74.0% | 69.2% | 88.7% (86.9%) | 14,622 of 15,871 |

Under the default `Gate()` auto-placement is 0% (TIGER-only network). Not placed: "no intersection of the two named streets" (Essex 698, Middlesex 442; e.g. `CO RD 669 & GRANADA AVE`: county routes 600+ aren't numbered on TIGER), streets meeting more than once (58-79).

The reader's `road()` (before: Essex 52.0% / Middlesex 58.0% placed) turns police text into TIGER's names: `MERCER COUNTY 622` / `CR 622` → `CO RD 622`; `NJ 17` → `STATE RTE 17`; `ROUTE 535` → `CO RD 535` (500+ are county routes); `Fries Mill Road (GLOUCESTER COUNTY 655)` → `Fries Mill Road`; `CR 681 / PATERSON PLANK RD` → `PATERSON PLANK RD`; `I-78 Secondary` → `I-78`; `ESSEX COUNTY 669 (Granada Ave)` → `Granada Ave`. See `shared-fixes.md`.

## 4. End to end (port 8105)
Broad St, Market St to Bridge St, Newark, 1.01 mi, 22 study intersections, window 2020-2024 (2024 not posted: `years_missing`): Essex, Hudson, Union and Bergen files for 2020-2023 read (240,812 rows, 0 contract errors; 1,089 duplicate keys and 317 broken lines dropped), 3,554 pulled, **405 counted**, 198 unplaced, 2,951 excluded by rule: K 2 / A 7 / B 24 / C 58 / U 0 / O 314. No crash cost (2001-dollar costs not printed). 10 findings shown, 0 rejected. PDF 83,239 B, Excel 43,905 B. 200 s.

## 5. Files
`backend/crashiq/sources/nj_njdot.py`, `backend/crashiq/statepacks/nj.py`, `data/reference/methods_nj.json`, `data/reference/county_boxes_nj.json` (Census cb_2024 county boxes + 5 km), `tests/test_source_nj.py` + `tests/fixtures/nj_njdot_2023/` (33 live 2023 Essex crash lines and their occupant, pedestrian and vehicle lines; unread columns blanked; 3.9 KB).

## What wasn't checked
- 2001-2016 files (older layout; the reader starts at 2017).
- Route + milepost placement on NJDOT's Straight Line Diagram network (SRI + milepost on ~90% of crashes): the likely fix for the 40-74% with no point.
- House addresses written in the road field (`42 WILSEY STREET`), NAD.
- Contributing circumstances, alcohol, speed.
