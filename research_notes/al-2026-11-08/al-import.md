# Alabama crash data: import notes (Hermes, 2026-11-08)

All numbers measured live on 2026-11-08 unless marked.

## 1. Sources

### 1a. CARE eCrash map layer (the reader)
- <https://care-esriext.aladata.com/arcgis/rest/services/eCrash/Red/MapServer/0> ("Alabama.DBO.ALABAMAINTEGRATEDCRASHDATA"),
  ArcGIS 11.3 MapServer, capabilities Map/Query/Data, maxRecordCount 5,000, **no token**. No description or copyright
  text. Run by the University of Alabama Center for Advanced Public Safety (CAPS), which builds CARE for ALDOT/ALEA.
- 250 fields, one row per crash: the crash row also carries the causal unit (CU*) and the second vehicle (V2*). There
  are no person or vehicle tables. Key: `ID` (= `CrashNum` = `DpsCaseNumber` on normal rows).
- Severity **KABCO** (`CrashSev`): Fatal Injury / Suspected Serious Injury / Suspected Minor Injury / Possible Injury /
  Property Damage Only, plus Unknown. Unknown = 2.1% of 2024 statewide and 5.1% in Jefferson; it isn't counted.
- Location: `Latitude`/`Longitude` (-1 when none), `HasCoord` (officer GPS, manual, or derived by CARE from a node,
  link or route-milepost), `StreetName`, `CrossStreet1/2`, `DistFromNode1`, `Route`, `Milepost`.
- Rows per year (normal + shifted rows, see 1b):

| year | rows | with a point |
|---|---|---|
| 2020 | 134,567 | 125,275 (93.1%) |
| 2021 | 152,621 | 144,438 (94.6%) |
| 2022 | 144,554 | 127,276 (88.0%) |
| 2023 | 144,418 | 122,044 (84.5%) |
| 2024 | 142,015 | 121,357 (85.5%) |
| 2025 | 140,514 | 118,689 (84.5%) |
| 2026 | 115,516 | 81,640 (70.7%) |

  Newest crash: 2026-11-08 (DateTime max). 2026 is the current, partial year.

### 1b. Shifted rows (CARE load defect, repaired in the reader)
From OBJECTID 746,179 on (227,676 rows: 1,699 late-loaded 2024 crashes, 2025 from April, all of 2026), the text columns sit **two places to the
left**. `CrashSev` holds the at-intersection flag and the real severity is in `ManrCrs`. `County` holds the year,
`NumMajInj` the county and `NumMinInj` the city. Doubles, dates, `ID`, the street names and the point are not shifted.
Found by matching value sets on 300 shifted rows against 300 normal ones. The repaired 2025 Jefferson rows have the
same distribution as 2024:

| | Jefferson 2024 (normal) | Jefferson 2025 (repaired) |
|---|---|---|
| rows | 26,509 | 21,550 |
| K/A/B/C/O/unknown | 97/323/1383/1807/21546/1353 | 61/334/1102/1414/17469/1170 |
| with point | 66.6% | 63.7% |
| street + cross street | 88.0% | 87.0% |
| interstate | 19.9% | 19.8% |

The reader detects a shifted row by a 4-digit `County` and filters years with `(Year IN (…) OR County IN (…))`.

### 1c. Other Alabama sources
- CARE **SAFETY Public** portal (<https://safety.aladata.com>): "publicly available Alabama crash data … no password
  is required". It gives cross-tabs, not records.
- CARE **SAFETY Private**: "multiple year location specific Alabama crash data … individually password protected"
  (<https://www.caps.ua.edu/analytics/portals/>). That makes it **gated** (an agency or consultant login).
- ALDOT open data: no crash layer found. ALDOT's AADT is at <https://aldotgis.dot.state.al.us/atd> (not used).

### Licence
- No licence is published for the layer.
- ALDOT's *Safety Data Access Guidebook* (sha256 5c113785…cf32b; `~/.hermes/state-manuals/al/`):
  - PDF p. 6: "These data are not to be shared with the public pursuant to Alabama Law and 23 U.S.C. §§148(h)(4) and 409."
  - PDF p. 10: since the 1995 amendment of §409 "ALDOT ceased releasing crash data to the p[ublic]".
- The open layer looks like a map back end that wasn't meant to be public. Verdict for a paid product: **no, not
  without written permission** from ALDOT (Office of Safety Operations) and CAPS. So the pack is **`reader_only`**,
  although every technical check passes.

## 2. Placement, the California way
Jefferson County (01073), 2024, random 2,000 with GPS (seed 2026). Method: hide the point, place the street pair on TIGER/Line 2024 Jefferson County with `locate.place`,
score under `Gate(tiger_only_auto=True)`.

| measure | value |
|---|---|
| street + cross street | 98.7% |
| placed from names | 65.3% |
| auto-placed | 60.8% |
| auto within 250 ft of CARE's point | 44.1% (Wilson low 41.3%) |
| tiers | {'exact': 1204, 'review': 668, 'relaxed': 16, 'near': 30, 'unique_pair': 12, 'verified_typo': 35, 'fuzzy': 9} |

Accuracy depends on where CARE's point came from:

| point source | n | auto-placed | within 250 ft |
|---|---|---|---|
| Coordinates derived from Node | 795 | 470 | 74.0% |
| Coordinates derived from Route-Milepost | 712 | 435 | 11.3% |
| Coordinates entered by Officer | 250 | 167 | 34.7% |
| Coordinates derived from Link | 150 | 86 | 41.9% |
| Coordinates entered Manually | 93 | 58 | 77.6% |

**The low accuracy is mostly the shared street-name key, not the data.**
- Birmingham repeats street names north and south of the railroad (3rd Ave N and 3rd Ave S, 11th St N and 11th St S).
- `names.street_key` drops the trailing N/S, so "3rd Ave N" and "3RD AVE S" get the same key (checked 2026-11-08),
  and a pair can land on the twin intersection ("4th Ave S & 15th St S" landed 11,594 ft off).
- Route-milepost points are CARE's own estimates (11% agree). Fix proposed in shared-fixes.md.

No-point crashes in Jefferson 2024:
- 8,079 crashes; 5,237 have a pair.
- 2,830 auto-placed by name (35.0% of the no-point crashes).
- Accuracy not measurable: no hidden truth.

House addresses: StreetName sometimes holds one ("600 Tuscaloosa Avenue SW", with the same text as the cross
street). Their share wasn't measured, and NAD coverage for Alabama wasn't checked.

## 3. End-to-end (port 8103, 2026-11-08, pack set active for the run, then reader_only)
- Corridor: 3rd Avenue North, Birmingham, about 11th St N to 24th St N, 1.21 mi; window
  2020-2024.
- Read: 39,416 rows read, 36,934 of them no-point county rows (the county fetch). 530 shifted rows were repaired;
  3,344 with Unknown severity dropped; 0 contract errors.
- Counted: pulled 1,470, counted **256**.
  - Excluded 919: 453 cross street not on the corridor, 374 outside the buffer, 64 outside the study limits,
    13 not on the corridor street, 11 grade-separated crossings, 4 freeway.
  - Unplaced 295: 251 no point and not placeable, 42 no cross street, 2 house addresses.
- Result:
  - K/A/B/C/U/O = {'K': 0, 'A': 4, 'B': 17, 'C': 28, 'U': 0, 'O': 207}.
  - Crash cost $14,079,535 (ALDOT costs).
  - Findings shown: 6.
  - PDF 58,526 B, Excel 38,664 B, 154 s.

## 4. What wiring needs
Nothing beyond the plug-in. To offer Alabama: get permission (§ Licence), set `status="active"`, and merge the
quadrant street-key fix.
