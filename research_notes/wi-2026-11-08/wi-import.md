# Wisconsin: statewide crash data for CrashIQ (Hermes, 2026-11-08)

Status: **active** (plug-in `statepacks/wi.py`, reader `sources/wi_dt4000.py`). Bucket **A\*** (open, but newest year 2022 and no licence text).

## 1. Source: WisDOT annual DT4000 crash data sets
- Index: https://wi-state-patrol.atlassian.net/wiki/spaces/OPENDATA/pages/2069528581/Wisconsin+Motor+Vehicle+Crash+Annual+Data+Sets
  (version 20230916-001, read 2026-11-08). DT4000 2017-2022; legacy MV4000 format 1994-2016 (not read).
- Each year is a public Box.com zip; `https://wisdot.box.com/shared/static/<id>.zip` downloads with no login (all 6 checked
  2026-11-08: 82.9, 86.6, 97.3, 67.6, 73.9, 74.1 MB). 2017-2019 keep the CSVs at the zip root (`WIN_annual_dt4000_<y>_crash.csv`),
  2020-2022 under `dt4000/`.
- The crash file: one row per crash, 213+ columns. The reader keeps 36 (KEEP) and caches each year gzipped (~7 MB).
- Statewide counts (read through the reader):
  - 2018: 144,212 crashes, GPS 95.2%, K 517 / A 2714 / B 12882 / C 14363 / O 113736, last date 2018-12-31
  - 2019: 145,288 crashes, GPS 98.4%, K 511 / A 2621 / B 12273 / C 13897 / O 115986, last date 2019-12-31
  - 2020: 114,697 crashes, GPS 98.5%, K 540 / A 2651 / B 10777 / C 10319 / O 90410, last date 2020-12-31
  - 2021: 128,296 crashes, GPS 98.8%, K 546 / A 2880 / B 11965 / C 11364 / O 101541, last date 2021-12-31
  - 2022: 128,830 crashes, GPS 99.1%, K 547 / A 2740 / B 11393 / C 10938 / O 103212, last date 2022-12-31
- Location: LATDECDG/LONDECDG (2022 source: 97.0% TLT = WisDOT location tool, 1.6% GPS); ONSTR or ONHWY+ONHWYSYS and
  ATSTR or ATHWY+ATHWYSYS on 99.997%; INTDIS (miles) + INTDIR on 77%; house number (ATCODE 101) on 12%.
- Severity: INJSVR = most severe injury in the crash, KABCO letters; never blank in 2018-2022.
- Flags used: PEDFLAG, BIKEFLAG, CYCLFLAG (motorcycle), TRKFLAG; ACSCNTL 101 (full control) or IH = freeway.
- Licence: "making its annual motor vehicle crash data sets available as open data"; no licence text. Paid use: **unclear**.

## 2. Community Maps (2010-now) is not a source
https://transportal.cee.wisc.edu/partners/community-maps/crash/termsOfService.do: "Automated access, bulk data extraction,
or use that degrades system performance is not permitted." The advanced download needs an account. Not read.
WisDOT GIS Open Data (data-wisdot.opendata.arcgis.com): no crash layer (search 2026-11-08).

## 3. Placement sample (the California way)
`placement_sample.py` -> `placement_sample.json`: 2000 random 2022 Milwaukee County crashes, TIGER/Line 2024 (55079), GPS hidden,
WisDOT's offset passed, `Gate(tiger_only_auto=True)`.
- GPS 99.7%; street pair 100.0%; offset given 83.5%; house number 18.7%.
- Name-placed 75.4%; auto 73.8%; within 250 ft (auto) **97.5%**, Wilson low 96.6%.
- Not placed: "no intersection of the two named streets" 369 (e.g. PARKING LOT, a highway crossing itself), "streets meet in more
  than one place" 122 (state highways that run along several streets).

## 4. End-to-end (live, port 8101)
W Capitol Dr (WIS 190), N 27th St to N 43rd St, Milwaukee, 1.01 mi, 2018-2022: reader rows 3,378
(1,947 no-GPS Milwaukee County crashes, sorted by street name), pulled 1404, counted **1015** (excluded 389),
K 3 / A 17 / B 114 / C 175 / U 0 / O 706, cost $131,133,181 (WisDOT 2025 $), 11 findings,
PDF 108,442 B, Excel 40,590 B. First pull downloaded 2019-2021 live (2018, 2022 pre-seeded from the same files).
