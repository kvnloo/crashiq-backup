# Lessons (newest first)

- 2026-10-20 · A coverage % is only as good as its denominator. Run 1 counted GPS crashes the assignment later
  excluded (Canada Blvd beside a Verdugo Rd corridor) as "located", so it read 95.8%; on crashes that actually count
  for the corridor it was 91.3%, and 65.0% in run 2 once the fixes found 10,600 reports run 1 silently missed.
  Measure coverage on what the study counts, and version the measure when it changes (#73 run history).
- 2026-10-20 · A test's own name matching must not borrow the app's. Run 1's independent check used the app's
  street cores, so it shared the leading-direction blind spot (#113) and called Glendale and Pasadena fine.
- 2026-10-20 · Substring matching on squeezed names needs a stop list: `NOT STATED` contains `STATE`, so every
  no-cross-street report named "State Street" (Santa Barbara, 6,136 junk rows from four counties, #121).
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
