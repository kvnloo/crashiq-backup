# Shared fixes Pennsylvania needs (Hermes merges centrally; none applied on this branch)

1. **Price U at the C cost per state** (`profile.state_costs` / `crash_cost`): PennDOT Pub 638 (2024) Table 4-3
   prices "Possible Injury and Unknown Severity" together. Fix: an optional `"U": "C"` (or a `U` dollar value) in
   `methods_<st>.json` `crash_costs`, read by `state_costs`. Test: a PA corridor with one U crash gets C's $155,850.
2. **Spelled ordinals past TWELFTH in `names.street_key`** (`ORDINAL_WORDS`): PennDOT writes `SIXTYTHIRD ST`,
   `FIFTY-FIFTH ST`, `TWENTIETH ST`. Worked around in `pa_penndot.street()` (`_number`). Test:
   `street_key("SIXTYTHIRD ST") == street_key("63RD ST")`.
3. **PennDOT two-letter suffixes** `PK` (Pike), `CR` (Circle), `TE` (Terrace), `BR` (Bridge) aren't in `SUFFIX`
   (`AV`, `BL`, `EX`, `PY`, `HW`, `WY` already work). Worked around in the reader (`SUFFIX`). Test:
   `street_key("LIMEKILN PK") == street_key("LIMEKILN PIKE")`.
4. **Not fixed, measured**: ramps named `RAMP A RD`, and two names in one field (`WOODHAVEN RD/THORNTON RD`), don't
   place. A split on `/` in the locator would let the first name try.
