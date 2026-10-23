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
| C4 | "Fatal crashes get extra effort: CrashIQ locates fatal crashes the police left without GPS, using the federal FARS record and the report itself." | Unplaced fatal crashes on the 479 statewide test roads: 27 → 2 (−93%) | FARS (fits both named roads), unique_pair and report offsets; only for crashes with no usable location | Run 5 → run 8, 2026-10-22 | 2025 until FARS 2025 is published |
| C5 | "Every number is traced to its source table." | n/a | Validator rejects any finding whose numbers aren't in a cited table; 0 rejections of valid findings statewide | Run 6 (#179 fixed) | — |
| C6 | "Works where police record little GPS." (example) | Fremont PD: GPS on 1.6% of reports; 97% of the test road's crashes located | Statewide test, Cities sheet | Run 5 | Citywide figure; #199 will measure it for every city |

| C7 | "93% of California's crashes in the state record are on the map, including 97% of fatal crashes." | 92.6% of 2,057,508 CCRS crashes 2021–25; fatal 97.3%; fatal + serious 93.3% | Every CCRS crash in one bin: police GPS checked against the report's streets, CrashIQ exact + unique_pair placement, FARS (run 8, PR #226) | 2026-10-22, run 8 | % of crashes in the state record, not of all crashes that happened; the step up from 86.1% includes a +1.1 pt test-harness correction |
| C8 | "On city streets, CrashIQ itself places about 4 in 10 crashes, the ones police left without usable GPS." | City streets: 88.7% on the map, 41.2% placed by CrashIQ | Same as C7, by road type | 2026-10-22, run 8 | — |
| C9 | "Placed at the right intersection 92% of the time across 144 police departments." | 92.4% (34,660/37,527; W95 92.1%), exact 92.1%, unique_pair 93.0% | Hidden police GPS, only GPS consistent with its own report's streets; both auto-placement tiers; city streets | 2026-10-22, run 8 | Freeways, state highways and county roads (CHP GPS, can't verify independently); point accuracy on all GPS is a lower bound |
## Candidate claims (not yet usable: need a measurement or a decision)
- Per-city and per-district coverage tables (#207) for district-specific materials; quote D11 only after Coronado is reviewed.
- TIMS agreement: allowed only as "CrashIQ's counts agree with TIMS, built from the same CHP records" (not a completeness claim); TIMS terms for commercial mention unresolved (#126).

## Never claim
- Comparisons with other products without a fair head-to-head test.
- That the state data is complete (it isn't: pain points 26–30).
- Accuracy numbers from cities whose police GPS can't serve as truth (San Jose until #143's correction is validated, and the 9 agencies flagged in #144).
