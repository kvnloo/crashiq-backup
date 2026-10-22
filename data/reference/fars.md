# FARS reference store (#174)

**What:** NHTSA's Fatality Analysis Reporting System, `accident.csv`, California rows only (STATE = 6). It is public
domain (US DOT). Each fatal crash in CCRS is linked to its FARS case. When CCRS has no usable location for it (no GPS,
or GPS that fails the street check), the FARS point is used if it fits the streets the report names (user decision
2026-10-21, docs/03); provenance `fars`.

**Where:** the app database, tables `fars_accident` (one row per FARS case, keyed by year + ST_CASE) and
`fars_source`, which holds per year the file it came from, the number of rows and when it was loaded. Nothing from
FARS is committed to the repo.

**Load or refresh (once a year):** NHTSA publishes a FARS year about 15 months after it ends (2024 in 2026; 2025
isn't out yet). Then:

```
python backend/scripts/load_fars.py --download 2025
```

- Source: `https://static.nhtsa.gov/nhtsa/downloads/FARS/<year>/National/FARS<year>NationalCSV.zip`, file
  `accident.csv`, about 35 MB zipped per year.
- Loading a year replaces that year. NHTSA also revises the previous year once; re-load it too.
- Then pull fresh crash data (Data sources → "Pull fresh data from CCRS") so studies use it.
- Files already on disk: `--csv path/accident_2024.csv`. Some years start with a byte-order mark (2021, 2022); the
  loader handles it.

**Link rule** (the Tester's, verified in #166 / PR #172 on 16,278 fatal crashes, 94.7% one-to-one):
- same county (CCRS county code → FIPS 2n−1) and date, same number killed
- time within 60 minutes (FARS unknown time matches any)
- more than one match: a road the report names breaks the tie; still more than one = ambiguous, never used
- a FARS case is year + ST_CASE, because case numbers restart every year

A point is usable when it lies in California (FARS writes 77.7777 / 88.8888 / 99.9999 for unknown) and is not shared
by 3+ FARS crashes.
