# Ohio crash data: import notes (Hermes, 2026-11-08)

Bucket **A\*** (verified live; the 2026-11-02 screen said D because it only looked at GCAT). Status **active**.

## Sources

1. **ODOT TIMS public crash layers**: one ArcGIS map service per year,
   `https://tims.dot.state.oh.us/ags/rest/services/Safety/<year>_Crash_Locations/MapServer/0`. No login. Listed in
   the `Safety` folder: 2021, 2022, 2023, 2024, 2025 (2020 answers "Service not found"). Query, JSON, max 2,000,000
   records per request, pagination supported.
   - Rows (returnCountOnly, 2026-11-08): 2021 269,674; 2022 265,502; 2023 252,570; 2024 251,091; 2025 264,530.
   - 2025 fatal crashes: 1,033. ODOT's own 2025 table (CrashCostsUpdate.pdf p. 1) lists 264,529 crashes and 1,033
     K, so the layer is ODOT's whole statewide crash file, not a filtered copy.
   - Columns: DOCUMENT_NBR (OH-1 document number, unique key), CRASH_YR, MONTH_OF_CRASH, DAY_IN_WEEK_CD,
     HOUR_OF_CRASH, CRASH_SEVERITY_CD/TXT, CRASH_TYPE_CD/TXT, ODOT_CRASH_LOCATION_CD/TXT (intersection kind, ramp,
     driveway…), FUNCTIONAL_CLASS_CD, ODOT_LANES_NBR, COUNTY_CD (ODOT 3-letter), ODOT_DISTRICT, ODOT_LATITUDE_NBR,
     ODOT_LONGITUDE_NBR, NLFID (ODOT route id), CTL_BEGIN_NBR (log point).
   - **Not in the layer:** day of the month, street names, cross street, people killed/injured, light, weather,
     surface, units/persons.
   - Severity (2024): Fatal 1,077; Serious Injury Suspected 6,148; Minor Injury Suspected 32,822; Injury Possible
     24,445; PDO/No Injury 186,599. That is KABCO (K/A/B/C/O).
   - GPS: 0 of 251,091 2024 rows have a null or 0 latitude.
   - Day-of-week codes: 2024 counts by code are 1: 26,852; 2: 34,590; 3: 38,503; 4: 37,541; 5: 38,517;
     6: 42,906; 7: 32,182. That fits 1 = Sunday … 7 = Saturday (Friday is the busiest day). It's inferred from the
     counts; ODOT's code list wasn't found.
2. **ODPS Crash Statistics** (`https://ohtrafficdata.dps.ohio.gov/CrashStatistics/Home`): the full OH-1 CSV for a
   county or the state, 5 years plus the current year, **emailed within 24 hours** after a captcha. It's free and
   public, with no account, but it can't be scripted (captcha, email link, PIN). It has the full date, the streets
   and the persons. Not built; this is the "bring your export" path if a user needs those fields.
3. **ODOT GCAT / AASHTOWare Safety**: agencies and pre-qualified consultants only (TIMS User Guide §7). Gated.
4. **OSHP OSTATS dashboard**: aggregate dashboards only.

## Licence

TIMS support page (https://tims.dot.state.oh.us/tims/support): *"The data published within the Ohio Department of
Transportation (ODOT) TIMS application is in the public domain and as such it is not copyrighted. Individuals can
use, reproduce or copy material from TIMS, such as tables, figures, or downloadable files without seeking permission
from ODOT."* … *"The crash location data is owned and provided to ODOT by the Ohio Department of Public Safety (ODPS).
No protected information (e.g. personally identifiable information) is available within this version of crash
data."* Also: *"TIMS REST endpoints are maintained to support the TIMS application and are subject to change without
notice."* The layer's licenseInfo: *"deemed to be public information … no warranties, expressed or implied"*.
Verdict for paid use: **ok_with_attribution** (public domain, credit ODPS/ODOT). The catch is that the endpoint may
change without notice.

## Placement sample (research_notes/oh-2026-11-08/placement_sample.json)

Franklin County (39049) 2024: 24,049 rows. The sample is 2,000 rows (10 pages of 200 at seeded random offsets).
- GPS present and plausible: 2,000 / 2,000 (100%); all inside the county box.
- No street names, so name placement (TIGER + `locate.place`) **can't be measured** and isn't needed: every crash has
  GPS. House-address share: not applicable.
- The NLFID gives a route for interstate/US/state-route crashes: 38.5% of the sample (IR 307, US 246, SR 217). The
  rest are municipal (MR 719), county (CR 408), ramp (RA 45) and township (TR 41) inventory ids, which aren't names;
  17 rows have no NLFID.
- Location type: Not An Intersection 1,360; Four-Way 339; T 188; 5+ point 54; roundabout 27; ramps 23; driveway 9.

## Reader

`backend/crashiq/sources/oh_tims.py`, `fetch_contract(box, county_fips, years, cache_dir)`:
- Queries each year's service by a lat/lon box on the attribute columns. Pages of 2,000, ordered by OBJECTID.
- A year with no service goes in `years_missing`.
- Caches final years as raw JSON per box and year.
- Severity: code 1-5 is K/A/B/C/O. An unknown code is dropped, never guessed.
- `date` is `""` (no day of month; the year, month, weekday and hour are kept). `killed`/`injured` are 0 (not
  published; PACK.data_notes says so).
- `is_freeway` = functional class 1-2. `ped` = crash type Pedestrian, `bike` = Pedalcycles.
- `road_number` = I-/US/SR route from the NLFID (kept out of `primary_road`, so an intersection crash coded to the
  crossing state route isn't thrown out as "not on the corridor street").
- County: ODOT's 88 codes sort in county-name order, so FIPS = 39 + 001, 003 … (the test checks each code's letters
  in the county name). During research, each code's mean 2024 point was checked to fall inside its county's box
  (88/88).

## End-to-end (port 8102, 2026-11-08), research_notes/oh-2026-11-08/e2e_result.json

- **Corridor:** N High St (US 23), Columbus, 5th Ave to Lane Ave, 1.21 mi, from the Overpass way geometry. Window
  2021-2025 (the default).
- **Crashes:** 643 pulled, **500 counted**: 486 at intersections, 14 on segments. 143 excluded: 113 outside the
  100-ft buffer, 30 outside the study limits. 0 unplaced.
- **Severity:** K 1, A 13, B 98, C 60, U 0, O 328 (KSI 14).
- **Crash cost:** $19,297,824 (ODOT 2025 economic unit costs).
- **Findings:** 9 shown.
- **Exports:** PDF 92,589 bytes, XLSX 42,605 bytes. 114 s.

## What wiring/shared code would need
See shared-fixes.md (partial dates; routes as street names).

## Not checked
- The ODPS emailed CSV's columns (it needs an email and a captcha; the user's action).
- ODOT's day-of-week code list (inferred from counts).
- Statewide rates and AADT.
- Whether TIMS will keep the 2021 layer when 2026 arrives (a five-year rolling window is likely; ODPS keeps 5 + 1).
