# Lessons (newest first)

- 2026-10-31 · A bucket named "street missing from the map" (D3, 26,631) was mostly crashes with **no GPS** (78%). Of the
  3,156 with GPS in the right city, the GPS was usually fine and failed only because the report's names didn't read:
  spelling ~700 (CHESEBRA = Chesebro, TEHON = Tejon), wording ~700 ("BEACH BL - SR39 BLVD", "STATE HIGHWAY 96", "W CURB
  LINE OF …"). Split every bucket by GPS before designing a rule (Tester; #305, #306).
- 2026-10-31 · GPS on a freeway line doesn't make a crash a mainline crash. CHP writes off-ramp crashes as "I-10 E/B TO
  <street>" with no "ramp", and cross-street crashes at interchanges carry GPS beside the line. For rates, classify by
  the report's road wording (user decision #297, #304).
- 2026-10-31 · "X TO Y" means different things: "<route> TO <local street>" as the road = an off-ramp; "<route> TO
  <route>" with a local cross street = the first route's main lanes (2026-10-25); with a route as the cross street = a
  true connector (review). Check earlier decisions before writing a new reading (#303 had to be corrected).
- 2026-10-29 · Caltrans district crash-data memos (TASAS Table B) give rate groups and average rates per segment and
  ramp. Read them with a deterministic parser, never AI (#298).
- 2026-10-26 · Caltrans count years run October–September: a calendar year = 0.75 × count year + 0.25 × next. The 2023
  AADT workbook repeats 2022 values on some segments; the table says which year was used (#289).
- 2026-10-26 · Caltrans AADT: never bridge a blank AHEAD leg (route break) or measure across a postmile prefix change
  (R, M …); 0.05 mi tolerance at line ends (#289).
- 2026-10-25 · NAD address points place house-address crashes within 400 ft of police GPS 86.1% of the time, but NAD covers
  only 10 CA contributors (647 of 12,568 D5 crashes). Elsewhere: review with the Census/TIGER suggestion (#277, #283).
- 2026-10-25 · On freeways, keep officer GPS that fits. The CHP postmile tie-breaker sided with GPS and with the report
  about equally (568 vs 514), and the user's three hand reviews all favoured the GPS (#262).
- 2026-10-25 · CHP's manual (HPM 110.5 ch. 3, Apr 2021) makes GPS the main crash location and the postmile a fallback
  "if GPS coordinates cannot be collected"; not required on ramps or connectors. An empty `Milepost*` is expected, not a
  quality signal. Source: `sources/ca-police-gps-capture.md`.
- 2026-10-25 · CHP GPS may be a scene fix or a point picked later on a map (MDC, Streets and Trips, Google Earth "upon
  return to their local Area office"). A GPS sitting exactly on the reference crossing is likely a map click: trust the
  report's measured offset there.
- 2026-10-25 · CHP replaced its report software (CARS → Crash Manager) in 2020–21. Our biggest statewide pile points
  (Auburn, downtown Sacramento) appear only in 2021–22: likely software defaults (unconfirmed). Find piles by rule each year.
- 2026-10-25 · SFPD and San Jose place crashes from street names/intersections in their own systems; their open data
  (DataSF, San Jose `crash-locations` with `TCRNUMBER`) is better truth than CCRS lat/long for them.
- 2026-10-23 · Freeway crashes are described by a reference street that crosses over or under the freeway, plus a
  distance along it. They never "intersect", so 24,076 sat unplaced (D1). Method: `methods/freeway-crashes.md`.
- 2026-10-23 · `IsFreeway = True` is freeway jurisdiction, not the main lanes. "I-680 S/B TO SR-4" is a crash on the
  connector ramp (Martinez 1428399, confirmed by the user).
- 2026-10-23 · Read report fields literally. The user misread S as N, and a connector as mainline, on first pass.
  A rule that reads the fields as written beats intuition.
- 2026-10-23 · On freeways the report beats the officer's GPS when they disagree (Lawndale GPS at the crossing's
  corner, report 200 ft S; Stockton GPS inside a parcel).
- 2026-10-23 · A repair that "fits" needs a chance control. DMS repair fits 55.6% vs 0.7% control (real, 4,111 crashes);
  missing longitude minus 74% vs 0.78% (real, 432); whole-degree latitude shifts ±1° 1.5% vs 2.1% (pure chance).
- 2026-10-23 · Landing on the named freeway is weak evidence: a 2 km random shift still lands on it 7.7% of the time,
  so ~1 in 5 of 5,894 "fits" are chance. Require agreement with the report's spot, not the road.
- 2026-10-23 · Check the live schema, not the mirror. Our CCRS mirror keeps 30 of 74 crash columns, and the PM told
  the user "CCRS has no postmile field" from it. The live table has `Milepost*` fields: real CHP postmiles, but on only
  2–4% of 2021–22 freeway crashes and ~0 from 2023. TASAS postmiles are assigned later by Caltrans; a postmile can still
  be derived for output from the public Caltrans layer (#248).
- 2026-10-23 · Write coordinates with an ASCII hyphen. A typographic minus (U+2212) made the user's Google Maps
  searches fail.
- 2026-10-22 · Name the leftovers. Sorting the difficult bin into buckets (D1–D9) and having the user place 3–20 real
  records by hand turned a vague 7% into concrete rules (playbook step 5).
- 2026-10-22 · A second street map can lose correct placements: the OSM + TIGER union added TIGER copies that created
  false meeting points (SF lost 35 placements, 33 of them right, and gained 11; LA lost 66, 63 right, gained 22, 19
  right; statewide −525 net, #243). TIGER-only road matches are 74.9% right vs OSM 90.0%: review only. Gate a new source by "no correct placement
  lost", not by net gain.
- 2026-10-22 · unique_pair (the two streets meet exactly once, allowing only what the report leaves out) placed
  +108,547 crashes at 92.4% vs exact 90.4% on hidden GPS, and 97.0% vs 95.7% on LAPD open data. Biggest single win.
- 2026-10-22 · "GPS right, names wrong" is rare: 2 of 200 random cases. Freeway distance, offsets and off-street GPS
  explain the rest. Check a plausible story with a random sample before building for it.
- 2026-10-22 · Clipping a city's street network to its outline loses county pockets and boundary streets: city box
  + 1 km recovered 23,467 crashes. A harness artefact can look like a data problem.
- 2026-10-22 · Default/dispatch points pile crashes onto one coordinate (one CHP point near Auburn: 333 crashes from
  59 areas). Find piles by pooling all agencies, then treat them as no GPS.
- 2026-10-22 · An OR of "coarse coordinate" rules would have thrown out 1,396 good points (#225). Test each rule's
  false positives on GPS that fits the report before adopting it.
- 2026-10-21 · FARS overrode locator placements until #192. A fallback source must only fill gaps, and its point
  must fit both named roads.

- 2026-10-20 · Officer GPS is a weak answer key for offsets: it usually sits at the intersection even when the report
  says hundreds of feet away (Concord: 92% of exact matches right at the intersection, 73% after the stated offset).
  Score the matcher at the intersection, and only on GPS that agrees with the report's own streets (agencies run
  68–90%; San Jose 0.2% because its GPS is DMS, #143). On that basis relaxed matches score like exact ones in most
  agencies (median difference −0.05 points across 84 agencies), which is evidence for the gate decision, not a decision.
- 2026-10-20 · A systematic GPS error shows up as a constant offset against a second source: San Jose's points were
  a median 34 km off, then 80 m after reading them as degrees-minutes-seconds. Check digit patterns (minutes and
  seconds < 60) per agency before trusting GPS.

- 2026-10-20 · CHP's PCF category depends on the subsection, not just the section (21453(a) signals, (c) right of
  way, (d) pedestrian), and CHP extended its own table in 2024 (sections that were 00 "unknown" in 2021–23 got real
  categories). A crosswalk must key on section + subsection and be checked by year (#52, pcf_categories.csv).
- 2026-10-20 · TIMS CASE_ID = 1 digit + CCRS Collision Id for 8-digit IDs; 7-digit IDs (LAPD, LASD, Long Beach) need
  agency + time + roads (#88). The built-in browser doesn't save downloads, but the page can fetch and process them.

- 2026-10-20 · A coverage % is only as good as its denominator. Run 1 counted GPS crashes the assignment later
  excluded (Canada Blvd beside a Verdugo Rd corridor) as "located", so it read 95.8%; on crashes that actually count
  for the corridor it was 91.3%, and 65.0% in run 2 once the fixes found 10,600 reports run 1 silently missed.
  Measure coverage on what the study counts, and version the measure when it changes (#73 run history).
- 2026-10-20 · A test's own name matching must not borrow the app's. Run 1's independent check used the app's
  street cores, so it shared the leading-direction blind spot (#113) and called Glendale and Pasadena fine.
- 2026-10-20 · Substring matching on squeezed names needs a stop list: `NOT STATED` contains `STATE`, so every
  no-cross-street report named "State Street" (Santa Barbara, 6,136 junk rows from four counties, #121).
  Fix: short names (≤ 6 letters) as whole words, long names squeezed (CHP splits MC FADDEN), placeholders never a street.
- 2026-10-20 · With parallel workers, every collector must read every worker's database. Run 1's history read 2 of 3
  and under-counted payload measures by a third; corrected openly in the row's note.
- 2026-10-19 · Test fixtures must be recorded from live data. The synthetic fixture spelled injury levels as phrases;
  live CCRS uses codes (`SuspectSerious`…), so every A/B/C crash became U and nobody noticed (#75/#79, fixed in #76). Same for a hyphen in
  an OSM street name: Union City lost 48 of 51 no-GPS corridor reports (#80). Only a run on real data found either.
- 2026-10-19 · A collapse in an agency's yearly report count looks exactly like a safe city. 61 local agencies fell
  under half their 2016–19 level in some year since 2021 (Gardena ~5 a year since 2022). TIMS can't catch it: same
  records. Compare every agency with its own history before trusting a count.
- 2026-10-19 · Overpass sometimes answers a valid query with 0 elements and no error (7 of 14 calls in one burst). Never
  cache an empty answer (#84).
- 2026-10-19 · A local SQLite mirror of the CCRS datastore runs the app's own SQL unchanged (the SQL is kept to the
  PostgreSQL/SQLite common subset): 2M crashes, ~1 GB, built in 3 minutes. Use it for any statewide test instead of
  thousands of live queries (`tests/statewide/ccrs_mirror.py`).
- 2026-10-19 · An offline stand-in must behave like the real service, or tests pass on nothing. FakeCkan built
  untyped SQLite columns, so `"County Code" IN ('1')` never matched the number 1 (PostgreSQL casts it): every
  no-coordinate row of a live fixture vanished, and Union City replayed 0 crashes while all its golden checks
  "passed" (empty sets). Guard: the golden suite asserts the replay returns every recorded crash (#53).
- 2026-10-19 · CCRS writes one Vehicle Code violation several ways (22350 / VC 22350; 21658A / VC 21658(A) /
  21658(a)), which splits one cause across rows of a PCF table. Normalized to one spelling per section (#53).
- 2026-10-19 · CHP's data dictionary is not what CCRS publishes. The dictionary lists injury text ("SUSPECTED SERIOUS
  INJURY"); the live `ExtentOfInjuryCode` holds codes (SuspectSerious, ...) plus retired SWITRS levels
  (SevereInactive, OtherVisibleInactive, ComplaintOfPainInactive). Matching on the dictionary dropped every A/B/C
  injury on live data while all tests passed on a hand-built fixture (#75). Always test against recorded LIVE rows
  (`tests/fixtures/live/`), not only fixtures written from the documentation.
- 2026-10-19 · A corridor street can change name at a city line, and each police department writes its own name:
  Union City Blvd is Ardenwood Blvd in Fremont, so Fremont PD's crashes at Rancho Dr and Paseo Padre Pkwy (both on
  the drawn corridor) were never searched. Match every name and ref OSM gives the corridor's ways, not just the
  most common one (#53). Union City study: 21 → 30 intersection crashes.
- 2026-10-19 · Live CCRS publishes one row per Collision Id (2016–2026, every year checked): only the latest report
  version is in the table (versions go up to 1,326), and `IsDeleted` is never true, so deleted reports are removed,
  not flagged. IWP rows are unique by `InjuredWitPassId`. The dedupe/version code is a safeguard, not a live fix (#53).
- 2026-10-18 · Git must never touch the live database. A `git stash` + checkout restored a stale, committed
  `data/crashiq.sqlite-wal`, and SQLite replayed it into the db and corrupted it. Recovered with `sqlite3 .recover`
  (backup in `data/backup/`), corrupt cache rows deleted and re-pulled. `*.sqlite-wal` / `*.sqlite-shm` are now
  untracked and ignored (#35, PR #36). Side effect: the user's Union City corridor came back wrong and was redrawn.
  With several sessions running, each works in its own worktree and never switches branches over `data/`.
- 2026-10-18 · Parallel sessions built the same thing twice (#40 vs #44, #46 vs #42/#51) because the stack was based on
  an old main. Before building, check open and merged PRs and claim the issue (CLAUDE.md).
- 2026-10-18 · A reliable clue is not automatically a useful one: beat is right 95% of the time but did not help (Long Beach got worse), because the candidates in contention share a beat. Test whether a clue *separates the candidates*, not just whether it is true.
- 2026-10-18 · Two maps (OSM + TIGER) add 1–2 points of coverage at the same accuracy; the remaining misses are in the records, not the maps.

- 2026-10-18 · Officer GPS is not ground truth either: only 73% of Long Beach PD records have GPS consistent with their own street names; some are hundreds of km off. Check record self-consistency before using GPS as an answer key.
- 2026-10-18 · Hidden-GPS test in a second city (Long Beach) agrees with SF: Jev loses to code matching at equal review rate (92.6% vs 95.2% on clean GPS). Code is the method.

- 2026-10-18 · A city's open data is not automatically good truth: LAPD points are snapped to intersections and some are km off (Canoga & Burbank 1.6 km). Check the truth on known intersections before scoring.
- 2026-10-18 · CCRS has 12,851 LAPD crashes for 2024; LAPD open data has 16,720. CCRS may miss ~23% of LAPD collisions (or LAPD publishes non-reportable ones). Follow up (F2).

- 2026-10-18 · CCRS has an `IsDeleted` flag (found by Hermes): drop those rows in every pull. None among SFPD 2023–24.
- 2026-10-18 · CCRS includes property-damage-only crashes: 59% of 2024 rows have 0 killed and 0 injured (found by Hermes). TIMS lacks most PDO.

- 2026-10-18 · Validate the truth before scoring against it: blank/duplicate report numbers and default "parking"
  points produced fake errors of 3–5 km. Hygiene dropped 25 of 5,333 links.
- 2026-10-18 · Test population must match the crashes the tool will place. In SF, GPS crashes = CHP freeway; the
  crashes we must place = SFPD city streets. A test on the former says nothing about the latter.
- 2026-10-18 · CCRS Report Number == DataSF case_id: an agency's own open data can be both truth and a cheaper
  placement method. Look for it in every city first.
- 2026-10-18 · Offsets are worth it: 2 m vs 38 m median error. But CCRS drops the offset in ~10% of SFPD crashes.
- 2026-10-18 · "Miles" offsets over 2 inside a city are feet. 3 of 5,309.
- 2026-10-18 · Leading directionals are part of names (SOUTH VAN NESS). Never strip them in the exact tier.
- 2026-10-18 · Plazas and malls (Fulton St plaza, Buchanan St mall) break intersections unless named footways are loaded.
- 2026-10-18 · Limit the street network to the reporting agency's jurisdiction, or same-named streets next door win.
- 2026-10-18 · Gate each tier on its own measured accuracy (dev/test split), not the blended number: a good overall
  98% can hide a 60% tier.
- 2026-10-18 · Jev's probability was not calibrated on this task (higher cut-off ≠ more accurate). Measure before
  trusting any model's confidence as a gate.
- 2026-10-18 · TIMS (user's usual source) = Berkeley's geocoded SWITRS/CCRS. Good second truth; needs login; check
  its terms before using it inside a paid product.
- 2026-10-15 · CCRS GPS coverage depends on the reporting agency (Long Beach 97%, SF 35%). Urban corridors are weakest.
