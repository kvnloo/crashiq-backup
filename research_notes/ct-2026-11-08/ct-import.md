# Connecticut: statewide crash data for CrashIQ (Hermes, 2026-11-08)

**Bucket A\*** (verified live 2026-11-08): open, record-level, statewide, a point on every crash, KABCO. Catch: no reuse licence.
**Status: active** (pack `backend/crashiq/statepacks/ct.py`, reader `backend/crashiq/sources/ct_uconn.py`).

## Source
- Connecticut Crash Data Repository (CTCDR), UConn Connecticut Transportation Safety Research Center for CTDOT.
  Public ArcGIS MapServer, no login: <https://gis.cti.uconn.edu/arcgis/rest/services/Crash_Dashboards/ConnecticutCrash/MapServer>
  - layer 0 Crash, 1 Person, 2 Vehicle; all point layers keyed by `CrashID`; maxRecordCount 2,000 (paged by OBJECTID).
  - Is it open or registration-only? **Open.** The CTCDR web tool (<https://www.ctcrash.uconn.edu/>) shows "User: not
    logged in" and queries without an account; the MapServer answers anonymous REST queries. No registration was used.
- Crashes per year (layer 0, `groupByFieldsForStatistics=CrashDateYear`, 2026-11-08):
  2015: 111,169, 2016: 115,935, 2017: 115,648, 2018: 114,156, 2019: 112,611, 2020: 83,791, 2021: 101,159, 2022: 102,802, 2023: 100,437, 2024: 104,258, 2025: 103,457, 2026_to_2026-11-06: 57,920. Latest CrashDate 2026-11-06.
- Crash fields: CrashDate (UTC instant), CrashTimeHour, CrashTownName, NameOfRoadway, NameOfIntersectingRoadway,
  RouteClass (Interstate / USRoute / State / Local...), MostSevereInjury (KABCO words with the letter), CrashSeverity,
  MannerOfCrashCollisionImpact, LightCondition, WeatherCondition, TrafficSurfaceCondition, FirstHarmfulEvent,
  TypeOfIntersection, CrashSpecificLocation, LawEnforcementAgencyName, work zone, school bus.
  Person: InjuryStatus, PersonType, Age, Gender, RestraintSystem, SpeedingRelated, DriverDistractedBy,
  ContributingCircumstances... Vehicle: VehicleBodyType and more.
- Lag (CTCDR notes): PDO about 3 months, fatal 3-6 months. The pack sets `final_lag_months=6`; the current year is
  `preliminary`.

## Licence (paid use: unclear)
CTCDR home page, 2026-11-08: "This data repository enables users to query, analyze and print/export the data for
research and informational purposes." and "This web site is exempt from discovery or admission under 23 U.S.C. 409."
No licence on the MapServer. The pack prints the 409 sentence on every export (`legal`).

## Measured on Hartford 2024 (6,107 crashes, 14,599 person and 12,088 vehicle rows)
- Reader contract (`packs.check_crash`): 0 errors on all 6,107.
- GPS: 100% inside the state box. Intersecting road named: 25.1%.
- Severity (crash): K 16, A 58, B 781, C 707, O 4,545 (no U). 15 crashes have no MostSevereInjury (all PDO).
- Collision words mapped to CCRS: REAR END 1,917, SIDE SWIPE 1,623, BROADSIDE 1,392, HEAD-ON 131; others keep CTCDR's words.
- Route roads come as `84-W`, `44-E`, `187-N` with RouteClass; the reader writes `I 84`, `US 44`, `CT 187` (OSM refs).
  The intersecting road has no class, so the number decides (CT Interstates 84/91/95/291/384/395/691, US 1/5/6/7/44/202,
  else CT). Ramps (`91-S-165A (EXIT 33)`) stay as written. Town suffix `MAIN ST NO 1` -> `MAIN ST`.

## Placement sample, the California way (`placement_sample.py`, `placement_sample.json`)
2,000 random Hartford 2024 crashes; GPS hidden; TIGER/Line 2024 network of the Capitol Planning Region (09110).
- GPS present and plausible: 100.0%. Naming both roads: 23.6%.
- Placed by name: 19.8% of all, 83.7% of pairs (tiers {'review': 77, 'exact': 391, 'near': 3, 'unique_pair': 1}).
- Within 250 ft of the hidden point: 97.7% of placed (Wilson 95% low 95.7%).
- Default `Gate()`: 0 auto, because the sample network is TIGER-only and `tiger_only_auto` is false. With
  `tiger_only_auto=True`: 83.0% of pairs, 97.7% within 250 ft (low 95.7%).
- Not placed: {'no intersecting road in source': 1528, 'no intersection of the two named streets': 61, 'exact: streets meet in more than one place': 16}. "More than one place" comes from the region-wide network (MAIN ST & PARK ST exists in
  several towns); the app builds a corridor-sized network, so that case doesn't arise there.
- No-GPS crashes it would add: none (every crash has a point). House addresses: none in the source.

## End to end (port 8104, 2026-11-08)
Farmington Avenue, Hartford, 1.19 mi, 2021-2025: 1,765 rows read, 0 contract errors, 864 kept,
**498 counted** (366 excluded, off the corridor), K 2 A 6 B 76 C 65 U 0 O 349,
crash cost $32,683,409 (CTDOT HSIP costs), 10 findings, PDF 74,658 B, Excel 39,755 B.
Overpass was busy once (retried).

## Not done / not checked
- Vehicle movements, primary collision factor, DUI, speed: not mapped (data notes in the pack say so).
- data.ct.gov / CTDOT open-data copies: not re-checked; the MapServer is the source.
- NAD / address points: not needed (100% GPS), not checked.
- Shared code: see `shared-fixes.md` (one locator name form).
