# Default / dispatch GPS points (#218)

**What:** exact points (rounded to 5 decimals, ~1 m) where police GPS piles up without being a crash location:
statewide CHP defaults, downtown Sacramento, campus police points, placeholder digits (38.12346, −121.12346),
coordinates truncated to whole degrees (34, −118). A crash whose GPS sits on one of these, and doesn't fit the
streets its report names, is placed by its street names instead (user decision 2026-10-22, docs/03).

**Rule (the Tester's, #219, posted on #218):** a point shared by ≥ 10 crashes naming ≥ 5 different street pairs, of
which < 50% fit the point (a road the report names within 400 ft + the stated offset). Pooled across agencies: the
biggest defaults are shared by dozens of CHP areas. Thresholds: `backend/crashiq/config/gps.json`.

**This file:** `gps_piles.json`, the 50 points (1,828 crashes) the rule finds in CCRS 2021–25 (mirror of
2026-10-19, 1,554,835 crashes with police GPS), made by the Tester's `tests/statewide/gps_profile.py --piles`.
The pull also finds piles inside a corridor's own search box from the reports it reads, so the list matters for
points elsewhere: reports naming the corridor whose GPS sits on a listed point anywhere in the area are found by
name. Refresh once a year with the CCRS year, or when the Tester's scan changes.

**Coarse coordinates:** 2 decimals or fewer (~1 km; trailing zeros don't count) in both latitude and longitude are
no location either; in one of them, only when the point also fails the street check, because good GPS can end in
zeros (34.100000 reads 34.1; PM review of #225). The Tester counts 2,136 rows with 2 or fewer decimals in either
coordinate in 2021–25.
