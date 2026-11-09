# Iowa: crash data for CrashIQ (Hermes, 2026-11-08)

Every number was measured live on 2026-11-08 unless marked. Scripts: `placement_sample.py` (result in
`placement_sample.json`); year counts from `returnCountOnly` queries; end-to-end in `e2e_result.json`.

## 1. Source: Iowa DOT Traffic_Safety ArcGIS services (the data behind ICAT)
- Crashes: https://gis.iowadot.gov/agshost/rest/services/Traffic_Safety/Crash_Data/FeatureServer/0 (one row per
  crash). Persons: `.../Crash_Person_Data/FeatureServer/0` (CRASH_KEY text). Vehicles:
  `.../Crash_Vehicle_Data/FeatureServer/0` (VEH_CRASH_KEY). Public, no login, maxRecordCount 2000.
- Window: the prior 10 years plus the current one, updated daily; latest CRASH_DATE 2026-11-05.
- Rows per year: 2015 54,847 · 2016 56,069 · 2017 55,998 · 2018 56,895 · 2019 58,565 · 2020 47,894 · 2021 54,624 ·
  2022 53,706 · 2023 52,870 · 2024 53,342 · 2025 52,717 · 2026 (to Nov 5) 42,979.
- Location: an Iowa DOT point on every crash (2026-11-02 screen: 639,375 of 639,375; Polk 2024 sample: 2,000/2,000).
  Street text in `LITERAL`: "A AND B", "A MEASURING 45 FEET NORTH FROM B", "100 BLK NE 41ST ST", "I 80 W - 132.00MM".
  The reader splits it into street, cross street, offset, house/block number or milepost.
- Severity: per-crash counts of fatalities, major, minor, possible and unknown injuries, so K/A/B/C come straight from
  Iowa's own levels; "unknown injury" is U. (Iowa's CSEV code merges possible and unknown as 4; checked equal.)
- Codes decoded from Iowa DOT's metadata workbooks (`~/.hermes/state-manuals/ia/Crash_Data_metadata.xlsx`,
  `Crash_Vehicle_metadata.xlsx`).
- Ped/bike from the person layer's NM_TYPE (it lacks some crashes, so a floor); motorcycle/heavy truck from VCONFIG.

### Licence
CC BY 4.0 on the ArcGIS items, plus Iowa DOT's GIS Data Terms of Use
(https://iowadot.gov/policies_and_statements/terms-of-use#gis, effective 2026-06-19), quoted:
> These licenses allow you to copy, share, adapt, transform, and build upon the Data for any purpose, including
> commercial use, provided that you give appropriate credit to the Data source, which may be the Iowa Department of
> Transportation or a third party, and comply with the terms of the applicable license.

Verdict for a paid product: **ok with attribution**. The pack's `legal` line gives the credit. (The site's general
terms are "noncommercial", but they cover the website content; the GIS data section above governs the data.)

### Cities
None needed: the state layer has every crash with a point (2026-11-02 screen found no city feeds).

## 2. Placement sample (Polk County, 2024, 2,000 random crashes, seed 2026)
GPS hidden, street pairs placed on TIGER/Line 2024 (tl_2024_19153) with `locate.place`:
- GPS present and inside Iowa: 100%.
- Street pair: 57.6%; house or block address with no cross street: 19.4%.
- Placed from names: 38.9% of all (67.6% of pairs). Tiers: exact 749, unique_pair 17, verified_typo 7, relaxed 3,
  fuzzy 1, near 1; review 373.
- Auto-placed under the gate's tiers: 38.3% (66.6% of pairs). Within 250 ft of Iowa DOT's point: **96.2%**
  (Wilson 95% low 94.6%). Plain `Gate()` auto-places 0 on a TIGER-only network (every placement is `tiger_road`);
  the score uses `Gate(tiger_only_auto=True)`.
- Not placed: no cross street 462; streets don't meet 299 ("IA 163 E & IOWA STATE FAIRGROUNDS AND EAST 33RD ST",
  "NE 64TH ST & NE 78TH AVE, BONDURANT, IA 50035"); meet in more than one place 66 ("UNIVERSITY AVE & 42ND ST");
  "I80 & 35 WB" style (I-35/80 concurrency) reads as a missing name.
- House addresses: NAD's feature service returned HTTP 400 on every query on 2026-11-08: **not measured**.
- What it adds: nothing for placement (every crash has a point); it is what the corridor-street name check sees.

## 3. Importer
`backend/crashiq/sources/ia_dot.py`: `fetch_contract(box, county_fips, years, cache_dir)` reads crashes in the box,
joins non-motorist and vehicle types by crash key. Plug-in `statepacks/ia.py`, `status="active"`, first year 2015.
Test: `tests/test_source_ia.py` on a recorded Merle Hay Road fixture (80 KB).

## 4. End to end (2026-11-08)
Merle Hay Road, Des Moines/Urbandale, 1.0 mi, 2020-2024: pulled 443, counted 346 (excluded 97, unplaced 0);
K 0, A 3, B 23, C 55, U 30, O 235. Crash cost $23,380,188 (Iowa TSIP 2018 costs; U unpriced). Findings shown 8.
PDF 51,151 bytes, Excel 36,977 bytes, 123 s.

## 5. What we didn't check
- Address-point placement (NAD down); OSM+TIGER network placement as the app builds it.
- Freeways other than Interstates (`is_freeway` is Interstates only).
- Iowa DOT's major-cause codes (primary factor, DUI, speed rows blank).
