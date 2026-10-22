# Step 2 (#211): the difficult bin. What's in it, why, and which fixes gain most at what accuracy

Tester, 2026-10-22. **Measure only: the user picks the fixes.**

**Basis:** CCRS mirror 2026-10-19, OSM 2026-10-18, app code main e2f1633 (backend unchanged since). It uses the **corrected** #199 coverage: `reports/testing/coverage-correction-2026-10-22.md`, on the map 85.3% → **86.1%**.

**Completeness guard:** every difficult crash was re-placed on main. That's 285,705 crashes in the corrected file, plus 38 that #206 drops from exact, minus the 163 main already places: 285,580 difficult on main.

## Headline

- **Difficult bin on main: 285,580 of 2,057,508 crashes (13.9%).**
- **Biggest fix by far: auto-place the unique-pair tier** (#201/#203; it exists on main with the gate off).
  - Gain: **+106,700 crashes**, 278 of them fatal and 5,863 serious injury. That's 5.2 points of all crashes, taking on the map from 86.1% to about 91.3%.
  - Accuracy, against the exact tier that is already auto-placed:
    - hidden police GPS: 92.4% (low 91.7%, n=7,422) vs exact 90.4% (low 90.0%, n=22,597);
    - **LAPD open data: 97.0% (low 96.3%, n=2,878) vs exact 95.7% (low 94.7%, n=1,925)**.
  - It's at least as accurate as the tier already trusted, statewide and in the big districts (table below). District 5 is lower (85.2% vs 89.2%).
  - **SF DataSF can't test it:** n = 4 (4 right). SF report names don't leave out what OSM writes, so the tier almost never fires there. LAPD's open data is where it is exercised, and the 98% bar can't be shown on SF for this tier.
- **Bug #212** (leading abbreviations: AVE M ≠ Avenue M; ST/MT/FT): up to 5,018 difficult crashes. Engineering is on it, and the failing test is merged (#213).
- **Not recommended:** auto-placing fuzzy or near, and the offset-direction clue. Each is well below the exact tier's accuracy on every truth.

## Part C: ranked fixes

| Fix | Crashes gained (fatal / KSI) | Hidden police GPS, right intersection | LAPD open data | SF open data | Effort | Decision |
|---|---|---|---|---|---|---|
| (yardstick) exact tier, already auto-placed | - | 90.4% (low 90.0%, n=22,597) | 95.7% (low 94.7%, n=1,925) | 99.2% (low 98.9%, n=3,627) | - | - |
| 1. Auto-place unique_pair (#201/#203: the two streets, allowing only what the report leaves out, meet once) | 106,700 (278 / 5863) | 92.4% (low 91.7%, n=7,422) | 97.0% (low 96.3%, n=2,878) | 100.0% (low 51.0%, n=4) | config: add unique_pair to the gate (tier exists on main) | user: gate change (docs/03 98% bar) |
| 2. Fix #212: expand leading abbreviations (AVE M = Avenue M; ST/MT/FT) | up to 5,018 | measure after the fix (same tiers as today, on more names) | - | - | normalizer bug fix (Engineering) | none (bug) |
| 3. OSM + TIGER street-network union (#17) | ~18,098 (audit estimate) | - | placed 90.1% -> 93.0%, accuracy 83.7% -> 83.3% (all tiers, point) | placed 93.4% -> 94.4%, low 98.0% -> 97.9% | build the union for every county; TIGER download for the other 56 counties (user OK needed) | user: build it, and approve the downloads |
| 4. Alias / spelling table learned from the audit (PROPOSAL only) | ~11,140 (audit estimate) | - | - | - | table + review UI; every entry approved by the user (CLAUDE.md) | user: approve the table |
| Auto-place relaxed (suffix differs) | 9,977 (23 / 455) | 91.2% (low 88.9%, n=697) | 94.4% (low 88.3%, n=107) | 98.4% (low 91.7%, n=64) | config | below the bar on the low bound |
| Auto-place fuzzy (spelling) | 8,080 (10 / 360) | 75.0% (low 71.8%, n=768) | 89.4% (low 77.4%, n=47) | 82.8% (low 65.5%, n=29) | config | not recommended |
| Auto-place near (streets pass within 30 m) | 13,635 (25 / 441) | 16.6% (low 16.0%, n=13,668) | 18.2% (low 8.6%, n=33) | 46.7% (low 30.2%, n=30) | config | not recommended |
| Clue: offset direction picks one of several meeting points | 1,366 (5 / 70) | 49.3% (low 42.5%, n=203) | - | - | code | not recommended (about a coin toss) |
| Clue: jurisdiction (one candidate outside every city) | 96 (0 / 4) | - | - | - | code | negligible |

unique_pair by Caltrans district (gain on the difficult crashes; right intersection on hidden police GPS, self-consistent truth; LAPD open data is District 7, DataSF District 4):

| District | Crashes gained | unique_pair, hidden police GPS | exact tier on the same truth |
|---|---|---|---|
| District 1 | 228 | 84.6% (low 66.5%, n=26) | 88.0% (low 84.7%, n=467) |
| District 2 | 155 | 84.1% (low 70.6%, n=44) | 90.9% (low 87.2%, n=317) |
| District 3 | 465 | 89.7% (low 82.1%, n=97) | 91.0% (low 89.8%, n=2,259) |
| District 4 | 4,522 | 93.0% (low 90.0%, n=385) | 90.2% (low 89.4%, n=5,720) |
| District 5 | 2,535 | 85.2% (low 80.7%, n=291) | 89.2% (low 87.3%, n=1,184) |
| District 6 | 8,499 | 91.9% (low 90.3%, n=1,225) | 88.2% (low 86.6%, n=1,722) |
| District 7 | 63,061 | 93.5% (low 92.6%, n=3,056) | 90.2% (low 89.2%, n=4,342) |
| District 8 | 9,927 | 95.0% (low 93.3%, n=823) | 93.6% (low 92.7%, n=3,560) |
| District 9 | 20 | 88.2% (low 65.7%, n=17) | 82.3% (low 74.2%, n=113) |
| District 10 | 3,174 | 91.8% (low 89.5%, n=670) | 91.8% (low 90.4%, n=1,668) |
| District 11 | 4,313 | 93.1% (low 88.6%, n=189) | 83.0% (low 79.2%, n=441) |
| District 12 | 9,801 | 88.8% (low 86.0%, n=599) | 85.8% (low 83.2%, n=804) |

SF DataSF (where the 98% bar was set): unique_pair placed only 4 test-half crashes (4 right; Wilson low 51.0%). San Francisco's report names don't leave out what OSM writes, so the tier almost never fires there and the bar can't be tested on SF for it. LAPD's open data (Los Angeles: report names without the direction OSM writes) is where the tier is exercised.


## Part A: what's in the bin (main's locator, corrected bins)

285,580 of 2,057,508 CCRS crashes 2021-2025 (13.9%).

| Reason | Crashes | Share of bin | Police GPS present but off the roads |
|---|---|---|---|
| unique pair held by the gate (#201: the two streets meet only once) | 106,707 | 37.4% | 4,190 |
| relaxed match held by the gate | 9,977 | 3.5% | 466 |
| named streets don't meet on the map | 111,475 | 39.0% | 44,005 |
| no cross street (blank, NOT STATED, UNKNOWN, PRIVATE PROPERTY) | 25,114 | 8.8% | 1,962 |
| near / fuzzy match held by the gate | 21,715 | 7.6% | 6,348 |
| streets meet in more than one place | 6,738 | 2.4% | 1,056 |
| no street map for this place | 3,854 | 1.3% | 3,068 |

## Caltrans district

| Caltrans district | Difficult | unique pair | relaxed | don't meet | no cross | near/fuzzy | meet twice+ | no map | GPS off |
|---|---|---|---|---|---|---|---|---|---|
| District 1 | 1,099 | 228 | 34 | 577 | 50 | 56 | 53 | 101 | 592 |
| District 2 | 2,250 | 155 | 67 | 1,536 | 48 | 123 | 71 | 250 | 1,030 |
| District 3 | 13,464 | 465 | 316 | 8,204 | 1,455 | 1,756 | 778 | 490 | 5,789 |
| District 4 | 35,757 | 4,523 | 1,580 | 20,914 | 2,594 | 4,667 | 1,217 | 262 | 11,205 |
| District 5 | 9,518 | 2,535 | 417 | 4,156 | 673 | 633 | 241 | 863 | 2,142 |
| District 6 | 19,257 | 8,499 | 760 | 6,531 | 1,434 | 677 | 256 | 1,100 | 5,622 |
| District 7 | 108,163 | 63,065 | 3,533 | 31,390 | 3,208 | 5,215 | 1,594 | 158 | 15,625 |
| District 8 | 37,862 | 9,928 | 1,294 | 15,989 | 6,696 | 2,931 | 884 | 140 | 8,261 |
| District 9 | 196 | 20 | 0 | 136 | 1 | 0 | 15 | 24 | 163 |
| District 10 | 10,317 | 3,174 | 332 | 3,407 | 2,226 | 718 | 264 | 196 | 2,782 |
| District 11 | 21,159 | 4,313 | 953 | 10,596 | 1,559 | 2,691 | 842 | 205 | 3,736 |
| District 12 | 26,493 | 9,802 | 691 | 8,039 | 5,168 | 2,248 | 523 | 22 | 4,146 |
| unknown | 45 | 0 | 0 | 0 | 2 | 0 | 0 | 43 | 2 |

## Road type

| Road type | Difficult | unique pair | relaxed | don't meet | no cross | near/fuzzy | meet twice+ | no map | GPS off |
|---|---|---|---|---|---|---|---|---|---|
| city street | 224,398 | 105,735 | 9,706 | 68,402 | 23,616 | 11,604 | 5,335 | 0 | 18,377 |
| freeway | 31,521 | 42 | 14 | 24,579 | 665 | 5,826 | 285 | 110 | 30,266 |
| state highway (off freeway) | 19,177 | 927 | 156 | 12,249 | 556 | 4,218 | 776 | 295 | 4,698 |
| county road (outside cities) | 10,484 | 3 | 101 | 6,245 | 277 | 67 | 342 | 3,449 | 7,754 |

## Severity

| Severity | Difficult | unique pair | relaxed | don't meet | no cross | near/fuzzy | meet twice+ | no map | GPS off |
|---|---|---|---|---|---|---|---|---|---|
| fatal | 936 | 278 | 23 | 495 | 33 | 35 | 17 | 55 | 339 |
| serious injury (KSI, not fatal) | 12,327 | 5,586 | 432 | 4,456 | 362 | 766 | 297 | 428 | 2,534 |
| other | 272,317 | 100,843 | 9,522 | 106,524 | 24,719 | 20,914 | 6,424 | 3,371 | 58,222 |

## Top 25 cities (CCRS city name)

| Top 25 cities (CCRS city name) | Difficult | unique pair | relaxed | don't meet | no cross | near/fuzzy | meet twice+ | no map | GPS off |
|---|---|---|---|---|---|---|---|---|---|
| Los Angeles | 41,204 | 29,670 | 1,288 | 7,649 | 202 | 1,730 | 665 | 0 | 2,771 |
| Unincorporated | 12,663 | 2 | 102 | 7,796 | 375 | 1,168 | 616 | 2,604 | 11,908 |
| Long Beach | 9,554 | 6,385 | 192 | 2,516 | 23 | 384 | 54 | 0 | 651 |
| San Diego | 9,186 | 1,370 | 297 | 5,502 | 345 | 1,366 | 306 | 0 | 1,824 |
| Sacramento | 6,299 | 71 | 75 | 4,215 | 709 | 869 | 360 | 0 | 2,321 |
| Lancaster | 5,763 | 3,641 | 38 | 1,766 | 92 | 129 | 97 | 0 | 209 |
| Ontario | 5,323 | 3,781 | 35 | 740 | 435 | 283 | 49 | 0 | 279 |
| Anaheim | 5,122 | 3,701 | 28 | 876 | 204 | 283 | 30 | 0 | 655 |
| San Jose | 4,618 | 775 | 143 | 3,042 | 10 | 554 | 94 | 0 | 1,087 |
| Pasadena | 4,402 | 3,565 | 173 | 560 | 6 | 65 | 33 | 0 | 123 |
| Riverside | 3,996 | 141 | 42 | 1,817 | 1,753 | 168 | 75 | 0 | 1,162 |
| Fresno | 3,513 | 766 | 35 | 1,551 | 1,037 | 93 | 31 | 0 | 827 |
| Oakland | 3,498 | 344 | 371 | 1,544 | 30 | 1,049 | 160 | 0 | 743 |
| Santa Ana | 3,116 | 144 | 67 | 443 | 2,290 | 161 | 11 | 0 | 404 |
| Madera | 2,997 | 1,833 | 267 | 721 | 88 | 70 | 18 | 0 | 187 |
| Fullerton | 2,969 | 2,277 | 10 | 470 | 55 | 129 | 28 | 0 | 343 |
| Glendale | 2,888 | 2,035 | 110 | 395 | 276 | 54 | 18 | 0 | 110 |
| Tulare | 2,663 | 2,225 | 39 | 220 | 72 | 35 | 72 | 0 | 101 |
| San Francisco | 2,618 | 23 | 295 | 1,880 | 10 | 361 | 49 | 0 | 182 |
| Ventura | 2,554 | 1,597 | 117 | 706 | 3 | 103 | 28 | 0 | 336 |
| Stockton | 2,358 | 127 | 11 | 487 | 1,673 | 54 | 6 | 0 | 487 |
| Corona | 2,187 | 606 | 34 | 834 | 507 | 133 | 73 | 0 | 696 |
| La Habra | 2,096 | 1,778 | 42 | 258 | 0 | 11 | 7 | 0 | 2 |
| Oceanside | 2,078 | 664 | 188 | 873 | 15 | 240 | 98 | 0 | 73 |
| San Bernardino | 2,057 | 918 | 65 | 825 | 117 | 95 | 37 | 0 | 555 |

## Top 25 agencies (NCIC)

| Top 25 agencies (NCIC) | Difficult | unique pair | relaxed | don't meet | no cross | near/fuzzy | meet twice+ | no map | GPS off |
|---|---|---|---|---|---|---|---|---|---|
| 1942 Los Angeles + 18 more city names (local) | 38,548 | 29,634 | 1,287 | 5,714 | 178 | 1,076 | 659 | 0 | 84 |
| 1900 Lancaster + 48 more city names (local) | 16,264 | 7,031 | 721 | 6,491 | 530 | 1,140 | 343 | 8 | 2,193 |
| 1941 Long Beach (local) | 9,262 | 6,382 | 191 | 2,336 | 23 | 280 | 50 | 0 | 376 |
| 3711 San Diego (local) | 7,282 | 1,370 | 296 | 4,110 | 148 | 1,058 | 300 | 0 | 28 |
| 3300 Moreno Valley + 29 more city names (local) | 5,969 | 253 | 103 | 2,367 | 2,931 | 223 | 91 | 1 | 715 |
| 3607 Ontario + 3 more city names (local) | 5,031 | 3,783 | 35 | 528 | 435 | 201 | 49 | 0 | 3 |
| 3001 Anaheim + 4 more city names (local) | 4,590 | 3,703 | 28 | 508 | 197 | 128 | 26 | 0 | 140 |
| 3600 Victorville + 13 more city names (local) | 4,530 | 166 | 553 | 2,673 | 154 | 756 | 228 | 0 | 367 |
| 1953 Pasadena (local) | 4,292 | 3,562 | 172 | 462 | 5 | 58 | 33 | 0 | 3 |
| 3404 Sacramento + 3 more city names (local) | 3,979 | 70 | 75 | 2,230 | 592 | 652 | 360 | 0 | 15 |
| 4313 San Jose (local) | 3,821 | 771 | 144 | 2,384 | 8 | 426 | 88 | 0 | 299 |
| 3313 Riverside (local) | 2,943 | 141 | 41 | 829 | 1,738 | 124 | 70 | 0 | 142 |
| 1005 Fresno (local) | 2,908 | 761 | 35 | 972 | 1,033 | 76 | 31 | 0 | 222 |
| 2002 Madera (local) | 2,812 | 1,833 | 267 | 537 | 89 | 69 | 17 | 0 | 0 |
| 1925 Glendale + 3 more city names (local) | 2,806 | 2,035 | 111 | 319 | 277 | 46 | 18 | 0 | 24 |
| 3019 Santa Ana + 6 more city names (local) | 2,773 | 143 | 67 | 250 | 2,285 | 22 | 6 | 0 | 67 |
| 0109 Oakland (local) | 2,744 | 344 | 370 | 1,068 | 27 | 780 | 155 | 0 | 5 |
| 3008 Fullerton (local) | 2,646 | 2,276 | 10 | 236 | 45 | 51 | 28 | 0 | 26 |
| 5406 Tulare (local) | 2,619 | 2,225 | 39 | 177 | 74 | 32 | 72 | 0 | 57 |
| 9550 Unincorporated + 53 more city names (CHP) | 2,564 | 0 | 2 | 2,205 | 51 | 292 | 7 | 7 | 2,521 |
| 3801 San Francisco (local) | 2,452 | 22 | 294 | 1,731 | 8 | 338 | 48 | 11 | 14 |
| 3700 Vista + 9 more city names (local) | 2,436 | 586 | 150 | 995 | 34 | 519 | 152 | 0 | 28 |
| 5600 Thousand Oaks + 7 more city names (local) | 2,411 | 1,193 | 38 | 802 | 210 | 77 | 91 | 0 | 1,137 |
| 3000 Mission Viejo + 13 more city names (local) | 2,390 | 296 | 168 | 1,186 | 0 | 550 | 190 | 0 | 47 |
| 5608 Ventura (local) | 2,285 | 1,592 | 109 | 454 | 2 | 100 | 28 | 0 | 70 |


## Part B: root causes (weighted stratified samples, `tests/statewide/bin2_audit.py`)

Samples: 306 "named streets don't meet" and 255 "police GPS off the roads", stratified by Caltrans district and weighted back to statewide counts. 90 sampled crashes moved to bin 1 with the #199 correction and are left out. Each crash gets one root cause by fixed rules (first match wins), with its evidence in `bin2_audit.csv`.

### Named streets don't meet on the map
| Root cause | Estimated crashes |
|---|---|
| freeway or ramp | 25,952 |
| street missing from the map | 18,098 |
| street outside the city's map | 17,860 |
| house number in the name | 12,354 |
| streets don't intersect | 11,716 |
| streets nearly meet | 6,616 |
| misspelling or abbreviation | 5,217 |
| route number vs street name | 4,987 |
| leading abbreviation (#212) | 3,569 |
| private road or parking lot | 2,550 |
| travel direction in the name | 782 |
| two streets in one field | 154 |

### Police GPS off the roads: the name side
| Root cause | Estimated crashes |
|---|---|
| freeway or ramp | 30,494 |
| streets nearly meet | 7,125 |
| street missing from the map | 6,029 |
| street outside the city's map | 4,944 |
| streets don't intersect | 4,004 |
| house number in the name | 2,302 |
| misspelling or abbreviation | 2,078 |
| private road or parking lot | 1,590 |
| leading abbreviation (#212) | 511 |
| route number vs street name | 487 |
| travel direction in the name | 78 |

### Police GPS off the roads: where the GPS is
| Root cause | Estimated crashes |
|---|---|
| far off (over 1 mile, or the roads aren't on the map) | 36,564 |
| near neither road, within 1 mile | 19,296 |
| near one named road only | 1,138 |
| near both roads, far from where they meet | 256 |

What the audit found:
1. **Freeways and ramps lead both samples.** A freeway crash names the freeway and a cross street, and the two don't share a node. Freeway crashes are left out of corridor studies, and placing them is a different method (postmile / route), so they're a separate decision.
2. **House numbers in a road field** ("BROADWAY & BROADWAY 7346") are addresses, not intersections. The app's address tier (OSM addresses) could place some; that wasn't measured statewide.
3. **"Street outside the city's map"**: the street is in the county but not on the city's clipped network. These are mostly boundary streets, so a buffer around the city network is the fix (not measured).
4. **"Street missing from the map"** is the ceiling for the OSM + TIGER union. On open data the union adds coverage at a slight accuracy cost:
   - LA: placed 90.1% → 93.0%;
   - SF: placed 93.4% → 94.4%, with the low bound 98.0% → 97.9%.
5. **The Tester's own GPS-check bug** (fixed in this PR's first commit) accounted for most of the "GPS near a named road" share. Of the GPS-off crashes left, most have GPS more than a mile from the named roads, which points to coordinate errors.

## Caveats
- The hidden-GPS truth is police GPS that agrees with the report as written (within 400 ft of a meeting point of the two named streets, trailing direction included). It's noisier than open data: the exact tier scores 90.4% here and 99.2% on SF. **Compare a fix with the exact tier on the same truth**, not with 98%.
- Near and fuzzy have no self-consistent truth (the named streets don't meet), so their hidden-GPS figure uses all police GPS that fits the roads: a lower bound.
- The truth sample is up to 200 crashes per city, so it's weighted toward smaller cities, not by crash volume.
- The LAPD open-data test used 2024 truth only (the cached file) and CCRS rows from the Tester's mirror, with no network. SF is Engineering's standard test half.
- Travel direction as a clue (from Parties) wasn't measured. The offset-direction clue is a coin toss, so it isn't recommended.

## Decisions for the user
1. Auto-place unique_pair? This is a gate change: docs/03 sets the 98% bar, which can't be shown on SF for this tier.
2. Build the OSM + TIGER union, and approve TIGER downloads for the other 56 counties?
3. An alias / spelling table from the audit (proposal only; every entry needs your approval)?
4. A method for freeway crashes (postmile / route) and for house-number crashes (address tier)?

Files: `tests/statewide/bin2.py`, `bin2_report.py`, `bin2_audit.py`, `bin2_whatif.py`, `bin2_rank.py`. Results are in `reports/testing/difficult-bin-2026-10-22/`.
