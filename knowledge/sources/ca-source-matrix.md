# California: which crash source for which road type (issue #18, 2026-10-18)

Full report: `reports/California crash data sources by road type.md`. Evidence: `research_notes/ca-sources-2026-10-18/`.
This file records knowledge. The consensus rule and the questions in the report are still the user's decision.

## Road type in CCRS (2024, 417,170 crashes, deleted dropped)
Derive road type from agency + flags; `IsFreeway` is **blank on every local-agency row**.

| Road type | How to derive | Share | GPS | PDO |
|---|---|---|---|---|
| City streets | NCIC not 9xxx, `City Is Incorporated`, not `IsHighwayRelated` | 44.4% | 53.3% | 52.4% |
| Freeways | `IsFreeway` = True (CHP only) | 32.0% | 100.0% | 66.3% |
| Unincorporated county roads | CHP (NCIC 9xxx), not highway, not incorporated | 15.5% | 100.0% | 62.7% |
| Conventional state highways, outside cities | CHP, `IsHighwayRelated`, not freeway | 4.1% | 100.0% | 56.5% |
| State highways inside cities | local agency, `IsHighwayRelated` | 3.1% | 54.5% | 48.3% |

## Matrix
| Road type | Records | Location | Cross-check |
|---|---|---|---|
| Freeways / CHP roads | CCRS | CCRS GPS (validate vs the record's streets) | Caltrans TASAS (state highways), FARS (fatal) |
| City streets | CCRS (keeps PDO) | Our locator; validated GPS where present | TIMS points (F+I only), agency open data (SF good, LA gap) |

Source files: `ca-ccrs.md`, `sf-datasf-crashes.md` (PR #16 branch), `ca-tims.md`, `ca-caltrans-tasas.md`, `la-lapd-collisions.md`, FARS below.

## FARS (NHTSA), as a fatal-count check
- CA deaths, FARS Encyclopedia: 2023 4,169 (final), 2024 3,876 (1st release); 2024 fatal crashes 3,583.
- CCRS: 2023 4,271 killed (+2.4%); 2024 4,059 killed (+4.7%), 3,755 fatal crashes (+4.8%).
- FARS counts deaths within 30 days on public trafficways. Within 5% = consistent.
- The CrashAPI (`crashviewer.nhtsa.dot.gov/CrashAPI`) returned "Access Denied" (Akamai) to curl on 2026-10-18; the Encyclopedia pages load.

## Lessons (dated, with evidence)
- 2026-10-18 · Location quality depends on who writes the report, not the road: state highways inside cities (city police) have 54.5% GPS, the same as city streets; CHP rows are 100%. (CCRS 2024)
- 2026-10-18 · CCRS `IsFreeway` is only filled on CHP reports. Derive road type from NCIC + `IsHighwayRelated` + `City Is Incorporated`. (CCRS 2023–24, all local rows NULL)
- 2026-10-18 · TIMS is not a second record source: same CHP records, F+I only, with SafeTREC geocodes. It can place crashes better, not count them better. (TIMS help pages)
- 2026-10-18 · CCRS has only 67–77% of LAPD's own crash count in every year 2019–2024: a steady gap, not a lag. Cause unknown. (CCRS NCIC 1942 vs data.lacity.org d5tf-ez2w)
- 2026-10-18 · LAPD's reporting fell ~65% from 2019 to 2021 in both LAPD's data and CCRS. LA trend studies across 2020–21 need a warning.
- 2026-10-18 · CCRS state-highway counts run above Caltrans's own: freeways +4.5% crashes, +17% fatal crashes (2024). Caltrans counts only crashes *on* the highway and drops suicides. Use Caltrans's rule before comparing to Caltrans average rates.
- 2026-10-18 · CCRS SFPD injury crashes are 91–99% of DataSF's injury count (2019–2025): SF sources agree.

## Pain points to add to `knowledge/pain-points.md` once PR #16 merges
Rows 15–18 are in the report (Caltrans vs CCRS on state highways; LAPD reporting break; LA open data frozen; TIMS has no PDO and no licence).
