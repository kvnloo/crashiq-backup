# Shared fixes found by the Illinois build (not applied; for Hermes to merge centrally)

1. **`packs.COMING` still lists IL.** `tests/test_packs.py::test_setup_lists_ready_states_first` fails once IL is a
   pack. Fix: delete `"IL": "Illinois"` from `COMING` in `packs.py`. Meanwhile `statepacks/il.py` does
   `COMING.pop("IL", None)` (remove that line with the fix).
2. **Illinois route words** (DuPage 2025 sample, `names.street_key`):
   - `Il Route 59` -> core `IL ROUTE 59`, `Il Rte 59` -> `IL RTE 59` (TIGER `State Rte 59` -> `SR 59`).
   - `E Il-38` -> `EAST IL 38` (a direction before `IL-38`; `Il-64` alone already works).
   Fix: read `IL ROUTE|IL RTE|IL-` + number as `SR <n>`, also after a direction.
   Test: `assert street_key("Il Route 59") == street_key("Il Rte 59") == street_key("State Rte 59")` and
   `assert street_key("E Il-38").core.endswith("SR 38")`.
3. **`Route 30`** reads as `SR 30`, but in Illinois "Route 30" is often US 30 (TIGER `US Hwy 30`). Not fixable by name
   alone; IDOT's RouteNumber field doesn't say the system either. Note only.
4. **Doubled direction** `S S Highland Ave` -> `SOUTH S HIGHLAND` (officer typo). Fix: collapse a repeated leading
   direction letter. Test: `street_key("S S Highland Ave") == street_key("S Highland Ave")`.
5. **Combined names** `North Ave / Il-64` in the road field: split on ` / ` and try each part (as intersections' alt
   names already are in `crashes.pull_reader`).
