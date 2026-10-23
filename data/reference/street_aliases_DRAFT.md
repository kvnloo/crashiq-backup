# street_aliases_DRAFT.csv: proposed street aliases (not in use)

**DRAFT, for the user's entry-by-entry approval (#230; CLAUDE.md: nothing is learned without user approval). The app
does not read this file.** Approved entries move to the live alias files (`data/aliases/*.csv`, `raw,replacement`),
which Engineering wires into the locator.

Made by `tests/statewide/alias_mine.py` from the CCRS mirror 2026-10-19 (2021–2025) and OSM 2026-10-18, on the
run-8 city street maps (each city's box + 1 km) and the app's code on main.

| Column | Meaning |
|---|---|
| scope_type, scope, county_code | where the alias applies (a CCRS city name; aliases are local) |
| raw | the report's road text, normalized the way the app reads alias files (upper case, `. , # ' "` → space) |
| replacement, map_street | the OSM street it is (normalized, and as OSM writes it) |
| votes, agreement_pct, rival | crashes whose other street meets exactly one map street resembling `raw`; share pointing to `map_street`; the runner-up, if any |
| similarity | name similarity of `raw` and `map_street` (app's `names.similarity`) |
| crashes_with_name, difficult_with_name | crashes in the city with this road text; of them, in the difficult bin (run 8b) |
| would_place | difficult crashes the app's gate (exact + unique_pair) places once the alias is applied |
| holdout_k / holdout_n / holdout_pct / holdout_low | hidden police GPS, self-consistent with the report once the alias is read: right intersection (within 250 ft) of n, Wilson 95% low |
| examples | up to three Collision Ids |
| kind | `abbreviation (cleaner rule)`: the map name is `raw` with standard abbreviations spelled out (better as one name-cleaner rule); `local spelling or name` |
| status | `proposed` for every row |
