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

## Results, held-out test half (2,655 SFPD crashes, truth = DataSF by report number)
| Tier | Share | Within 250 ft | 95% low | Right intersection |
|---|---|---|---|---|
| exact (auto) | 91.0% | 98.7% | **98.1% ✓** | 99.4% |
| jev (suggestion only) | 5.0% | 94.0% | 88.7% | 80.5% |
| address (user decision) | 1.7% | 77.3%* | — | — |
| review, no suggestion | 2.3% | — | — | — |
*vs. DataSF's own approximation of the address, so understated.
Dev half: exact 99.0% (low 98.5%). Jev cost all night: < $0.01.

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
