# Lessons (newest first)

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
