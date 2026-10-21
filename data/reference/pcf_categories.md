# PCF violation section → SWITRS category crosswalk (`pcf_categories.csv`)

User decision #52 / 1A (2026-10-20, docs/03): rebuild CHP's own section→category assignment from SWITRS records,
keep a key when ≥ 99% of its records agree, and list the rest. Mapping only; nothing here is a judgement.

## Source
- **TIMS SWITRS Query & Map, Crashes export** (UC Berkeley SafeTREC; CHP's SWITRS records), downloaded
  2026-10-20 by the Tester session in the user's signed-in browser panel, with the user's OK for these two queries:
  - Los Angeles County, collision dates 01/01/2021–12/31/2024: **165,741** fatal and injury crashes
  - Fresno County, same dates: **14,697** crashes
- TIMS data as of Sep 15, 2026 (provisional years excluded: 2025–26).
- Fields used: `PCF_VIOLATION` (section), `PCF_VIOL_SUBSECTION`, `PCF_VIOL_CATEGORY` (the category CHP's SWITRS
  program computed), `PRIMARY_COLL_FACTOR` (for crashes with no section), `ACCIDENT_YEAR`.
- The raw files were processed in the browser and are not stored; only these counts are. TIMS terms: acknowledge
  "Transportation Injury Mapping System (TIMS), Safe Transportation Research and Education Center, University of
  California, Berkeley"; data "AS IS". Product use of TIMS-derived data is the open question #126; this table holds
  counts of CHP's own codes.

## Method
- Key = (section, subsection) when a section is given (`key_type = section`); else the primary-collision-factor
  code (`key_type = factor`: A violation not stated, B other improper driving, C other than driver, D unknown,
  E fell asleep). TIMS exports leave `PCF_VIOL_CODE` (law code type) blank (`-`), so it can't be part of the key.
- **The subsection matters:** 21453(a) → 12 Traffic Signals and Signs, (c) → 09 Automobile Right of Way,
  (d) → 11 Pedestrian Violation.
- Status: `mapped` = one category in ≥ 99% of the key's crashes; `unknown` = CHP's own program gives 00 (Unknown)
  or `-`; `split` = no category reaches 99%, with the year-by-year split in `split_by_year`.

## Agreement
629 keys, 180,438 crashes: **262 mapped (172,936 crashes, 95.8%)**, 349 unknown (7,020), 18 split (482).
Every mapped key agrees 100% in the data; LA and Fresno never disagree on a mapped key.
**The splits follow the year:** in 2021–2023 CHP assigned 00 to some sections that 2024 maps to a real category
(21954 → 10, 21955(a) → 10, 23103(a) → 17, 21960(a) → 05, 21720 → 05, 21235(b) → 02), i.e. CHP extended its table
in 2024. Whether to use the 2024 category for those is the user's call (not done here).

## Coverage of CCRS 2021–2024 (`tests/statewide/pcf_coverage.py`, local CCRS mirror copied 2026-10-19)
CCRS publishes only the violation text, written many ways (`VC 22350`, `22350`, `VC 21658(A)`, `21453A`,
`22107 CVC`, `VC 21650.1`, `21651(A1)`). Parsed to (section, subsection):

| | All crashes (1,655,224) | Fatal + injury (668,113) |
|---|---|---|
| mapped | 91.1% | 93.6% |
| blank violation text | 5.6% | 4.3% |
| words, not a section (`UNSAFE BACKING` 13,988, `UNSAFE SPEED` 5,647, `UNSAFE TURN` 4,649, …) | 2.7% | 1.4% |
| unknown (CHP 00) | 0.4% | 0.3% |
| split (listed) | 0.1% | 0.2% |
| section not in the crosswalk | 0.1% | 0.1% |

The word entries are descriptions, not sections; mapping them would be a guess, so they stay unmapped.
