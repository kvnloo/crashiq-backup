# Shared fixes Nebraska would like (not made; Hermes merges centrally)

1. **`names.py` doesn't read `N-133` (Nebraska highway) as a route.** Workaround in the reader: `N-<n>` is written
   `NE <n>`, OSM's ref, which matches a corridor tagged `NE <n>` by name (street_key reads it as "NORTHEAST <n>" on
   both sides). Fix: add the pack's highway prefix (`N`, plus `L-`/`S-` link and spur roads) to `ROUTE` / `ROUTE_ANY`.
   Test: `assert route_numbers("N-133") == route_numbers("NE 133") == {"133"}`.
2. **Local freeway names** (`NORTH FREEWAY`, `KENNEDY FREEWAY`, `W DODGE EXPRESSWAY`) aren't in TIGER's names; OSM
   has them as `name`/`ref` on the ways. Not worked around (GPS covers every NE crash).
3. **A new study's default window ignores `first_year`.** `POST /studies` with no years for NE answers 422 "NDOT NTIP
   crash data starts in 2021. Pick 2021 or later." because the default window is five years back from the last final
   year (2020-2024). Fix: clamp the default `from_year` to `pack.first_year`. Test: creating an NE study with no years
   gives `from_year == 2021`. The end-to-end run passed 2021-2025 explicitly.
