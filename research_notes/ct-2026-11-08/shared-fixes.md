# Shared fixes found by the Connecticut pack (not applied; Hermes merges centrally)

1. `names.street_key` reads `CT 187` as `CT 187` and TIGER's `State Rte 187` as `SR 187`, so a Connecticut route crash
   named in OSM form misses a TIGER-only road. In the Hartford sample a retry in TIGER form (`STATE RTE n`, `US HWY n`) placed 14 of 472 pairs that the reader's form missed.
   Fix: treat `CT <n>` (and other two-letter state prefixes) as `SR <n>` in `street_key`, or add `CT` to its state-route
   prefixes. Test: `assert street_key("CT 187")[0] == street_key("STATE RTE 187")[0]`.
   Workaround in the reader: none needed for the app (OSM ways carry `ref=CT 187`).
