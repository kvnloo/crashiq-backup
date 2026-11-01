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

## Use in CrashIQ (#283, user decision 2026-10-25)
- `backend/crashiq/nad.py` builds a SQLite index (`data/cache/nad/nad_ca.sqlite`, ~4 min, once) from
  `nad_ca_r24.csv`, keyed by county, house number and street core; no network.
- Matching: the crash's county and city (`Inc_Muni` or `Post_City`; the county alone when the crash is
  unincorporated), the same house number, the same street (the app's name cleaner; a street type both sides write
  must agree). The matches must be one place (within 1,000 ft); the spot is their mean.
- Checked on the Tester's #264 pools (Engineering, 2026-11-01): 623 of 12,568 D5 crashes placed (#264's own matching:
  647); on the hidden-GPS truth pool, 1,704 placed, 86.2% within 400 ft and 74.5% within 250 ft. Where both placed
  the same crash, 2,280 of 2,300 points are within 50 ft of each other.
