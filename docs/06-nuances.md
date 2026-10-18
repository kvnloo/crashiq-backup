# CrashIQ — technical nuances list

Every doubt about crash-analysis practice goes here. The user answers from experience, or we research it.
Status: OPEN / ANSWERED (who, date) / RESEARCHED (source).

| # | Question | Why it matters | Status |
|---|---|---|---|
| N1 | One count per crash: confirm CCRS Crashes table has one row per crash (CollisionId) and that severity = most severe injury in that crash (from InjuredWitnessPassengers) | HSIP counts once per crash, not per vehicle/victim | OPEN (verify in data) |
| N2 | Does CCRS include property-damage-only (PDO) crashes? TIMS excludes them | HSIP Analyzer has a PDO cost; rates and profiles change | OPEN (verify in data) |
| N3 | Mapping CCRS injury codes to KABCO / HSIP five levels (Fatal, Severe, Other visible, Complaint of pain, PDO) | Severity counts and B/C | OPEN |
| N4 | HSIP influence area: 250 ft, but only to mid-block when the next intersection is < 500 ft away | Crash assignment | RESEARCHED (Caltrans HSIP instructions; see research notes) |
| N5 | COVID years 2020–2022: exclude by default in HSIP mode, or offer a toggle? | HSIP allows exclusion | OPEN (user) |
| N6 | Preliminary (most recent) CCRS records: include or not, per mode? | Data completeness | OPEN (user) |
