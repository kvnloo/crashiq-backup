# Shared fixes found while building WI (not applied)

1. `names.street_key`: Wisconsin highway codes (`STH 32`, `USH 41`, `CTH PP`, OSM ref `WIS 190`) aren't known, so
   they don't match TIGER's `State Hwy 32` / `Co Rd PP`. Worked around in `wi_dt4000.road` (writes TIGER's names).
   Shared fix: STH/WIS -> SR, USH -> US, CTH -> CO RD. Test: `street_key("WIS 190") == street_key("State Hwy 190")`.
