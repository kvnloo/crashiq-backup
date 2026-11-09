# Mississippi: DPS eCrash public data, statewide (2026-11-08)

Written by Hermes. Every number measured on 2026-11-08 from the URLs named here, unless dated otherwise.

## 1. Source

- **eCrash public data**, Mississippi Department of Public Safety (DPS),
  https://publicdata.dps.ms.gov/Public-CrashData/eCrash/. No login. One Excel workbook per year:
  2019 (partial year), 2020, 2021, 2022, 2023, 2024 (posted 2026-02-05, 97.8 MB for 2020), 2025 (`DRAFT`, "data may
  change when all reports for 2025 are closed"). Older years (2004–2018) are ReportBeam files in another schema
  (`/Public-CrashData/ReportBeam/`, column map `eCrash-ReportBeam-Column Mapping.xlsx`); not read.
- Sheets: `Crashes` (53 columns), `Drivers`, `Passengers`, `Non-Motorists`, `Vehicles`, linked by `Crash ID` (GUID;
  `Crash Id` on Drivers/Passengers). 2024: 74,968 crashes, 130,475 drivers, 27,549 passengers, 988 non-motorists,
  133,821 vehicles (`scan.py`, `~/.hermes/cache/scratch/states/ms/scan2024.json`).
- Location: `Latitude`/`Longitude` on **74,968 of 74,968** 2024 crashes, all inside Mississippi. Also `Street Name`
  (40,926), `Intersecting Street Name` (11,553 with both), `Road Number` (34,042: a bare number, "55", whose kind is
  `Road Classification`: Interstate / US highway / State highway), `Milepost Number` (30,402), `Address Number`
  (8,998; sometimes a house number, sometimes a cross street or route, e.g. `HARDY ST.`, `US 49`: not used).
- Severity: per person `Injury Status`, KABCO as printed: `(K) Fatal Injury`, `(A) Suspected Serious Injury`,
  `(B) Suspected Minor Injury`, `(C) Possible Injury`, `(O) No Apparent Injury`. Crash level = worst person; the
  crash's own `Fatality Count` makes it K, and an `Injury Count` with no injured person row makes it U.
  2024 through the reader: K 670, A 2,196, B 7,425, C 9,181, U 109, O 55,387.
- Missing from the public file: manner of collision, driver movements (so no parties), primary collision factor.
- The 2026-11-02 screen was right (bucket A).

## 2. Licence

No licence published. The DPS public data home page (https://publicdata.dps.ms.gov/) says: "These data sets are
typically used to respond to public records requests and made available to the public free of charge. The datasets
do not contain personally identifiable information (PII) or information that might be otherwise be restricted by
state or federal law or regulation." Verdict for a paid product: **unclear** (public, free, no reuse terms): ask DPS
(PublicRecords@dps.ms.gov) in writing.

## 3. Reader

`backend/crashiq/sources/ms_dps.py`. Reads the index page for the year's file (DRAFT years are `preliminary`),
downloads the workbook, joins people and vehicles, keeps gzipped crash records in the cache (`ms_dps_<year>_<url
hash>.json.gz`, about 5.4 MB a year) and deletes the workbook. A year takes about 2 minutes to read on this Mac
(126 s for 2024) plus the download; the first corridor pull of 2020-2024 (four workbooks downloaded, 2024 already cached) took 27 minutes here; the next pull of the same years took 2 minutes.
Roads: `Street Name`, else `Road Number` as a route (`I-55`, `US 49`, `MS 25`: OSM's ref, so a Lakeland Drive corridor tagged `MS 25` matches; `SR 25` didn't, see shared-fixes.md).
Flags: pedestrian/bicycle from Non-Motorists, motorcycle and heavy truck from Vehicles `Body Type`, hit-and-run from
Vehicles, alcohol/drug/work zone from Crashes.

Statewide, through the reader (2026-11-08):

| Year | Crashes | With GPS | K | A | B | C | U | O |
|---|---|---|---|---|---|---|---|---|
| 2020 | 74,618 | 74,618 | 676 | 2,605 | 7,865 | 9,569 | 119 | 53,784 |
| 2021 | 83,319 | 83,319 | 698 | 2,570 | 7,996 | 10,551 | 141 | 61,363 |
| 2022 | 78,736 | 78,736 | 660 | 2,454 | 7,563 | 9,568 | 141 | 58,350 |
| 2023 | 76,512 | 76,512 | 674 | 2,375 | 7,475 | 9,184 | 104 | 56,700 |
| 2024 | 74,968 | 74,968 | 670 | 2,196 | 7,425 | 9,181 | 109 | 55,387 |

## 4. Placement sample (`placement_sample.py`, `placement_sample.json`)

Hinds County (28049), 2024, 2,000 random crashes (seed 2026) from the reader:

- GPS present and plausible: **100%**.
- With both street names: 25.7% (the rest name one road only, often a route and milepost).
- GPS hidden, TIGER/Line 2024 network, `locate.place`: placed 18.6% of all (72.5% of pairs); auto-placed under the
  default gate's tiers (`tiger_only_auto=True`, TIGER-only network) 16.7% of all (65.1% of pairs); within 250 ft of
  the hidden GPS **73.7%** (Wilson 95% low 68.7%).
- What breaks: "Frontage Road" pairs meet in many places; abbreviations with periods (`Pear Orchard Dr. / North Town
  Dr.`, two streets in one field); `I-20 W OFF-RAMP`. None matters for the app, since every crash has GPS.
- House addresses: not needed (100% GPS); not measured.

## 5. End-to-end (`e2e_result.json`, server on port 8104)

Lakeland Drive (MS 25), Jackson, line (32.3338, -90.1700) east to (32.3339, -90.1535), through the I-55 interchange, 0.97 mi, 2020-2024:
pulled 581, counted **304** (K 1, A 2, B 16,
C 42, U 0, O 243), excluded 277 (I-55 interchange,
frontage roads, cross streets), unplaced 0, 0 contract errors. Cost: not priced (no MDOT cost table).
Findings shown 6. PDF 45,505 bytes, Excel 34,202 bytes.
The first run wrote bare state routes as `SR 25` and counted only 178: 148 crashes coded `Road Number 25` didn't
match the corridor's OSM ref `MS 25`. The reader now writes `MS 25` (shared-fixes.md §1).

## 6. Status

`active`: open download, record-level with GPS, end-to-end passes. User action: ask DPS about reuse in a paid product.
