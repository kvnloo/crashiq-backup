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
