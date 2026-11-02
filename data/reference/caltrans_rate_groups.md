# Caltrans basic average crash rates (`caltrans_rate_groups.csv`): state-pack data (#287 part 1)

Source note: `knowledge/sources/ca-caltrans-tasas.md`.

Caltrans' statewide average crash rate for each **rate group** (a kind of highway segment, intersection or ramp), for
comparing a state-highway location's crash rate with the statewide average (user decision 2026-10-29, docs/03
"Caltrans rate groups for statewide-average comparison"). The engineer enters each location's rate group; nothing is
guessed.

## Source
- **Caltrans, *2024 Crash Data on California State Highways***, "2024 Basic Average Crash Rate Table" for highways
  (H01–H67, printed pages 83–85), intersections (I01–I31, pages 86–87) and ramps (R01–R80, pages 88–90). Printed page
  = PDF page − 3. Table pages dated 5/27/2026; the book was prepared 03/18/2026.
- URL: https://dot.ca.gov/-/media/dot-media/programs/research-innovation-system-information/documents/annual-collision-data/2024-crash-data-on-cshwy-book-v3-a11y.pdf
  (3,890,174 bytes; SHA-256 4ec3f34c199e7c533c287e64a77a9ff06d8cfe002e5bb14ea7d41b3654e7daf0), downloaded 2026-11-01
  with the user's OK into `data/cache/caltrans_downloads_2026-11-01/`. Not stored in the repo.
- The table's own note: "Highway, Intersection and Ramp Base Rates / Crash Percentage were loaded into Transportation
  System Network (TSN) on April 22, 2022."
- Built by `scripts/extract_caltrans_rate_groups.py` (pdftotext -layout, one regex per row), not typed. The script
  checks that every group appears once and in order, and that each row's fatal and injury percentages add up to its
  F+I percentage.

## Columns
| Column | Meaning (from the table) |
|---|---|
| `group` | Rate group: H01–H67, I01–I31, R01–R80 |
| `base_rate` | Highways: crashes per million vehicle-miles (MVM). Intersections: crashes per million vehicles entering. Ramps: crashes per million vehicles traversing the ramp |
| `adt_factor`, `adt_op` | Added to the base rate: `/` = the factor divided by ADT in thousands ("0.60/" with 5,000 ADT adds 0.12); `*` = the factor times ADT in thousands ("0.017" with 20,000 ADT adds 0.34). Only some highway groups have one |
| `pct_fatal`, `pct_injury`, `pct_fi` | Share of the group's crashes that are fatal, injury, fatal + injury (%) |
| `type`, `terrain_or_adt`, `design_speed`, `control`, `ramp_areas`, `on_off`, `area` | The group's description: highway type, terrain (or freeway ADT band), design speed; intersection type (F, M and S = four-legged, multi-legged, offset; T, Y and Z = tee, wye, other; R = roundabout) and control; ramp type, ramp areas, on/off; rural, suburban or urban |
| `cost_fi_k`, `cost_all_k` | Crash costs ($1,000) per F+I crash and per crash, from the table (not used; CrashIQ ranks by LRSM costs, `crash_costs_ca.md`) |
| `printed_page` | The book's printed page |

## How CrashIQ applies it (`backend/crashiq/rate_groups.py`)
- **Expected rate** = base rate + ADT factor, with the location's ADT (a segment's window-average Caltrans AADT in
  T22; a ramp's window-average ramp ADT in T25; an intersection's entering vehicles in T2).
- **Expected fatal + injury and fatal rates** = expected rate × `pct_fi` / 100 and × `pct_fatal` / 100.
- **Approximate:** CrashIQ counts crashes as it places them on the corridor (mainline only, #304), not by Caltrans'
  on-highway rule (no "associated with" crashes, suicides or beat 902), so every comparison with these averages is
  labelled approximate.
