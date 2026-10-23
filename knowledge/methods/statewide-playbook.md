# Playbook: getting a state's crashes on the map

Written 2026-10-23 from California (CCRS 2021–25, 2,057,508 crashes → 92.6% on the map after run 8; fatal 97.3%,
KSI 93.3%). The order that worked, so the next state doesn't repeat the learning. Each step links to its evidence.
Decisions behind each rule are in docs/03; this file is the how.

## 1. Freeze the basis before measuring anything
- Mirror the crash tables locally, pin the street-map extract date, and state the code commit on every result.
- Every comparison uses the same basis (docs/03, 2026-10-19). A completeness guard checks the crash count is identical
  in every stage. Reconcile each change as an effect ("+N onto the map, these moves"), never just before/after headlines.

## 2. Profile the police GPS per agency (cheap, big wins) — `reports/testing/gps-profile-2026-10-22.md`
Check, per agency and year:
- **Degrees-minutes-seconds written as decimal.** Minutes/seconds digits < 60. San Jose 63% of its points; also many
  CHP areas. Convert per crash only when exactly one reading fits the report's roads (#143, #247).
- **Missing minus on longitude** (432 CA crashes). Try it before dropping a point as out of state (#247).
- **Shared default / dispatch points** (1,755 crashes on 50 points, e.g. one CHP point near Auburn with 333 crashes) and
  **coarse coordinates** (≤ 2 decimals): treat as no GPS (config/gps.json). Don't use an OR of coarse rules: it would
  have dropped 1,396 good points (#225).
- **Don't** shift latitude by whole degrees: it fits by chance as often as the real repair (2026-10-23).
- Accept GPS only when it fits the report's own roads (400 ft + the stated offset). When it sits at the intersection
  but the report says N ft away, use the report's offset (#218).

## 3. Place the crashes without usable GPS — `methods/geocoding.md`
- Street network = the reporting agency's area (city box + 1 km), not a clipped outline: county pockets and boundary
  streets matter (+23,467 crashes in run 8).
- Normalize names: keep leading and trailing directions; expand leading abbreviations (AVE M = Avenue M, #212); the
  cleaner rules of #242 (PKY/PW, EXPWY, HW, TRL, RT as a trailing word, JR, CYN, MTN, HTS).
- Tiers that auto-place: **exact** and **unique_pair** (the two streets, allowing only what the report leaves out, meet
  once). unique_pair added +108,547 crashes at accuracy equal to or better than exact.
- **Alias table** of local spellings, city-scoped, every entry approved by the user (912 in CA,
  `data/reference/street_aliases.csv`). Build it from the difficult-bin audit, with a GPS check per entry.
- Fatal crashes: FARS coordinates as a fallback, only when the FARS point fits both named roads.
- Freeway crashes: `methods/freeway-crashes.md`.

## 4. Measure every change the same way
- Truth: an agency's own open data joined by report number (SF, LA, San Jose, Pasadena) first, then hidden police GPS,
  **only on GPS that agrees with the report** (self-consistent truth). Officer GPS often sits at the intersection.
- Accuracy per tier with a Wilson 95% lower bound; 98% bar for a tier to auto-place unless the user decides otherwise.
- Claims that reach the website go in `knowledge/claims.md` with their run and basis.

## 5. Sort what's left into named buckets, largest first
CA after run 9A (145,237 difficult crashes): D3 street missing from the map 29,207 · D2 no cross street 25,720 ·
D1 freeway / ramp reference 24,076 · D6 named streets don't cross 16,145 · D7 spelling held (not auto-placed) 15,026 ·
D5 house number as location 12,819 · D4 near-miss streets 11,734 · D8 streets meet in more than one place 7,987 ·
D9 no street map for the area 2,523.
For each bucket: pull 5–20 real records, have the user place them by hand and explain the clues, turn that into a
rule, build it behind a gate, measure, then the user approves.

## What did not work (don't retry without new evidence)
| Idea | Result |
|---|---|
| Auto-placing `near` (streets pass within 30 m) | 16.6% right on hidden GPS |
| Auto-placing `fuzzy` (spelling) | 75.0% |
| Offset direction to pick between meeting points | 49.3%, a coin toss |
| Jev (LLM) as an auto-placer | 88.1% vs fuzzy 92.5% at the same review rate |
| OSM + TIGER union as built (#17) | lost correct OSM placements (SF lost 35, 33 of them right, gained 11; LA lost 66, 63 right, gained 22, 19 right); statewide −525 net; off (#245), redo in #243 |
| TIGER-only road matches (`tiger_road`) as auto | 74.9% (low 70.3%, n=386) vs OSM 90.0%; review only |
| "GPS right, names wrong" | 2 of 200 (1%); not a pattern |
| Whole-degree latitude repair | chance |
| Accepting GPS that is merely on the named freeway | ~1 in 5 by chance |
| libpostal / usaddress / USPS table vs our normalizer | ours better (`tools.md`) |
