# US: National Address Database (NAD), US DOT

**Where:** https://www.transportation.gov/gis/national-address-database. The text file is at data.transportation.gov
(`fc2s-wawr`, `TXT.zip`, 8.48 GB): release r24, one national file `NAD_r24.txt` of 42 GB, and a file geodatabase
(`yw36-suxr`). The zip uses **Deflate64**: macOS unzip, bsdtar and ditto can't read it. The PyPI `zipfile-deflate64`
(built with `CFLAGS="-include stdio.h"` on macOS) streams it.
**Licence:** public domain (US DOT; data contributed by states, counties and cities). Commercial use OK.
**Local copy:** Tester worktree `data/cache/nad/` (downloaded 2026-10-25, user-approved, #264), with the
California rows kept as `nad_ca_r24.csv` (summary: `nad_ca_r24.csv.summary.json`), not committed.

## Quirks (with evidence)
- **Address points** (rooftop / site / structure), with `Placement` saying which. In #264 they were within 400 ft of
  police GPS 86–87% of the time, against about 67% for TIGER-range interpolation on the same crashes.
- **California coverage in r24 is partial: 2,534,873 points from 10 contributors.** Whole counties: San Bernardino,
  Sacramento, Ventura, Solano, Santa Cruz, Merced, Shasta, Santa Barbara. Cities only: Stockton, Costa Mesa. Nothing
  for Los Angeles, San Diego, San Francisco, Alameda, Santa Clara, Riverside, Fresno or Kern. (2026-10-25, #264)
