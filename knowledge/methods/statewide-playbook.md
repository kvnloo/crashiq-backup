# Playbook: getting a state's crashes on the map

Written 2026-10-23 from California, brought up to date 2026-11-01. CCRS 2021–25: 2,057,508 crashes. Coverage:
- run 8: 92.6% on the map;
- run 10 (#295): **93.48%** (fatal 97.76%, KSI 94.28%);
- CrashIQ's street-name placements (exact + unique_pair) are at the right intersection 92.4% of the time on hidden police
  GPS (low 92.1%, C9);
- the exact tier agreed with San Francisco's own crash data 98.7% of the time (#16, 2026-10-18 basis).

This is the order that worked, so the next state doesn't repeat the learning. Each step links to its evidence.
Decisions behind each rule are in docs/03; this file is the how.

**Keep it current:** every PR that changes how crashes are placed, counted or rated updates this file, or the method
file it links to, in the same PR.

## 1. Freeze the basis before measuring anything
- Mirror the crash tables locally, pin the street-map extract date, and state the code commit on every result.
- Every comparison uses the same basis (docs/03, 2026-10-19). A completeness guard checks the crash count is identical
  in every stage. Reconcile each change as an effect ("+N onto the map, these moves"), never just before/after headlines.
- Check which copy of the crash table you have. The CA live table has 74 data columns; our first mirror had 30 and
  hid fields we later needed (Milepost*, IsHighwayRelated). Pull the full schema once (#253).

## 2. Police GPS first: repair it, then trust it when it fits — `reports/testing/gps-profile-2026-10-22.md`
In CA, 73% of everything on the map sits on the officer's own GPS. Check per agency and year:
- **Degrees-minutes-seconds written as decimal.** Minutes/seconds digits < 60. San Jose 63% of its points; also many
  CHP areas. Convert per crash only when exactly one reading fits the report's roads (#143; statewide #247/#251:
  4,111 crashes, chance control 0.7%).
- **Missing minus on longitude** (432 CA crashes, chance 0.78%). Try it before dropping a point as out of state (#247).
- **Shared default / dispatch points** (1,755 crashes on 50 points, e.g. one CHP point near Auburn with 333 crashes) and
  **coarse coordinates** (≤ 2 decimals): treat as no GPS (config/gps.json). Don't use an OR of coarse rules: it would
  have dropped 1,396 good points (#225).
- **Don't** shift latitude by whole degrees: it fits by chance as often as the real repair (2026-10-23).
- Accept GPS only when it fits the report's own roads (400 ft + the stated offset). When it sits at the intersection
  but the report says N ft away, use the report's offset (#218).
- **When the GPS fits, keep it. Don't move it** to where the report's distance points (user 2026-10-25). On freeways the
  CHP postmile sided with the GPS and with the report about equally (568 vs 514); in the user's own review the officer
  GPS was right every time. How officers capture GPS: `sources/ca-police-gps-capture.md`.
- **The fit check needs the report's street names to read correctly.** If the cleaner misses a spelling or a wording
  form, a good GPS is rejected (see step 5, D3).

## 3. Place the crashes without usable GPS — `methods/geocoding.md`
- Street network = the reporting agency's area (city box + 1 km), not a clipped outline: county pockets and boundary
  streets matter (+23,467 crashes in run 8).
- **Two maps:** OSM, plus Census TIGER where OSM lacks the street (#250 fix, #258: +4,965 in run 9C, 3 left the map).
  A TIGER-only road match doesn't auto-place on its own (`tiger_only_auto` off; 74.9% accurate).
- Normalize names:
  - keep leading and trailing directions;
  - expand leading abbreviations (AVE M = Avenue M, #212);
  - apply the cleaner rules of #242 (PKY/PW, EXPWY, HW, TRL, RT as a trailing word, JR, CYN, MTN, HTS);
  - route suffixes such as "PACIFIC COAST HWY - SR1" and "BEACH BL - SR39 BLVD";
  - more wording forms in #305 ("STATE HIGHWAY 96", "W CURB LINE OF …", two streets in one field).
  - a bare route in a freeway report ("405 SB", "99 HWY", "1-15 S/B" for I-15) is that route, read only for the
    corridor's own route (#334); never a house number, a numbered street or a number alone.
- Tiers that auto-place: **exact** and **unique_pair** (the two streets, allowing only what the report leaves out, meet
  once). unique_pair added +108,547 crashes at accuracy equal to or better than exact.
- **Alias table** of local spellings, city-scoped, every entry approved by the user (912 in CA,
  `data/reference/street_aliases.csv`). Build it from the difficult-bin audit, with a GPS check per entry. A second
  batch from D3 spellings near the GPS: #306.
- **Approximate tiers** (labelled, counted on the approximate side of coverage, never at an intersection):
  - freeway, from the report: "usually within 0.5 mi" (`methods/freeway-crashes.md`);
  - house-address crashes (D5) at USDOT NAD address points: "usually within 400 ft" (86.1% on police GPS). Where NAD
    doesn't cover, the crash goes to review with the Census/TIGER address-range point as a suggestion (#264, #283).
- **Mile markers (D3, user 2026-11-01, #319; off until measured):** "ANGELES CREST HWY & MILE MARKER 28.86" at that
  Caltrans postmile on the route the other field names (else the corridor's route), in the crash's county,
  interpolated between tenth points, plus a stated distance along the route (`mile_marker.py`). Two places for one
  postmile (a realignment prefix the report leaves out), or none, go to review with the reason. While off, the point
  is the review list's suggestion. First look (Engineering, 2026-11-01, 226 CCRS crashes with police GPS and a route
  number): median 375 ft from the GPS, 53.5% within 0.1 mi, 87.6% within 1 mi, so CHP's markers are often not
  Caltrans postmiles (signed miles, or rounded). Tester measures before any switch-on.
- **Railway and trail crossings (D3, user 2026-11-01, #318; off until measured):** "FRANCIS ST & RAIL ROAD", "MANGO
  AVE & PACIFIC ELECTRIC TRL": where the corridor crosses that railway (any railway when the report just says
  railroad) or that named trail or path (`crossings.py`), from OSM railway=rail/light_rail/tram/subway and named
  highway=cycleway/path/footway, kept apart from the street graph. A stated distance is walked along the path in the
  stated direction. Two or more crossings, or none, go to review with the reason, never the nearest guess. A bike
  lane on the road is the road ("BIKE LANE" is dropped from the name). A crash on a separate bike-only path is placed
  on the path itself (user 2026-11-01, #331; `crossing_on_path`).
- **Fatal crashes:** FARS coordinates as a fallback, only when the FARS point fits both named roads. FARS beats an
  approximate placement (#280/#281).
- **Freeway crashes:** `methods/freeway-crashes.md`. In short:
  - mainline = where the cross street crosses, plus the stated distance;
  - ramp = at the ramp terminal;
  - "X TO Y" with a local cross street = X's main lanes (approximate);
  - true connectors (cross street = X or Y) go to review;
  - roads over or under a freeway aren't intersections (N7, #67).
- **Postmile:** each placed state-highway crash gets a derived postmile from the Caltrans postmile layer (#248). It's
  needed for traffic volumes and rates; it doesn't change placement.

## 4. Measure every change the same way
- Truth: an agency's own open data joined by report number (SF, LA, San Jose, Pasadena) first, then hidden police GPS,
  **only on GPS that agrees with the report** (self-consistent truth). Officer GPS often sits at the intersection.
- Accuracy per tier with a Wilson 95% lower bound; 98% bar for a tier to auto-place unless the user decides otherwise.
  Below the bar, a tier can still be approximate if the user approves the label (freeway 0.5 mi, NAD 400 ft).
- Every repair gets a chance control (shift the point randomly, count how often the "repair" still fits).
- No-change proofs run every corridor in tests/statewide/corridors_frozen.json; report every crash whose placement or
  assignment changes.
- Claims that reach the website go in `knowledge/claims.md` with their run and basis.

- **Freeway corridors (#328, #329):** a freeway corridor is its motorway ways only (#325). Its buffer is measured
  from every motorway way of its route within 150 m, both carriageways, not only the drawn line; the study limits
  still come from the drawn line. With no at-grade intersections, its known crossings are its grade separations: a
  no-GPS report naming another cross street is off the stretch.

## 5. Sort what's left into named buckets, largest first
CA after run 10 (#295; 134,249 difficult crashes):
- D3 street missing from the map: 26,631;
- D2 no cross street: 25,403;
- D1 freeway / ramp: 19,214 (4,704 with GPS off their roads, not in the app; 155 connectors in review);
- D6 named streets don't cross: 15,172;
- D7 spelling held (not auto-placed): 13,775;
- D5 house number: 12,568;
- D4 near-miss streets: 11,556;
- D8 streets meet in more than one place: 7,841;
- D9 no street map for the area: 2,086;
- newly difficult: 3.

Fatal / KSI per bucket: D3 155 / 1,424 · D1 60 / 605 · D5 44 / 487 · D9 36 / 330 · D6 36 / 754 · D2 33 / 400 ·
D4 26 / 454 · D8 22 / 389 · D7 21 / 625. The user has prioritised by these.

For each bucket: pull 5–20 real records, have the user place them by hand and explain the clues, turn that into a
rule, build it behind a gate, measure, then the user approves.

**Before writing a rule, split the bucket by GPS** (Tester, D3, 2026-10-31). D3's 26,631:
- 78% have no usable GPS at all;
- 10% have GPS outside the reported city or county;
- 12% (3,156) have GPS in the right city or county. Up to ~700 of them failed on spelling and up to ~700 on wording
  (the two overlap and are upper bounds, to be confirmed by #305/#306). The rest have GPS 400+ ft from the named
  street (1,285) or neither name on the map within about 1 mi (1,162).

The first two groups need a non-GPS method; the third is fixed in the name cleaner and the alias table (#305, #306).

## 6. Crash rates on state highways — `sources/ca-caltrans-traffic-census.md`
- **Exposure:** the state DOT's traffic census. In CA, Caltrans AADT by route, county and postmile (back and ahead
  legs), truck AADT by axle, and ramp ADT by district. Each crash joins through its derived postmile. Count years
  2016–2024 (#345); a window year before the oldest count has no rate, and the caveat names the year.
- **Join rules** (#289):
  - the nearer count point's facing leg, split at the midpoint;
  - 0.05 mi tolerance at a line's ends;
  - never bridge a blank AHEAD (a route break);
  - never measure across a postmile prefix change;
  - an honest User-Agent on downloads.
- **Calendar years:** a count year runs October–September, so a calendar year = 0.75 × that count year + 0.25 × the next.
- **Coverage:** a segment-year gets a rate only when every 0.05 mi sample has a count; never a partial guess.
- **Which crashes count** (user 2026-10-31, #297): a mainline rate counts the highway's own mainline crashes only.
  - **GPS on the freeway line is not proof of mainline.** Ramp and cross-street crashes at interchanges often carry
    GPS on or beside the line. Classify by the report's road wording (`backend/crashiq/rate_class.py`, #304):
    - a ramp named, or "<route> <dir> TO <local street>" (= the <dir> off-ramp to that street), or "<local street>
      TO <route> <dir>" (= the <dir> on-ramp from that street, user 2026-11-01, #331), or a connector
      "<route> TO <route>" whose cross street is one of the routes → ramp (rated in the ramp table; a connector
      gets no ramp rate);
    - "<route> TO <route>" with a local cross street → mainline;
    - the highway as the primary road → mainline. On a conventional highway, the highway as the secondary road
      with the distance blank or within the study's influence radius (250 ft) → mainline too (an intersection
      crash, user 2026-11-01);
    - any other primary road (a cross street, a frontage road) → in no rate; on a freeway, always.
  - An intersection's mainline crashes count in the segment on their GPS side; with no GPS, or GPS within 25 ft of
    the intersection, the segment after it; the last intersection, the segment before (user 2026-11-01).
  - Ramps are rated separately, by a strict match to one ramp row, else the engineer picks (#300). A year's ramp
    count is the latest at or before it; one more than 5 years older than the year gives no rate (user 2026-11-01).
- **Small numbers:** under 10 crashes, show counts and mark the rate "too few to compare" (#271).
- **Statewide comparison:** the rate group is entered by the engineer, or read by code from the DOT file they attach.
  Never guessed, and never read by AI (#294, #298).
- **What the crash file can't tell you:** the DOT's own crash list may drop "associated with" crashes and suicides;
  CCRS has no field for these. Say so wherever a rate is compared with the DOT's.

## What did not work (don't retry without new evidence)
| Idea | Result |
|---|---|
| Auto-placing `near` (streets pass within 30 m) | 16.6% right on hidden GPS |
| Auto-placing `fuzzy` (spelling) | 75.0% |
| Offset direction to pick between meeting points | 49.3%, a coin toss |
| Jev (LLM) as an auto-placer | 88.1% vs fuzzy 92.5% at the same review rate |
| OSM + TIGER union as first built (#17) | lost correct OSM placements (statewide −525 net). Fixed in #250/#258 (TIGER only where OSM can't), now on |
| TIGER-only road matches (`tiger_road`) as auto | 74.9% (low 70.3%, n=386) vs OSM 90.0%; review only |
| "GPS right, names wrong" as a general rule | 2 of 200 (1%) on the run 8 sample. D3 (2026-10-31) shows the names were *misread*, not wrong: fix the reading, don't trust GPS blindly |
| Whole-degree latitude repair | chance |
| Accepting GPS that is merely on the named freeway | ~1 in 5 by chance |
| Moving fitting officer GPS to the report's spot (`freeway_move_gps`) | replaced by "keep the GPS" (user 2026-10-25) |
| Auto-placing true freeway-to-freeway connectors | 81.5% within 0.5 mi (n=65); review instead |
| libpostal / usaddress / USPS table vs our normalizer | ours better (`tools.md`) |
