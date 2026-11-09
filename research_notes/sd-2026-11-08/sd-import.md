# South Dakota crash data: import (2026-11-08)

Written by Hermes. Every number below was measured 2026-11-08 by code (reader `sources/sd_dps.py`, scripts in this folder).

## 1. Source: SD DPS Office of Accident Records, Raw Crash Data
- Page: https://www.safesd.gov/ → "Download Crash Data" → "Raw Crash Data. Data updated April 15 annually. Choose a year to download data in pipe-delimited format." Years listed: 2011-2025.
- Files: `https://www.safesd.gov/downloads/raw-data/SDARSFiles<year>.zip`, 8-10 MB each (2011: 8,118,763 B; 2015: 9,127,131 B; 2019: 10,480,387 B; 2025: 10,328,825 B). No login.
- 13 pipe-delimited tables per zip (Accident, Person, Vehicle, Weather, Citation, DriverContrib, NonMotorist, ...), linked by `AccidentSeqID`. The reader reads Accident, Person, Vehicle and Weather only.
- Personal data: the tables carry names, addresses, birth dates, VINs and plates. The reader reads only the columns it maps and caches only the contract fields; the zip is deleted after reading.

| Year | Crashes | GPS in SD | Road + cross street | K | A | B | C | O |
|---|---|---|---|---|---|---|---|---|
| 2020 | 17,583 | 100.0% | 98.7% | 132 | 419 | 1,297 | 1,598 | 14,137 |
| 2021 | 19,461 | 100.0% | 98.7% | 131 | 495 | 1,415 | 1,706 | 15,714 |
| 2022 | 18,598 | 100.0% | 98.4% | 121 | 507 | 1,402 | 1,683 | 14,885 |
| 2023 | 18,771 | 100.0% | 98.4% | 129 | 450 | 1,490 | 1,629 | 15,073 |
| 2024 | 18,689 | 100.0% | 98.1% | 134 | 477 | 1,511 | 1,499 | 15,068 |
| 2025 | 18,974 | 100.0% | 97.8% | 110 | 507 | 1,621 | 1,404 | 15,332 |

(2025: 1 Accident row of 18,975 has its columns slipped by a `|` inside a text field; dropped and counted.)

- Severity: `Person.InjuryStatusDesc` = Fatal injury (K) / Incapacitating (A) / Non-incapacitating (B) / Possible (C) / No injury (O); the crash takes its worst person, never below `Accident.Severity` (Fatal → K, Injury → U, PDO → O). Full KABCO, no `severity_note`.
- Location: WGS84 `LatitudeValue`/`LongitudeValue` on every crash; road (`LocRoadwayName`), nearest cross street (`LocNearestCrossName`) with distance and compass direction; route + reference marker (`PrimaryHwyNbr`, `ILTMRM`).

## 2. Licence
- safesd.gov: "Vehicle crash reports are covered by South Dakota open records statute and are maintaned in our database for a period of 15 years." Footer: "Copyright ©2022 South Dakota Department of Public Safety. All Rights Reserved."
- No reuse licence for the raw data. Verdict for a paid product: **unclear**. The dps.sd.gov/Disclaimer page renders by script; its text wasn't read.

## 3. Placement sample, the California way (`placement_sample.py` → `placement_sample.json`)
Minnehaha County (Sioux Falls), 2025: 5,836 crashes, 100% GPS, 97.0% with road + cross street. 2,000 random crashes with both names, GPS hidden, placed with `locate.place` on a Census TIGER/Line 2024 network (46099) using the road, cross street, distance and direction:
- placed from names: 75.7% (exact 1,405, review 487, unique pair 83, near 21, verified typo 3, relaxed 1)
- auto-placed: 0% under the default `Gate()` (TIGER-only network); 74.4% under `Gate(tiger_only_auto=True)`, of which **91.4% within 250 ft** of the hidden GPS (Wilson 95% low 89.9%)
- not placed: "no intersection of the two named streets" 436 (e.g. `W 77TH ST & W BITTERROOT ST`), streets meet more than once 51
- Since every crash has GPS, names add nothing here (0 no-GPS crashes); they're a cross-check only.

Reader repairs (in `sd_dps.street_pair`, no shared change): a road written "A / B" (an intersection in one field; 171 in 2025) is split; a cross street equal to the road (610) is replaced by `LocIntersectionName` when it differs (388). Interstate ramp suffixes (`I 229 N1`) already reduce to `I 229` in `names.street_key`.

## 4. End to end (port 8105)
S Minnesota Ave, W 41st St to W 57th St, Sioux Falls, 0.97 mi, 11 study intersections, window 2020-2024: 521 rows read, 0 contract errors, 513 pulled, **340 counted** (173 excluded by rule, 0 unplaced): K 0 / A 2 / B 17 / C 53 / U 0 / O 268. No crash cost (SD has no per-level costs). 6 findings shown, 0 rejected. PDF 56,707 B, Excel 37,226 B. 96 s.

## 5. Files
`backend/crashiq/sources/sd_dps.py`, `backend/crashiq/statepacks/sd.py`, `data/reference/methods_sd.json`, `data/reference/county_boxes_sd.json` (Census cb_2024 county boxes + 5 km), `tests/test_source_sd.py` + `tests/fixtures/sd_sdars_2025_sample.zip` (40 live 2025 Accident rows and their Person/Vehicle/Weather rows, cut to the read columns, 4.7 KB). No shared fix needed.

## What wasn't checked
- Column names in 2011-2019 files (the reader was run on 2020-2025 only).
- Contributing circumstances, DUI and speed (not mapped yet).
- House addresses / NAD.
