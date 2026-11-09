# Pennsylvania: PennDOT public crash data, statewide (2026-11-08)

Written by Hermes. Every number measured on 2026-11-08 from the files named here.

## 1. Source

- **PennDOT public crash data** (PennDOT GIS Open Data, "Crash Data Download" map): one zip per county and year,
  `https://gis.penndot.pa.gov/gishub/crashZip/County/<COUNTY>/<COUNTY>_<YEAR>.zip` (1-3 MB), and a statewide zip per
  year `https://gis.penndot.pa.gov/gishub/crashZip/Statewide/Statewide_<YEAR>.zip` (~24 MB). No login.
- Years 2006-2025 (`..._2005.zip` is 404). 2025 was posted 2026-06-05 (Last-Modified header): a year lands in June
  of the next year, so `final_lag_months=6`.
- Each zip holds 8 CSV tables keyed by CRN: CRASH, ROADWAY, FLAGS, PERSON, VEHICLE, COMMVEH, CYCLE, TRAILVEH. The
  reader uses CRASH (GPS `DEC_LATITUDE/DEC_LONGITUDE`, `MAX_SEVERITY_LEVEL`, month, weekday, hour, collision type,
  light, weather, surface), ROADWAY (street names in `RDWY_SEQ_NUM` order, route, segment, access control) and FLAGS
  (pedestrian, bicycle, motorcycle, heavy truck, hit-and-run).
- The day of the month is not in the public files ("Data ... that could be used to infer information about persons
  involved in a crash are not included in the public dataset", Crash Data Dictionary 06-26,
  `~/.hermes/state-manuals/pa/Crash_Data_Dictionary_2026.pdf`). Crash lists show month and year only.

### Licence
None published. PennDOT Open Data (https://data-pennshare.opendata.arcgis.com/) offers "all of our published GIS
data that you can map, style, chart, download or share"; DVRPC's catalog copy says "License: No License Provided".
Verdict for a paid product: **unclear**: ask PennDOT in writing (user actions).

## 2. Statewide numbers (Statewide_<year>.zip, streamed)

| Year | Crashes | GPS | ≥1 street name | 2 street names | K / A / B / C / U (8+9) / O |
|---|---|---|---|---|---|
| 2021 | 118,095 | 99.71% | 99.49% | 37.1% | 1,153 / 4,271 / 26,752 / 8,491 / 15,654 / 61,774 |
| 2022 | 116,145 | 99.75% | 99.87% | 37.5% | 1,092 / 4,027 / 26,432 / 7,927 / 14,911 / 61,756 |
| 2023 | 110,736 | 99.81% | 99.96% | 38.1% | 1,131 / 4,082 / 26,474 / 7,896 / 14,002 / 57,151 |
| 2024 | 110,934 | 99.85% | 99.92% | 37.4% | 1,060 / 4,010 / 27,620 / 7,667 / 13,085 / 57,492 |
| 2025 | 109,698 | 99.54% | 99.70% | 36.7% | 979 / 3,907 / 27,145 / 7,573 / 12,433 / 57,661 |

Severity map (`MAX_SEVERITY_LEVEL`): 1 K, 2 A, 3 B, 4 C, 0 O; 8 "injury, unknown severity" and 9 "unknown if
injured" → U, because PennDOT's own Crash Facts 2025 (p. 8) counts both among injury crashes; 5 (died before the
crash) → O.

## 3. Placement sample, the California way (`placement_sample.py`, `placement_sample.json`)

2,000 random 2025 crashes per county with two different street names, GPS hidden, placed with `locate.place` on a
Census TIGER/Line 2024 network, scored against PennDOT's GPS.

| | Philadelphia (42101) | Allegheny (42003) |
|---|---|---|
| 2025 crashes in county | 7,014 | 10,528 |
| GPS present and plausible | 99.46% | 97.56% |
| two street names | 48.1% | 41.8% |
| placed from names (any tier) | 92.7% | 72.1% |
| auto under default `Gate()` | 0% (TIGER-only placements are suggestions) | 0% |
| auto with `tiger_only_auto` (exact + unique_pair) | 91.5% | 67.5% |
| of those within 250 ft | 99.13% (Wilson low 98.58%) | 97.26% (low 96.25%) |
| crashes with no GPS / of them with a street pair | 38 / 5 | 257 / 71 |

What breaks: PennDOT spells numbered streets (`SIXTYTHIRD ST`, `FIFTY-FIFTH ST`; ~7% of Philadelphia's street rows).
The reader now writes `63RD ST` (Philadelphia: 67.8% → 92.7% placed). Still unplaced: ramps named `RAMP A RD`,
two names in one field (`WOODHAVEN RD/THORNTON RD`), and pairs that meet twice. No house numbers, so NAD doesn't apply.
Since GPS covers 97.6-99.5%, names add at most ~0.07% (Philadelphia) to ~0.7% (Allegheny) of crashes.

## 4. End to end (port 8103, 2026-11-08)

North Broad Street, Girard Ave to Susquehanna Ave, Philadelphia: 1.03 mi, 11 study intersections, 2021-2025.
Pulled 1,068 rows (0 contract errors), kept 554, **counted 375**: K 6 / A 29 / B 103 / C 50 / U 102 / O 85.
Crash cost **$155,251,853** (PennDOT Crash Facts 2025 costs, U unpriced). 14 findings shown, 0 rejected.
PDF 59,260 bytes, Excel 37,784 bytes, 234 s.

## 5. Wiring
Plug-in only: `statepacks/pa.py` → `sources/pa_penndot.fetch_contract`. No shared file changed. Shared fixes the core
would need: `shared-fixes.md`.

## 6. Not checked
PERSON/VEHICLE tables (party rows, movements), PennDOT's DUI/speed flags → T14, other big cities' street formats
(Erie, Allentown), the 2006-2020 files.
