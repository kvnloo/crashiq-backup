# Caltrans districts by county (`caltrans_districts.csv`)

Source: Caltrans, Division of Local Assistance, "Local Assistance Contacts"
(https://dot.ca.gov/programs/local-assistance/other-important-issues/local-assistance-contacts), read 2026-10-22.
It lists each district's counties; District 9 is listed as "Inyo, Kern/Eastern, Mono".

- `ccrs_county_code`: CCRS County Code (California's counties in alphabetical order, 1-58); `fips`: the county's
  FIPS code (06 + 2n-1, as used for FARS, #166).
- **Kern** is split between District 6 and District 9 (eastern Kern). CCRS gives only the county, not the side, so
  every Kern crash counts under District 6 here; District 9's figures leave out eastern Kern.
- Used by `tests/statewide/coverage.py` (#199) to roll crash coverage up to districts.
