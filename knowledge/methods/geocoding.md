# Placing crashes that have no GPS (issue #1)

Code: `backend/crashiq/{names,osm,locate,jev}.py` · test: `backend/scripts/validate_geocode.py` · unit tests: `tests/`.

## Method (frozen 2026-10-18 on the dev half, then measured once on the test half)
1. **Street network = the reporting agency's jurisdiction only** (OSM boundary by Wikidata id, SF = Q62), named
   roads + named footways/plazas. A bbox let "Bayshore & Main" match Brisbane's Main St (officer meant Marin St).
2. **Normalize names** (`names.street_key`): suffixes, ordinals (07TH→7TH, SEVENTH→7TH), noise (N/B, BLOCK, ramps),
   routes (RT/I/US/SR + number). **Keep leading directionals** — "SOUTH VAN NESS" is its own street; stripping
   it was a bug. Directional-free match only as a relaxed fallback.
3. **Tiers, cheapest first**, each tagged on the crash: `address` → `exact` → `relaxed` (any suffix) → `near`
   (streets pass within 30 m without a shared node) → `fuzzy` (typo, ≥0.88, clear margin) → `jev` → `review`.
4. **Offset along the primary road** in the reported direction (not a straight compass move when the road bends
   away). Offsets matter: median error **2 m with offset vs 38 m without** (542 crashes).
5. **Gate per tier:** a tier may auto-place only if it proves ≥98% (95% lower bound) on held-out data.
   Everything else goes to review, with the best suggestion pre-filled.

## Results, held-out test half — FINAL (run 2026-10-18, `data/results/geocode_sf_test_summary.json`)
SFPD crashes 2023–2025, truth = DataSF by report number, 4,028 test crashes (8,056 linked). Wilson 95% lower bounds.
Cleaning: 12,305 CCRS rows read · 0 CHP-deleted · 5 feet-typed-as-miles fixed · 25 duplicate/blank report numbers
dropped · 18 truth records with unrelated streets dropped.

| Arm (what auto-places) | Coverage | Accuracy (≤250 ft) | Wilson 95% low |
|---|---|---|---|
| **A: exact only (default gate)** | **90.2%** | **98.8%** | **98.3% ✓** |
| B: exact + relaxed + near + fuzzy | 94.1% | 98.5% | 98.1% ✓ (barely; 98.0% on dev) |
| C: exact + Jev on all leftovers | 95.1% | 98.2% | 97.8% ✗ |
| C′: exact + fuzzy + Jev on the rest | 95.2% | 98.2% | 97.8% ✗ |

By tier (test): exact 98.8% (right intersection 99.2%), relaxed 99.0% (n=100), near 73.3% (n=30), fuzzy 89.7% (n=29),
address 81.4% (n=70, vs SF's approximate address truth), review 167.
**Jev vs fuzzy at equal review rate** (docs/03 J1 ship rule), 326 leftovers: fuzzy family 92.5% vs Jev top-159 by p 88.1%.
Jev 1.14 (released 2026-10-14): same 88.1%. → Jev does not beat fuzzy; it does not ship as an auto-placer.
Jev spend: 1.13 run 169 calls, 69,900 input tokens, $0.0029 (5 failed calls); 1.14 run $0.0037. Output tokens are free.

## What didn't work (keep it)
- **SF hidden-GPS test on CCRS crashes with GPS:** wrong population (CHP freeway). Replaced by the DataSF join.
- **Joining on non-unique report numbers** gave unrelated "truth" (3 crashes placed at one point).
- **`near` tier:** 59–67% accurate. Streets that pass close aren't the intersection the officer meant. Not auto.
- **`relaxed` tier:** 95–96%. Close, but under the bar on n≈60. Not auto.
- **Jev on leftovers:** 87–94% and **its probability doesn't separate right from wrong** (higher cut-offs were
  not more accurate). Jev handles typos very well (MISSINO, VALENICA, OCATAVIO…). Most "misses" pick the right
  intersection but the truth has an offset CCRS dropped. Role: one-click suggestion in the review queue.
- **Broader Jev candidates** raised coverage but lowered accuracy (87%).
- Claude on the same leftovers: **not run** (no ANTHROPIC_API_KEY on the machine). Next head-to-head.

## Ideas not yet tried
- Agency open-data join first (SF DataSF, LA open data) where it exists: exact coordinates, no matching.
- Census TIGER address ranges for the address tier (nationwide, public) instead of OSM addresses.
- Give Jev more state: offset/direction, candidate cross-streets, the other crashes at the same street pair.
- Second truth source: TIMS (Berkeley) geocodes; needs the user's login and its terms may limit commercial use.
- Repeat in a second city with a different agency style (LA, San Jose) before trusting the 98% statewide.

## Second city: Los Angeles (LAPD, NCIC 1942), 2026-10-18
- **Link works:** CCRS writes LAPD report numbers as `2401-07452`; LAPD open data (data.lacity.org `d5tf-ez2w`)
  uses `240107452`. Strip the dash. 11,265 of 12,851 LAPD 2024 crashes linked (after hygiene).
- **LAPD truth is snapped to the intersection:** for crashes with a reported offset ≥150 ft, LAPD's point is a
  median 6 m from the intersection and 92 m from the offset point (n=472). So LA truth can only score *which
  intersection* we chose, not the offset. Script scores LA at the chosen intersection (`SCORE_AT_INTERSECTION`).
- **LAPD truth has large geocode errors:** e.g. Canoga Ave & Burbank Blvd: ours at the real intersection
  (34.1733, -118.5974), LAPD 1.6 km away; Burbank & Fulton 5.9 km away; Devonshire & Petit 8 km away. Same
  street names on both sides. 205 of 336 exact-tier "misses" name the same intersection as LAPD.
- **Dev-half numbers (truth-limited):** exact 82.4% within 250 ft of LAPD's point, but the chosen intersection
  agrees with LAPD's street names 93.3%; relaxed 96.1% by names. **LA cannot certify 98% with LAPD truth.**
  Need a better LA truth (TIMS geocodes, or hand-checking a random sample) before any LA claim.
- LA naming differs from SF: more `relaxed` matches (3,027 vs 1,909 exact) because of N/S/E/W halves and
  missing suffixes. Directional halves (N vs S Figueroa) deserve their own handling and test.
- Performance: whole-network scans were too slow for LA (8 min); street index by core added (O(1) lookups).

## The user's original test: hidden GPS, same record (Long Beach PD, NCIC 1941), 2026-10-18
Design: crashes from a police agency that records GPS; hide the record's own lat/long, place from its street
names, compare. No second source. LBPD 2023–25: 13,181 crashes, 96% with GPS; 146 feet-typed-as-miles fixed.
- **Officer GPS is itself noisy.** Only 72.6% of LBPD records have GPS on their own primary street (≤30 m) and
  near their own cross street; ~1.6% are >1 km off (one 446 km, one 1,223 km away). Against raw GPS, no method
  can show 98%: the answer key is wrong several % of the time.
- **Raw GPS, dev half (6,326):** exact 88.6% (44% coverage), all code tiers 85.4% (87%); Jev vs fuzzy at equal
  review rate 77.7% vs 82.1%. Jev spend $0.017.
- **Clean-GPS subset (records whose GPS agrees with their own street names):** exact 97.0% (W95 96.2%, 54% coverage);
  all code tiers 96.2% (98% coverage); relaxed alone 95.3%; exact + Jev 96.1%. **Jev vs fuzzy: 92.6% vs 95.2%.**
- Long Beach writes names without the OSM directional ("7TH ST" for East/West 7th St), so `relaxed` carries 44% of
  crashes there vs ~2% in SF. City writing style changes which tier does the work.
- **Conclusion across SF and Long Beach: Jev does not beat code matching on this task.** Code is the method; Jev
  stays a review suggestion at most. The 98% bar on the clean subset is not yet met in Long Beach (97.0%):
  remaining misses are mostly 100–250 m, worth investigating (offset handling, GPS taken away from the scene).

## The user's geocoding method: weighted clues (2026-10-18, from the user's hands-on experience)
When the user geocoded crashes by hand, they used the approach road and the direction of travel, and when clues
conflicted they **weighted each clue by how hard it is for the officer to get it wrong**: street names (read off
signs) beat direction and distance (often estimated). Design to build (backlog #17):

| Clue | Source in public CCRS | Weight (start) |
|---|---|---|
| Primary / cross street | Crashes: `PrimaryRoad`, `SecondaryRoad` | High |
| Each driver's street (approach road) | Parties: `StreetOrHighwayName` | High |
| Beat / reporting district | Crashes: `Beat`, `ReportingDistrict` (LBPD 2024: 99.5% filled) | Medium |
| Traffic control at the spot | Crashes: `TrafficControlDeviceCode` | Medium–low |
| Each driver's direction and movement | Parties: `DirectionOfTravel`, `MovementPrecCollDescription` | Low–medium |
| Distance and direction from cross street | Crashes: `SecondaryDistance`, `SecondaryDirection` | Low |
| Road character | Parties: `SpeedLimit`, `Lane`, `TotalLanes` | Low |

Score every candidate location; the top one wins only if clearly ahead; otherwise review, showing which clues
disagree. Start weights from the user's judgment, tune them on the hidden-GPS dev half, report on the test half.
**Not in public data:** narratives and sketches (`SketchDesc` = "See Attachment"). Clients (agencies,
consultants) hold the full reports, so "upload your reports, we read the narratives too" is a paid-feature idea.
First puzzle cases: Long Beach Traffic Circle (`E PACIFIC COAST HWY & TRAFFIC CIR`): resolve by each driver's street.

## Clue reliability, measured (Long Beach PD 2023–25, hidden GPS) — `backend/scripts/clue_reliability.py`
Street names scored on all 12,652 GPS records (raw GPS is wrong ~6–10%, so these are lower bounds); every other
clue on 9,207 clean-GPS records. Results in `data/results/clue_reliability_lb.json`.

| Clue | Right | n | Log-odds weight |
|---|---|---|---|
| Beat (matches the beat of its 15 nearest neighbours) | 95.0% | 9,187 | 2.9 |
| Cross street (within 250 ft + stated distance) | 89.2% | 11,692 | 2.1 |
| Primary street (GPS on it, ≤30 m) | 86.8% | 12,096 | 1.9 |
| Driver direction of travel (along the primary, mid-block) | 83.4% | 1,017 | 1.6 |
| Direction of the offset (N/S/E/W within 60°) | 74.6% | 484 | 1.1 |
| Traffic control code vs mapped signal/stop within 40 m | 62.2% | 7,891 | 0.5 (OSM signal gaps count against it) |
| Distance (within 50% or 15 m of the true distance) | 57.8% | 2,483 | 0.3 |
| Each driver's street (Parties `StreetOrHighwayName`) | — | 0 | LBPD never fills it (statewide 2024: 75% of drivers) |

The user's order held (names high, distance/direction low), except **beat ranks highest** and driver direction
higher than expected. Log-odds weights = ln(p / (1 − p)): the naive-Bayes way to add independent clues. Next: score
candidate locations with these weights and test on the hidden-GPS halves (#17). Parties_2025 is download-only
(not in the API), so driver clues cover 2023–24.

## Test 1: weighted-clue scorer (2026-10-18) — no gain over the current rules
`backend/crashiq/clues.py`, `validate_geocode.py --method scored`. Candidates = every plausible intersection; points
= primary 1.9 + cross street 2.1 (scaled by match quality) ± beat 2.9, beat territory learned from the *other* half.
Dev halves; current rules (all tiers) as the comparison.

| | Current rules | Scorer, names only | Scorer, names + beat |
|---|---|---|---|
| SF, at the 98% bar (Wilson low ≥ 98%) | 94.4% placed / 98.5% | 94.7% / 98.5% | 94.6% / 98.6% |
| Long Beach, at the same coverage (~88%) | 88.0% / 85.6% | 88.7% / 84.7% | 88.6% / 84.1% |
| Long Beach, at the same accuracy (~85.7%) | 88.0% | 85.4% | 81.2% |

- **No gain.** Our rules already use the names well; the scorer only adds a dial (SF: 97.4% placed at 97.5%).
- **Beat made Long Beach worse**, although beat agrees with neighbours 95% of the time: the candidates being
  decided between are usually in the *same* beat (no help), and near beat boundaries a noisy beat map (learned from
  officer GPS, 27% inconsistent) vetoes the right answer. Beat may still help the specific "streets meet twice far
  apart" case; not tested separately.
- Lesson: a clue being reliable ≠ a clue being *useful*. It has to separate the candidates actually in contention.

## Test 2: two maps (OSM + TIGER) — small, real gain
`validate_geocode.py --network both`. Dev halves, all code tiers.

| | SF placed / accuracy (W95 low) | Long Beach placed / accuracy |
|---|---|---|
| OSM only (today) | 94.4% / 98.5% (98.0%) | 88.0% / 85.6% |
| TIGER only | 93.9% / 98.4% (98.0%) | 87.7% / 85.1% |
| **Union** (OSM, TIGER where OSM can't) | **95.5% / 98.3% (97.9%)** | **90.0% / 85.2%** |
| **Consensus** (both agree ≤250 ft) | 92.7% / **98.7% (98.3%)** | 85.2% / **86.0%** |

Maps disagree rarely (SF 7 crashes, LB 31). Union = +1–2 points placed at about the same accuracy; consensus =
fewer placed, slightly more accurate. Both are cheap (TIGER is a free download per county).
