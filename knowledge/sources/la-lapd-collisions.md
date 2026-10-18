# Los Angeles: LAPD "Traffic Collision Data from 2010 to Present" (d5tf-ez2w)

**Where:** https://data.lacity.org/resource/d5tf-ez2w.json (Socrata). 622k rows, one row per collision (`dr_no`).
**Licence:** CC0 1.0. **Status:** no longer updated. LAPD moved to a new records system; the replacement dataset isn't
published yet. Data last updated 2025-03-11; latest `date_occ` 2025-03-08. (checked 2026-10-18)
**Location:** hundred-block address + cross street + point; missing locations are (0, 0). Points are snapped to the
intersection (pain point #6: median 6 m from it even when the crash was 87 m away).
**No severity field** beyond MO codes; victim age/sex of one victim.

## Counts vs CCRS (LAPD = NCIC 1942), 2026-10-18
| Year | LAPD open data | CCRS | CCRS / LAPD |
|---|---|---|---|
| 2019 | 56,628 | 37,708 | 67% |
| 2020 | 42,385 | 30,045 | 71% |
| 2021 | 18,796 | 13,908 | 74% |
| 2022 | 16,417 | 11,724 | 71% |
| 2023 | 16,461 | 10,984 | 67% |
| 2024 | 16,720 | 12,851 | 77% |

- The gap is steady, so it isn't a CCRS lag. Cause UNVERIFIED; a DR-number vs CCRS `Report Number` join would show which
  crashes are missing.
- Both sources fall ~65% from 2019 to 2021: a reporting change, not a safety change. Warn on LA trend windows across it.
- CCRS LAPD rows have GPS on only 0.2–1% (2019–2025).
- User decision (2026-10-18, PR #16): city crash maps are for verification/tallying only, not a placement source.
