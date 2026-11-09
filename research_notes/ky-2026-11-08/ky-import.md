# Kentucky crash data: import notes (Hermes, 2026-11-08)

All numbers measured live on 2026-11-08 unless marked.

## 1. Source: KSP Collision Analysis for the Public (verified)

- Site: <http://crashinformationky.org/> (Kentucky State Police, KyOPS collision reports from every Kentucky agency).
  Linked from KYTC Highway Safety Resources as "query page for KY State Police public access crash database"
  (<https://transportation.ky.gov/HighwaySafety/Pages/Resources.aspx>).
- Access: **open, no login**. The site's Location Search page makes two calls that CrashIQ reuses:
  - `POST /LocationSearch/ExecuteQuery` (form fields: anti-forgery token from the page, `ListCounties`, `DateRangeStart`,
    `DateRangeEnd`, `Polygon` = `(lat, lon)|(lat, lon)|…|`, `incidentTypeEnum=0`). Returns one row per crash, 39 columns:
    agency, county, KYTC road number (`KY1931`, `US0060`, `I 0024`, `WK9001`), street number, roadway name, location
    description, milepoint, date, time (`0840`), intersection road, between-streets 1 and 2, vehicles, units, number
    killed, number injured, weather, road condition, hit and run, direction-analysis code, manner of collision, road
    character, light, ramp from/to, `xIncidentGUID`, `xIncidentID`.
  - **The grid's Latitude/Longitude are rounded to whole degrees** (all 86 rows of a test = 38.0, -86.0).
    `POST /AdvancedSearch/GetMappingDataByReportType` with the rows' GUIDs (`aIncidentGUID[]`, `sIncidentType=03`)
    returns the full point (`xLatitude` 38.201528630, `xLongitude` -85.793741524) and a category (1 killed, 2 injured,
    3 property damage). 2,000 GUIDs answered in 3 s.
- Limits: a county-only search over more than ~2 weeks statewide answers "Result set is too large" (the county list
  doesn't filter without a shape: 14 days = 4,725 rows from all over the state). A polygon search answers whole years
  (central Louisville 2 km box: 159 crashes in 2024, 583 in 2020-2024, 82 s); the reader halves any range the site
  calls too large.
- Years: polygon searches return rows for January 2015, 2016 and 2019 (190 / 225 / 161 in a small downtown box), so
  the reader starts at 2015. KyOPS is updated daily.
- Statewide totals for comparison (KTC, Analysis of Traffic Crash Data in Kentucky 2020-2024, Table 1, PDF p. 20):
  119,962 / 131,752 / 130,347 / 139,268 / 139,662 crashes in 2020-2024.
- **Severity: not KABCO.** Public rows have the number killed and injured only. KABCO exists in KYTC's CRASH database
  (Table 1 above gives K/A/B/C/O) and in the Advanced Search model (`Person_Collision.InjurySeverityCde`), but every
  Advanced Search query we built answered "Sorry, an unexpected error occurred". So K / U / O only; A, B, C never
  invented (`severity_note`).
- Person/vehicle tables: none public. KTC's CDAT (crashtool.uky.edu) has them but needs a signed MOU with KYTC.
- Other open sources checked: KYTC's ArcGIS server (maps.kytc.ky.gov) and ArcGIS Online (KYTCGIS) have no crash
  point layer (only network screening and curve layers); KOHS dashboards are Power BI (aggregate). Louisville (LOJIC)
  publishes a High Injury Network, not crash points.

### Licence

No licence is published. The home page says: "The integrity of the data is dependent upon both the accuracy and
frequency with which the data is entered and user’s interpretation. Therefore, no warranty, either expressed or
implied, is given to the accuracy, completeness, reliability, or suitability for any particular purpose of the
information contained in this website." Paid-product use: **unclear**; ask KSP.

## 2. Sample (central Louisville, 2025-01-01 to 2025-02-28, every row, through the reader)

- 1,970 crashes, all Jefferson County; GPS on 100%, every point inside the query box.
- Roadway name 96.2%; roadway + intersecting or between street 50.7%;
  street number 21.3%.
- Severity: {'O': 1692, 'U': 273, 'K': 5}. Freeway (interstate or parkway) 19.0%; parking-lot crashes
  5.1%.
- Earlier statewide check (14 days Jan 2024, 2,000 rows mapped): every one had a point.

## 3. Placement, the California way

Jefferson County (21111), 2025-01..02, random 2,000 with GPS (seed 2026): hide the GPS, place roadway + cross street on Census TIGER/Line 2024 Jefferson County with
`locate.place`, scored under `Gate(tiger_only_auto=True)` (TIGER-only network; plain `Gate()` auto-places 0 there).

| measure | value |
|---|---|
| crashes with a street pair | 50.7% |
| placed from names (any tier) | 44.2% of all |
| auto-placed | 43.7% of all |
| auto-placed within 250 ft of the hidden GPS | 86.9% (Wilson 95% low 84.5%) |
| tiers | {'review': 128, 'exact': 457, 'unique_pair': 404, 'verified_typo': 1, 'near': 7, 'fuzzy': 1} |
| not placed | {'no cross street in source': 972, 'no intersection of the two named streets': 94, 'exact: streets meet in more than one place': 21, 'relaxed: streets meet in more than one place': 13} |

GPS covers essentially all crashes, so names add nothing to coverage; they serve the not-on-the-corridor-street
check. Formats that break the locator (shared-fixes.md): ramp text as the cross street ("I264 EB EXIT17A OFF RAMP TO
KY155 SB"), route numbers written without a space ("KY1747", "I264"), and roadway names without a suffix ("PRESTON").
House addresses: not measured (GPS on every crash).

## 4. End-to-end (port 8103, 2026-11-08)

Corridor Bardstown Road, Louisville, Grinstead Dr to Taylorsville Rd area, 0.84 mi (polyline from
OSM way geometry), window 2020-2024:
pulled 391, counted 294 (excluded 97: 66 outside study limits, 27 outside buffer, 4 not on
the corridor street), K/A/B/C/U/O = {'K': 0, 'A': 0, 'B': 0, 'C': 0, 'U': 58, 'O': 236}; crash cost not computed (no Kentucky cost table);
findings shown 8; PDF 67,287 bytes, Excel 41,972 bytes;
165 s.

## 5. What wiring needs

Nothing beyond the plug-in (`statepacks/ky.py`). The reader holds a cookie session per pull; a pull of a 1-mile
corridor for 5 years is 5 polygon searches + 1 mapping call.
