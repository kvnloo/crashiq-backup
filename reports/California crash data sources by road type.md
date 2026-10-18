# In California, CCRS Is the Record Source on Every Road Type; TIMS Wins Only on Placing City-Street Injury Crashes

Issue #18 · Hermes · researched 2026-10-18 · status: research only, nothing here is decided

The user's starting rule was "TIMS for city streets, CHP/CCRS for freeways." The data supports the freeway half outright and the city-street half only for *location*. **Freeways, state highways outside cities and unincorporated county roads (52% of 2024 crashes) are reported by CHP, and in CCRS every one of those records has GPS** (100.0%, 2024). Nothing beats CCRS there, except that Caltrans's own state-highway counts (TASAS) are 4.5% lower for freeway crashes and 17% lower for fatal freeway crashes, so any comparison against Caltrans average rates has to use Caltrans's counting rules. **City streets (44% of crashes) are where the sources split.** CCRS has all of them, property-damage crashes included (52% of city-street crashes are PDO), but only 53% carry GPS, and LAPD and SFPD records about 1%. TIMS geocodes about 97% of fatal and injury crashes, but it drops every PDO crash and is built from the same CHP records, so it can place crashes better but can't count them better. City open data counts differently again: **LAPD's own dataset has 1.3–1.5 times as many crashes as CCRS in every year 2019–2024**, and it stopped updating in March 2025. San Francisco agrees much better (CCRS has 91–99% of DataSF's injury crashes). Hermes's recommendation: one record set (CCRS) for every road type, our locator plus a TIMS cross-check for city-street placement, and a source check on every study that reports the gap rather than merging sources.

**Method.** Counts are from live queries on 2026-10-18 (script `research_notes/ca-sources-2026-10-18/queries.py`, output `evidence.json`): CCRS 2023–2024 grouped by road type, CCRS LAPD and SFPD counts by year 2019–2026, LAPD and DataSF open data by year. Caltrans state-highway totals come from Caltrans's *2024 Crash Data on California State Highways* (prepared 03/18/2026); FARS figures from the FARS Encyclopedia. TIMS facts come from SafeTREC's help pages and terms; Hermes has no TIMS account, so no TIMS record was downloaded. Earlier measurements (SF join, Long Beach GPS, offsets) are from `knowledge/pain-points.md` and `knowledge/sources/` on the PR #16 branch. Road type comes from CCRS fields: `IsFreeway`, reporting agency (NCIC code starting with 9 = CHP), `IsHighwayRelated`, `City Is Incorporated`. "PDO" here means no one killed or injured. Anything not confirmed from a primary source is marked **UNVERIFIED**. Sources with URLs: `research_notes/ca-sources-2026-10-18/sources.md`.

## Who reports which road decides how good the data is

CCRS 2024 (417,170 crashes after dropping deleted reports), grouped by road type:

| Road type (CCRS fields) | Reported by | Crashes | Share | Has GPS | PDO | Fatal crashes |
|---|---|---|---|---|---|---|
| City streets (local agency, incorporated, not highway) | City police / sheriff contracts | 185,148 | 44.4% | **53.3%** | 52.4% | 1,462 |
| Freeways (`IsFreeway`) | CHP | 133,289 | 32.0% | **100.0%** | 66.3% | 946 |
| Unincorporated county roads | CHP | 64,645 | 15.5% | 100.0% | 62.7% | 780 |
| Conventional state highways outside cities | CHP | 17,135 | 4.1% | 100.0% | 56.5% | 364 |
| State highways inside cities | City police | 12,893 | 3.1% | 54.5% | 48.3% | 182 |
| Other CHP inside cities | CHP | 3,985 | 1.0% | 100.0% | 75.4% | 21 |

2023 shows the same pattern (city streets 44.8% of crashes, 51.3% with GPS; every CHP group ≥99.9%). Two things follow. **The location problem is a city-police problem, not a road problem**: a state highway inside a city has the same 55% GPS as a city street because the city police write the report. And **CCRS's `IsFreeway` flag is only filled on CHP reports**; local-agency rows have it blank, so "road type" in CCRS has to be derived from agency + highway + incorporated flags, as above.

## The sources compared

| | **CCRS** (CHP, data.ca.gov) | **TIMS** (UC Berkeley SafeTREC) | **Caltrans TASAS / TSN** | **City open data** (DataSF, LAPD) | **FARS** (NHTSA) |
|---|---|---|---|---|---|
| Records | Every reported crash, all agencies, 2016–2026 | SWITRS (CHP) records, last 10 final years + provisional | State-highway crashes only, coded to postmile | One agency's own reports | Fatal crashes only |
| PDO | **Yes** (59% of all rows, 2024) | **No** ("TIMS excludes property-damage-only crashes") | Yes | SF: no (injury only). LA: yes | No |
| Location | Officer GPS: 100% CHP, 53% city streets, ~1% LAPD/SFPD; street pair + offset on all | SafeTREC geocode `POINT_X/Y` on ~97% of F+I crashes (Esri StreetMap Premium intersection locator + offset; TSN postmiles on state highways) | Postmile (linear referencing) | SF: SFPD coordinates; LA: hundred-block address, snapped points | Lat/long |
| Freshness | Daily; current year preliminary | Quarterly; CHP finalizes 12–18 months late | Annual book (2024 published 03/2026); data by request | SF quarterly; **LA frozen since 2025-03-11** | ~15-month lag |
| Access | Open API, no login | Free account, CSV download per query | Request form, **PDF output only**; CPRA for non-Caltrans work | Open API | Open download |
| Licence | Public domain | **No licence grant**: attribution requested, data "AS IS", §409 notice, CPRA litigation limits, Caltrans staff told not to rely on it | Caltrans records; not a redistributable feed | DataSF PDDL 1.0; LAPD CC0 1.0 | US government work |

TIMS is not a second source of crashes. It is CHP's records with SafeTREC's geocodes added. SafeTREC also notes that since CHP moved to CCRS (2015), CCRS no longer returns Caltrans highway attributes, so TIMS now checks officer GPS on state highways and falls back to its postmile method when needed.

## Where two sources cover the same crashes, how well they agree

| Comparison | Years | Result | What explains it |
|---|---|---|---|
| **CCRS vs LAPD open data**, City of LA | 2019–2024 | CCRS has **67–77%** of LAPD's count every year (2024: 12,851 vs 16,720; 2023: 10,984 vs 16,461; 2019: 37,708 vs 56,628) | Consistent gap, so not a reporting lag. Possible causes: LAPD reports that never reach CHP, or LAPD counting incidents CHP doesn't treat as reportable crashes. **UNVERIFIED**; needs a report-number join (LAPD's DR number vs CCRS `Report Number`) |
| **LAPD reporting drop**, both sources | 2019→2021 | LAPD open data 56,628 → 18,796 (−67%); CCRS LAPD 37,708 → 13,908 (−63%) | Both sources drop together, so it's a change in what LAPD reports, not a real safety change. Cause **UNVERIFIED**. Any LA trend or before/after study across 2020–21 is invalid without a warning |
| **CCRS vs DataSF**, SFPD injury crashes | 2019–2025 | CCRS has **91–99%** of DataSF's injury crashes (2024: 2,893 vs 3,026; 2025: 2,917 vs 2,946) | Close. Whether DataSF includes non-SFPD reports is UNVERIFIED. Known since 2026-10-18: the two join exactly on report number (5,309 linked crashes 2023–24), and ~10% of SFPD records lose their offset in CCRS |
| **CCRS vs Caltrans TASAS**, freeways | 2024 | Crashes 133,289 vs 127,545 (**+4.5%**); fatal crashes 946 vs 808 (**+17%**); killed 1,049 vs 882 (+19%) | Caltrans counts crashes *on* the highway only: it excludes crashes "associated with" a state highway, suicides and beat-902 incidents. CCRS `IsFreeway` is the officer's flag |
| **CCRS vs Caltrans TASAS**, all state highways | 2024 | CCRS highway-related 163,317 vs 153,588 (+6.3%); fatal 1,492 vs 1,337 (+12%) | Same reasons; CCRS `IsHighwayRelated` is broader than "on the highway" |
| **CCRS vs FARS**, statewide deaths | 2023, 2024 | 4,271 vs 4,169 (+2.4%, FARS final); 4,059 vs 3,876 (+4.7%, FARS 1st release); fatal crashes 2024: 3,755 vs 3,583 (+4.8%) | FARS counts deaths within 30 days on public trafficways only. Agreement within 5% |
| **CCRS vs TIMS**, statewide F+I crashes | 2023 | 167,604 vs 163,848 (+2.3%) | **UNVERIFIED**: the TIMS figure is quoted by a third-party page, not read from TIMS. Same records, so they should agree closely |
| **Officer GPS vs the record's own streets** (Long Beach PD) | 2024 | Only 73% of GPS points sit on the streets the officer wrote | From pain point #2. GPS is not automatically the best location either |

## What this means per road type

| Road type | Records from | Location from | Cross-check | Confidence |
|---|---|---|---|---|
| **Freeways** | CCRS | CCRS GPS (100%), checked against the record's own route/streets | Caltrans TASAS for anything compared to Caltrans average rates; FARS for fatal counts | High. Matches the user's "CCRS for freeways" |
| **State highways (conventional)** | CCRS | CHP GPS outside cities; our locator inside cities (city police, 55% GPS) | Caltrans TASAS (same rate caveat) | High outside cities, medium inside |
| **Unincorporated county roads** | CCRS | CCRS GPS (100%) | FARS for fatal | High |
| **City streets** | CCRS (keeps PDO) | Our locator (PR #16: 90% auto-placed at 98.8% in SF), validated GPS where present | TIMS `POINT_X/Y` on the F+I subset; agency open data for counts (SF good, LA known gap) | Medium. Placement is solved in SF and being validated per city (#17); counts in LA are under-reported by CCRS |

**The user's TIMS-for-city-streets rule, restated with the evidence.** TIMS is the better *placed* injury dataset on city streets today: ~97% geocoded against CCRS's 53% GPS. But using it as the record set would drop the 52% of city-street crashes that are PDO (pain point #10), and it can't close the LAPD gap because it is built from the same CHP records. It also has no licence grant for a paid product. So TIMS fits as a placement cross-check (does our point agree with SafeTREC's?), not as the source of counts.

## Proposed consensus rule (for the user to decide)

1. **One record set per state.** In CA that is CCRS, all severities. Sources are never added together; a crash counted in two sources would be counted twice.
2. **Best location per crash, with provenance:** validated officer GPS → our locator (exact / address / relaxed / near) → user. A TIMS point, where the user has a TIMS export, is a check on our point, never a silent replacement.
3. **A source check on every study, reported in the audit block:** study-area count from CCRS vs the second source for that road type (Caltrans TASAS on state highways, agency open data on city streets, FARS for fatal). If the gap is over a threshold the user sets, the study shows a warning with the known reason.
4. **Known reporting breaks are warnings, not silent data:** e.g. LAPD 2020–21, current-year preliminary records, LA open data frozen after 2025-03-11.
5. **Rates against Caltrans averages (D3) use Caltrans's counting rule:** crashes *on* the state highway only, labelled "approximate to TASAS" until the user can import a Caltrans TSAR export.

## Licence notes

- **CCRS:** public domain (CHP). Fine for a paid product.
- **TIMS:** no licence is granted. The terms ask for an acknowledgment ("Transportation Injury Mapping System (TIMS), Safe Transportation Research and Education Center, University of California, Berkeley"), give the data "AS IS", carry the §409 notice, bar use "in connection with" pending litigation against the State or a local authority, and tell Caltrans staff not to rely on it for engineering decisions. Commercial use isn't mentioned either way. Hermes's reading, not legal advice: **don't redistribute TIMS geocodes inside CrashIQ without written permission from SafeTREC (tims_info@berkeley.edu)**. A user who uploads their own TIMS export for a cross-check is a lower-risk pattern.
- **Caltrans TASAS:** PDF output on request, CPRA for non-Caltrans projects. Not a feed CrashIQ can pull.
- **DataSF:** ODC PDDL 1.0. **LAPD:** CC0 1.0. **FARS:** US government work. All fine.
- The §407/§409 notice applies to crash data used for HSIP work in every source above (#4 Q4 lawyer review).

## Pain points to add (rows 15–18)

`knowledge/pain-points.md` lives on Claude Code's PR #16 branch, so these rows are listed here and on #18 instead of edited in:

| # | Pain point | Evidence | Cost to the client | How CrashIQ addresses it |
|---|---|---|---|---|
| 15 | **State and Caltrans counts differ on state highways** | 2024 freeways: CCRS 133,289 vs Caltrans 127,545 crashes; fatal 946 vs 808 (+17%) | Crash rates computed from CCRS but compared to Caltrans averages are inflated; HSIP numbers don't match Caltrans's | Caltrans counting rule applied before any comparison to Caltrans rates; gap shown |
| 16 | **A city's reporting can collapse, and it looks like a safety gain** | LAPD crashes 56,628 (2019) → 18,796 (2021) in LAPD's own data; same drop in CCRS | Before/after and trend studies in LA across 2020–21 show a fake 60%+ improvement | Reporting-break warnings per agency and year |
| 17 | **City open data goes stale without notice** | LAPD collision dataset frozen since 2025-03-11 (new RMS dataset not yet published) | Studies on "the city's data" miss 1.5+ years | Source freshness check before every study |
| 18 | **The best-geocoded free source has no PDO and no commercial licence** | TIMS: ~97% geocoded, F+I only, no licence grant | Agencies use TIMS for maps and miss half their crashes; consultants can't build products on it | CCRS records with our own placement; TIMS only as a check |

## Questions for the user

Reply like `1A 2Y 3Y…`. Hermes's recommendation is in brackets. Nothing in docs/ or the build has been changed for these.

1. **City streets:** (A) CCRS records + our locator, TIMS points only as a cross-check; (B) take TIMS points as the placement for F+I crashes when available (needs SafeTREC permission); (C) other. [A]
2. **Ask SafeTREC in writing** whether TIMS geocodes may be used inside a paid tool? Hermes drafts the email, you send it. [Yes]
3. **Study-level source-gap warning:** flag when the CCRS count differs from the second source by more than ___%. [10%]
4. **State-highway rates vs Caltrans averages (D3):** (A) filter CCRS to Caltrans's "on the highway" rule and label it approximate in v1, TSAR import later; (B) require a TSAR export from the user before showing SHS rates. [A]
5. **LA reporting break:** warn on any LAPD study window that crosses 2020–21? [Yes]
6. **LAPD gap:** worth a report-number join (LAPD DR number vs CCRS) to find which crashes CCRS is missing? About an hour of Claude Code time. [Yes, after #16 merges]
7. **FARS fatal check:** compare each study's fatal count with FARS as part of the source check (this is a check, not the v2 map overlay from #4 Q8)? [Yes]

## Confirmed versus unverified

**Confirmed 2026-10-18 (live queries or primary documents):** every CCRS count above; LAPD and DataSF counts by year; LAPD dataset frozen (data last updated 2025-03-11) and CC0; DataSF PDDL; TIMS excludes PDO, ~97% geocoded, method, terms text; Caltrans 2024 SHS statewide and freeway counts and its exclusions; Caltrans request form gives PDF only; FARS CA fatalities 2023/2024 and fatal crashes 2024.

**UNVERIFIED:** why CCRS has only 67–77% of LAPD's crashes; why LAPD reporting dropped in 2020–21; whether DataSF includes non-SFPD reports; the TIMS 2023 F+I count (secondary source); TIMS's real geocode accuracy on city streets (no TIMS export tested; SafeTREC publishes a rate, not an accuracy); the join key between TIMS `CASE_ID` and CCRS `Collision Id`.

## Conclusion

California doesn't need different sources for different roads. It needs one complete record set and different *location* handling by road type. CHP-reported roads (freeways, state highways outside cities, county roads) are fully located in CCRS. City streets are the hard part, and TIMS's advantage there is placement, which is the job PR #16 is already doing. The disagreements worth showing clients are the ones CrashIQ can explain: Caltrans's narrower counting on state highways, LAPD's reporting gap and break, and a frozen city dataset. The next state's pack (#19) should carry the same three things: its record source, its location method per road type, and the cross-checks to run.
