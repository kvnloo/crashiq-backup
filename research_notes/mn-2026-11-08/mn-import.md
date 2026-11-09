# Minnesota: statewide crash data for CrashIQ (Hermes, 2026-11-08)

Status: **active** (plug-in `statepacks/mn.py`, reader `sources/mn_mncrash.py`). Bucket **A\*** (open, but no API and no licence text).

## 1. Source: MN DPS MNCrash public portal
- URL: https://mncrash.state.mn.us/Pages/AdHocSearch.aspx ("Analyze Data"), no login. Read live 2026-11-08.
- ASP.NET WebForms (EasyQuery). No REST API. The reader replays what the browser does, in 4 postbacks plus the export:
  date operator "custom period" (`r1$e2` = 7), map rectangle (UTM 15N, EPSG:26915, `hdnMapCriteria`) and the two dates,
  Search, Export as CSV (a zip with one CSV). Query: `SELECT * FROM dbo.vwAdHocCollisionPublicPortal`.
- The server sends its certificate without the Sectigo EV E36 intermediate; the reader adds that one public CA
  (verification stays on).
- Export columns (17): ACN, Local ID, Crash Date, Roadway, City, Township, County, Tribal Nation, Agency, Crash Severity,
  Number of Fatalities, Number of Injuries, Latitude, Longitude, Alcohol Related, Distraction Related, Speed Related.
- Years: 2016 to now ("Crash data is only available from January 1, 2016 forward"); the current year is preliminary.
- 2024 statewide export (one query, 11.3 MB CSV): **63,643 crashes**, 2024-01-01 to 2024-12-31.
  - GPS present and plausible: 63,640 (99.995%); 1 point outside Minnesota.
  - Severity (KABCO words): K 421, A 1,751, B 6,351, C 9,090, O 44,307, blank 1,723 (2.7%). Blank -> K if a death is
    counted, U if an injury is counted, else O.
  - Roadway is one free-text field: street pair ("X at Y", "X near Y", "X @ Y") 44.7%; a street alone 55.3%.
    MnDOT route codes (ISTH 94, USTH 169, MNTH 13, CSAH 81) are written as TIGER names by the reader.
  - Interstate (by Roadway text): 8.7%.
  - One row has an unquoted comma in Roadway; the reader rejoins it.
- Not in the public export: person, vehicle and unit records; collision type; light, weather, surface; road class.
  Other years' row counts: not measured.
- Licence: none found on the portal. Public data under the Minnesota Government Data Practices Act (Minn. Stat. ch. 13).
  Verdict for paid use: **unclear**.
- MnDOT MnCMAT2 (crash mapping for agencies) needs a login: not used.

## 2. Placement sample (the California way)
`placement_sample.py`, output `placement_sample.json`: 2000 random 2024 Hennepin County crashes, TIGER/Line 2024 network
(27053), GPS hidden, `locate.place`, scored with `Gate(tiger_only_auto=True)` (TIGER-only network).
- GPS share 100.0%; street pair 50.6%; of the pairs, "near" 17.9%.
- Name-placed 30.8% of all (60.8% of pairs); auto 30.0%.
- Within 250 ft of the hidden GPS (auto): 70.5%, Wilson 95% low 66.8%.
- Misses: "near" crashes have no distance, and freeway crashes ("WB ISTH 394 @ LOUISIANA") place at the crossing, not on
  the ramp or mainline where the officer put the point. Not needed for placement: only 4 statewide crashes lack a point.
- House addresses: none in the export.

## 3. End-to-end (live, port 8101)
Lake St (OSM ref Hennepin CR 3), Lyndale Ave S to Portland Ave, Minneapolis, 0.9 mi, 2020-2024:
pulled 1060, counted **519** (excluded 541 by the corridor rules; breakdown not read),
K 3 / A 17 / B 65 / C 143 / U 0 / O 291. Cost $134,078,000 (MnDOT
SFY 2026 values). Findings shown 4. PDF 74,572 B, Excel 35,547 B, 252 s.
Reader cleaning: 54 blank severities from counts, 0 contract errors.

## 4. Wiring
None needed beyond the plug-in. Shared-code notes: `shared-fixes.md`.
