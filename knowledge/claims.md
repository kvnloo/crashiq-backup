# Verified claims register (for the website and marketing)

User request (2026-10-22): keep the numbers that show CrashIQ's accuracy and coverage, with their proof, so they can be
used on the website. **Rule: a number goes on the website only if it's in this table, with its method, basis and date,
and it was re-checked on the latest run.** Code computes every number (CLAUDE.md); no rounding up, no claims beyond the
test. Every entry says what it does **not** show. Updated by PM after each statewide run.



| # | Claim (allowed wording) | Number | Method and basis | Date / run | Does NOT show |
|---|---|---|---|---|---|
| C1 | "CrashIQ places crashes without GPS at the right intersection 98.8% of the time (San Francisco test)." | 98.8% (95% low bound 98.3%), 3,632 crashes | Hidden-truth test: SFPD reports in CCRS matched to San Francisco's own geocoded crash records by case number; exact-match tier only; held-out test half (`validate_geocode.py --city sf --split test`) | 2026-10-22, main | Accuracy in other cities (police GPS elsewhere is too noisy to grade to this standard; see #144) |
| C2 | "Tested on every incorporated city in California." | 524 cities, one 1-mile test road each | Statewide test, frozen corridor list v1 (`tests/statewide/`) | Runs 1–6, 2026-10-20 to 22 | Every road in each city (one test road per city) |
| C3 | "No crash report silently missed on the statewide test roads." | 0 (independent check v4) | Tester's independent search of the state data for reports that name the road and a study cross street, compared with what CrashIQ pulled | Runs 4–6 | Reports with no usable street names (those are listed for review, not missed) |
| C4 | "Fatal crashes get extra effort: CrashIQ locates fatal crashes the police left without GPS using the federal FARS record." | Unplaced fatal crashes on the 479 statewide test roads: 27 → 6 (−78%) | FARS (NHTSA) linked by county, date, time and deaths; used only for crashes with no usable location, and only when the point fits both named roads | Run 5 → run 7, 2026-10-22 | 2025 until FARS 2025 is published |
| C5 | "Every number is traced to its source table." | n/a | Validator rejects any finding whose numbers aren't in a cited table; 0 rejections of valid findings statewide | Run 6 (#179 fixed) | — |
| C6 | "Works where police record little GPS." (example) | Fremont PD: GPS on 1.6% of reports; 97% of the test road's crashes located | Statewide test, Cities sheet | Run 5 | Citywide figure; #199 will measure it for every city |

| C7 | "86% of California's crashes in the state record are on the map, including 95% of fatal crashes." | 86.1% of 2,057,508 CCRS crashes 2021–25; fatal 95.2%; fatal + serious 86.1% (corrected 2026-10-22, PR #215) | Every CCRS crash in one bin: police GPS checked against the report's streets, CrashIQ exact placement, FARS (`tests/statewide/coverage.py`, PR #207) | 2026-10-22, code 5f54c02 (#204/#206 net +127) | % of crashes in the state record, not of all crashes that happened (the record itself is incomplete in places: pain points) |
| C8 | "On city streets, CrashIQ places nearly a third of crashes the police left without usable GPS." | City streets: 75.0% on the map, 29.4% placed by CrashIQ | Same as C7, by road type | 2026-10-22 | — |
| C9 | "Placed at the right intersection 92% of the time across 144 police departments." | 92.1% (24,831/26,961; W95 91.8%) | Hidden police GPS, only GPS consistent with its own report's streets; exact tier; city streets | 2026-10-22, PR #207 | Freeways, state highways and county roads (CHP GPS, can't verify independently); point accuracy on all GPS is 72.1% (lower bound) |
## Candidate claims (not yet usable: need a measurement or a decision)
- Per-city and per-district coverage tables (#207) for district-specific materials; quote D11 only after Coronado is reviewed.
- TIMS agreement: allowed only as "CrashIQ's counts agree with TIMS, built from the same CHP records" (not a completeness claim); TIMS terms for commercial mention unresolved (#126).

## Never claim
- Comparisons with other products without a fair head-to-head test.
- That the state data is complete (it isn't: pain points 26–30).
- Accuracy numbers from cities whose police GPS can't serve as truth (San Jose until #143's correction is validated, and the 9 agencies flagged in #144).
