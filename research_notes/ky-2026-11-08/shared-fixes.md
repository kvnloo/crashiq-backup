# Shared fixes found by the Kentucky build (not applied; for Hermes to merge centrally)

1. **Route numbers without a space** (`KY1747`, `I264`, `US60` is fine): `names.street_key("KY1747")` gives core
   `KY1747`, so it never meets TIGER's "State Hwy 1747" / "KY-1747". Fix: in `names.py`, split a leading route prefix
   (`KY|US|I|SR`) from digits, as already done for `US60` -> `US 60`.
   Test: `assert street_key("KY1747") == street_key("KY 1747")`.
2. **Ramp text in the cross-street field** ("I264 EB EXIT17A OFF RAMP TO KY155 SB"): treat a secondary road that
   contains `RAMP` as "on ramp of <primary>" (no intersection placement), so it lands in a ramp tier instead of "no
   intersection of the two named streets". Test: such a pair returns `tier == "review"` with a ramp note, not None.
3. Roadway names without suffix (`PRESTON`, `BARDSTOWN`) already match (suffix-less key), nothing to do.
