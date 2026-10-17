# Spike: CCRS as the crash source (2026-10-15)

**Verdict: viable, but we need to geocode crashes that come without coordinates.**

## Findings
- data.ca.gov package `ccrs` (CHP) has Crashes / Parties / InjuredWitnessPassengers
  CSVs for **2016–2026**. They are queryable through the CKAN `datastore_search_sql`
  API: no login, and bounding-box SQL works.
- Crashes_2024 has 417,169 rows, of which **324,732 (78%) have Lat/Long**.
- Coordinate coverage is **uneven by city**. Unincorporated areas and CHP reports
  are ~100%, Long Beach 97%, LA City 56%, San Diego 57%, Sacramento 33%, SF 35%.
  Urban corridors, where most studies happen, are the weakest.
- Every row has `PrimaryRoad`, `SecondaryRoad`, `SecondaryDistance`, `SecondaryDirection`.
  That lets us **geocode by intersection**: match the normalized street names against
  the corridor's OSM intersections, then offset by distance and direction.
- Street names are messy ("CRENSHAW BLVD" / "CRENSHAW BOULEVARD", "I-105 W/B"),
  so the names need normalizing.
- Severity: Crashes has NumberKilled/NumberInjured. KABCO injury severity is in
  InjuredWitnessPassengers. Party details (mode, movement, age, fault) are in Parties.
- Per-year resource IDs live in the package metadata. Resolve them at runtime, don't hardcode them.

## Implications for design
1. Query both rows with coordinates (bounding box + corridor buffer) **and** rows
   without coordinates in the corridor's city/county whose street names match a
   corridor street. Geocode the second group to intersections.
2. Report a **location confidence** for each crash (GPS / intersection-matched /
   unmatched) and show the match rate on the dashboard. Never hide dropped crashes.
3. To verify: LA City's 28.8k crashes in 2024 looks low next to historic SWITRS
   volumes, so possible underreporting or a migration lag. Check against TIMS for
   one known corridor.
4. 2026 data is partial-year, and the most recent ~12 months may be preliminary
   (`Is Preliminary`). Default analysis window: the last 5 complete years.
