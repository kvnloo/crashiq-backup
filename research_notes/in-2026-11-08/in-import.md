# Indiana crash data: import notes (Hermes, 2026-11-08)

**Verdict: bucket D (gated), no pack.** The 2026-11-02 screen was right this time. Checked live 2026-11-08.

## Where Indiana's crash records are
- **ARIES** (Automated Reporting Information Exchange System), run for the Indiana State Police by LexisNexis Risk
  Solutions: every officer crash report. "LexisNexis Risk Solutions provides ARIES to state and local governments free
  of charge and charges a small fee for crash records and research requests"
  (<https://www.in.gov/cji/research/crash-statistics/index>).
- **Single reports:** "makes electronic vehicle crash reports available for a nominal fee through the BuyCrash website"
  (<https://www.in.gov/isp/crash-reports/>).
- **INDOT AASHTOWare Safety** (ARIES copy with INDOT's KABCO field "Crash Severity Level (NEW)"): "An Access Indiana
  account is now required for all external users to access ITAP and all applications within ITAP (e.g. AASHTOWare
  Safety)"; then "request access to AASHTOWare Safety ... Click 'Enroll New Application'"
  (<https://support.numetric.com/en/articles/12384809>). INDOT Traffic Engineering FAQ: "How do I request crash data for
  a project I am working on? Have your project manager contact the Office of Traffic Safety"
  (<https://www.in.gov/indot/traffic-engineering/traffic-guidance-documents>).
- **ARIES portal downloads** (<https://ariesportal.com/Downloads/Download>): Indiana State Police Yearly Crash
  Statistics 2025 (PDF) and a Crash Reporting Performance Report: summaries, no records.
- **Indiana Data Hub** (hub.mph.in.gov): CKAN `package_search?q=crash` -> 0 datasets (2026-11-08).

## Open layers found, none usable statewide
| layer | rows | why not |
|---|---|---|
| Indiana MPH Historical Crash Points (`services2.arcgis.com/hUPR9iC6qnMcwWsa/.../Historical_Crash_Points`) | 508,176, 2011-2016 | a 2016 demo: 60-124k a year, where Indiana had 198,247 collisions in 2024 (IUPPI, Indiana Crash Facts CY2024); injury "Unknown" on 92%; stale |
| IMPO 2018-2025 Fatal and SSI | 8,753 | Indianapolis region, K and A only |
| IMPO Bike and Ped Crashes 2022-2025 | 2,073 | pedestrian/bicycle only |
| Monroe County Crashes (Bloomington) | 51,092, 2003-2015 | one county, stale |

So no placement sample and no reader: there is no record-level statewide file to measure.

## What we have ready
- `in-column-map.md`: how an AASHTOWare/ARIES export would map to CrashIQ's crash contract (from ARIES export
  column names seen in public layers; INDOT publishes no export layout).
- `in-methods.md`: INDOT's own per-crash KABCO costs (2025 $), KABCO definitions and the 5-year rule (B8, 2026).

## What the user must do
See `in-summary.json` `user_actions`: an Access Indiana + ITAP + AASHTOWare Safety account (or an INDOT project
manager's request), a 5-year CSV export with lat/lon and road names, and a written OK for paid use.

## Not checked
The AASHTOWare export's real header (needs the account); the full VCRS data dictionary (NHTSA's copy refuses scripted
downloads, 403); city open data beyond ArcGIS search (Fort Wayne, Evansville, South Bend portals not searched).
