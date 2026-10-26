# US: TIGER/Line ADDRFEAT (address ranges), US Census Bureau

**Where:** https://www2.census.gov/geo/tiger/TIGER2026/ADDRFEAT/, one zip per county (`tl_2026_06<fips>_addrfeat.zip`).
California's 58 files total 188 MB. Each segment has `FULLNAME`, left/right ranges (`LFROMHN` / `LTOHN` /
`RFROMHN` / `RTOHN`), parity and ZIP.
**Licence:** US Government work, public domain. Commercial use OK.
**Local copy:** Tester worktree `data/cache/tiger_addrfeat/2026/` (downloaded 2026-10-25, user-approved, #264), not
committed.

## Quirks (with evidence)
- Ranges run FROM → TO along the line and may descend (2399 → 2301). Interpolate by position, not by sorting.
- **The same street name and number in more than one place in a county** (different cities) is common: 1,108 of the
  #264 crashes had matching ranges in more than one place. Limit to the crash's city first.
