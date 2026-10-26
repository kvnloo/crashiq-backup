# #264: open address sources for D5 crashes (house number as location), 2026-10-25

Tester session, measure only, on the run 10 basis (main 7045831; D5 bucket from run 9A, still difficult in run 10b).

Sources, user-approved in the Tester session on 2026-10-25:
- **Census Geocoder batch:** address strings only; each line's id was a local sequence number, not a crash id.
- **TIGER/Line 2026 ADDRFEAT:** downloaded, 188 MB.
- **USDOT NAD r24:** downloaded, 8.48 GB; California rows kept.
- **OpenAddresses:** not approved, not measured. Its licences vary by source.

Source records: `knowledge/sources/us-census-geocoder.md`, `us-tiger-addrfeat.md`, `us-nad.md`.

## Pools

- **D5:** 12,568 crashes whose report gives a house address instead of a cross street (`BROADWAY 7346`). 12,278 are
  in cities and 290 outside them.
- **Truth:** the same kind of crash (a road field with a house number, by buckets.py's rule) whose police GPS fits
  the report. That's a seeded sample of 10,000 from 32,856 (run 10b gps_usable, city streets and county roads). The
  GPS is hidden and is the truth. 4,023 of the sample are in cities and 5,977 outside them; D5 itself is 98% in
  cities, so the in-city line is the one to read.

## Method (the same for the two local sources)

- **Street match:** the source's street is the crash's when the app's `same_core` says so (a leading direction
  word dropped either way) and, when both have a street type, the types agree.
- **One place:** the matching candidates, inside the crash's city box + 1 km (else its county), must lie within
  1,000 ft of each other; the spot is their mean. Otherwise the crash is not placed.
- **TIGER:** interpolated along the matching segment's range, with parity respected.
- **NAD:** address points with the same number.
- **Census:** the service's own match and point. Outside cities the city went blank, because CCRS gives
  "Unincorporated" and no ZIP. The first send used "Unincorporated" and matched 0.1%, so it was resent.

## Results

| Source | D5 placed (of 12,568) | Truth placed (of 10,000) | Within 250 ft (95% low) | Within 400 ft (95% low) |
|---|---|---|---|---|
| Census Geocoder | **9,068 (72.2%)** | 6,763 | 47.0% (45.8%) | 64.7% (63.6%) |
| TIGER ADDRFEAT, local | 7,737 (61.6%) | 7,026 | 46.5% (45.4%) | 65.4% (64.3%) |
| NAD r24 | 647 (5.1%) | 1,709 | **74.3% (72.1%)** | **86.1% (84.4%)** |

In cities (D5 12,278; truth 4,023):

| Source | D5 placed | Truth placed | Within 250 ft (low) | Within 400 ft (low) |
|---|---|---|---|---|
| Census Geocoder | 9,004 (73.3%) | 3,021 | 49.7% (47.9%) | 67.9% (66.2%) |
| TIGER ADDRFEAT | 7,698 (62.7%) | 2,719 | 49.4% (47.6%) | 68.2% (66.4%) |
| NAD | 642 (5.2%) | 477 | 70.9% (66.6%) | 83.6% (80.1%) |

**Same counties, head to head.** NAD covers 8 whole counties: San Bernardino, Sacramento, Ventura, Solano,
Santa Cruz, Merced, Shasta and Santa Barbara. There, Census is 66.3% within 400 ft, TIGER 67.2% and NAD 86.7%; within
250 ft it's 49.1%, 47.5% and 74.9%. On that truth sample all three place about the same number (1,592 / 1,708 /
1,683 of 2,271). On D5 they place 989, 683 and 631 of 1,615.

**NAD's California coverage (r24): 2,534,873 points from 10 contributors.**
- Whole counties: San Bernardino 840,205; Sacramento 703,920; Ventura 301,791; Solano 172,315; Santa Cruz 108,882;
  Merced 102,424; Shasta 79,417; Santa Barbara 56,393.
- Cities only: Stockton (San Joaquin) 117,299; Costa Mesa (Orange) 51,623.
- Nothing usable for Los Angeles, San Diego, San Francisco, Alameda, Santa Clara, Riverside, Fresno, Kern and the
  other counties.

**By Caltrans district.** Placed = D5 crashes placed. 400 ft = truth accuracy, with the number of truth crashes the
source placed in brackets.

| District | D5 | Census placed | TIGER placed | NAD placed | Census 400 ft (n) | TIGER 400 ft (n) | NAD 400 ft (n) |
|---|---|---|---|---|---|---|---|
| 1 | 106 | 55 | 49 | 0 | 68.9% (103) | 70.3% (175) | – |
| 2 | 171 | 86 | 47 | 18 | 53.7% (95) | 61.1% (90) | 88.2% (34) |
| 3 | 640 | 430 | 314 | 186 | 63.6% (1197) | 64.2% (1377) | 89.0% (871) |
| 4 | 2,492 | 1,963 | 1,717 | 23 | 75.9% (1078) | 76.1% (1083) | 87.4% (95) |
| 5 | 1,060 | 805 | 723 | 72 | 59.9% (424) | 56.3% (558) | 89.2% (232) |
| 6 | 523 | 354 | 238 | 0 | 59.5% (1007) | 62.1% (922) | – |
| 7 | 2,494 | 1,493 | 1,454 | 63 | 72.5% (1083) | 74.8% (1055) | 74.8% (147) |
| 8 | 903 | 561 | 403 | 229 | 55.2% (752) | 55.6% (732) | 82.9% (257) |
| 9 | 6 | 1 | 1 | 0 | 76.9% (13) | 75.0% (12) | – |
| 10 | 291 | 224 | 108 | 52 | 58.8% (417) | 59.5% (420) | 73.6% (72) |
| 11 | 3,409 | 2,851 | 2,515 | 0 | 61.4% (399) | 60.3% (418) | – |
| 12 | 473 | 245 | 168 | 4 | 62.6% (195) | 62.5% (184) | 100.0% (1) |

## Reading it

- **The two interpolation sources agree with each other and are far below the app's bar.** Census and TIGER ranges are
  each about 65–68% within 400 ft, against 98% for the exact tier. Census places more because its own matching
  is looser than this test's one-place rule.
- **Address points (NAD) are much closer:** 86–87% within 400 ft in the same counties, with the same truth and the
  same crashes. So the interpolation sources' gap is mostly their own, not the truth's: rooftop points beat ranges.
- **NAD covers only about a fifth of the state's points** and none of LA, San Diego or the Bay Area core. It places
  5% of D5.
- **Truth caveat:** many truth reports also name a cross street, and the crash may be at that corner rather than at
  the house. Reports giving only the address street measure higher (Census 77.0%, TIGER 76.6% within 400 ft in
  cities, n about 800).
- **Not measured:**
  - OpenAddresses, which wasn't approved; it has address points for many counties NAD lacks, with per-source
    licences;
  - county or city address-point layers (e.g. LA County's);
  - the SF open-data truth (case-number matched), on which the app's OSM `address` tier scored 81.4%.
- **Licences:** all three measured sources are US Government public domain; commercial use is OK.

Which source (if any) goes in the app, and with what label (precise or approximate), is the user's decision.

Scripts: `tests/statewide/d5_pools.py`, `d5_common.py`, `d5_census.py`, `d5_tiger.py`, `d5_nad.py`, `d5_eval.py`.
The NAD California filter (`nad_ca.py`) ran in a scratch venv with `zipfile-deflate64` (user-approved); it isn't
committed, since it's one-off source preparation (described in `knowledge/sources/us-nad.md`). Outputs are in
`data/statewide/` in the Tester worktree, not committed.
