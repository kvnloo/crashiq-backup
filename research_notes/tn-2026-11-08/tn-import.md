# Tennessee crash data: import notes (Hermes, 2026-11-08)

All numbers measured live on 2026-11-08 unless marked. The 2026-11-02 screen called Tennessee bucket D (gated); that is
right for full TITAN and wrong for CrashIQ: **TDOT publishes every crash statewide for 2021-2024 with a point and
KABCO**, and the Department of Safety publishes every fatal and injury crash since 2024 with GPS and KABC.
**Verified bucket: A\*** (open, record-level, located, KABCO; catches: no street names, no PDO statewide after 2024,
no licence).

## 1. TDOT statewide crash layer, 2021-2024 (primary)

- Layer: <https://services2.arcgis.com/nf3p7v7Zy4fTOh6M/arcgis/rest/services/Tennessee_Crashes_JAN_2021_JAN_2025/FeatureServer/0>
  (ArcGIS Online item 9a25e06f713a4a1688bec0a9cb2bc582, owner TDOT_GIS, public, modified 2025-08-13). Point layer
  (State Plane, read with outSR=4326), 2,000 rows a call, paging. **No login.**
- Rows: 763,379 (2021: 196,833; 2022: 193,471; 2023: 184,844; 2024: 179,966; Jan 2025: 8,265, not read).
- Columns: MSLINK, ID_NUMBER (county + route + section), BLM (log mile), RELATIONTO (junction), RELATIONT2,
  URBANRURAL, NBR_TENN_C (county), NBR_RT2 (route: `I0024`, `SR011`, local ids like `03252`), SPCL_CSE, CNTY_SEQ,
  CASENO, TDOTLOC (Along Roadway / At an Intersection / Ramp), YEAROFCRAS, DATEOFCRAS, TIMEOFCRAS (`1451`),
  **TYPEOFCRAS** (severity), TOTALKILLE, TOTALINJUR, TOTAL_INCA, TOTAL_OTHE, TOTALVEHIC, FIRSTHARMF, MANNEROFCO,
  WEATHERCON, LIGHTCONDI, LOCATE_TYP (Automatic 762,201 / Manual 1,177).
- **Severity is KABCO**: Prop Damage (over) 501,472 / Prop Damage (under) 83,608 / Possible Injury 80,645 / Suspected
  Minor Injury 73,233 / Suspected Serious Injury 19,442 / Fatal 4,979. Read K / A / B / C / O.
- Manner of collision: ANGLE 216,443, NO COLLISION W/ VEHICLE 198,747, REAR-END 182,514, SIDESWIPE SAME 64,887, ...
- No street names: a route number only (Davidson 2024: 63% of crashes on an I or SR route, read as
  `I 24` / `SR 11`; the rest are local road ids, no name). No person or vehicle rows.
- Davidson County 2024: 25,690 crashes, point on 100%, severity {'C': 2247, 'O': 17536, 'B': 5317, 'A': 484, 'K': 106}, freeway (interstate)
  25%.
- Agreement with TDOSHS for 2024 in Davidson (both layers have it): K 106 vs 106, A 484 vs
  493, B 5317 vs 5623, C 2247 vs 2369 (TDOT's snapshot is from January 2025; TDOSHS keeps updating).

## 2. TDOSHS crash dashboard layer, 2025 on

- Layer: <https://tnmap.tn.gov/arcgis/rest/services/SAFETY/MapForDashboards/MapServer/0> ("All Pulled Crash Records"),
  behind the "Searchable Crash Dashboard (Updated Weekly)" on <https://gis.safety.tn.gov> ("Current: 1/1/2024 -
  10/21/2026"). 2,000 rows a call. **No login.**
- Rows: 126,994 (2024: 45,524; 2025: 45,060; 2026 to 10-21: 36,410). **Fatal and injury only** (`Fatality = 0 AND
  Injury = 0` returns 0 rows). Crash_Type = Fatal / Suspected Serious / Suspected Minor / Possible Injury: KABC, no O.
- GPS: 15 of 126,994 rows without (99.99%). No street names, no road field, no manner, no surface.
- Flags "-" = no, the flag's name = yes, except **LargeTruck_Involved, whose yes value reads "ATV_Involved"** (7,893
  rows; the real ATV_Involved column has 314): any non-"-" value is read as yes.
- Davidson 2025: 8,733 crashes, severity {'B': 5641, 'C': 2562, 'K': 103, 'A': 427}, flags {'ped': 380, 'bike': 97, 'motorcycle': 244, 'heavy_truck': 511}.
- **TITAN** itself: "for the exclusive use of law enforcement agencies in the state of Tennessee. Membership is
  required" (<https://www.tn.gov/safety/stats/titan.html>): not used.

## 3. Nashville: Metro Traffic Accidents (fills the PDO gap from 2025)

- <https://services2.arcgis.com/HdTo6HJqh92wn4D8/arcgis/rest/services/Traffic_Accidents_2/FeatureServer/0> (item
  1df26ca05f3f407e95ab5a4fc013eab7, NashvilleOpenData): 223,465 rows 2019 to 2026-11, 1,000 a call; Lat/Long,
  Street_Address ("NOLENSVILLE PKE & THOMPSON LN"), injuries, fatalities, collision type, weather, light. No KABCO.
- 2025: 26,994 crashes, 18,495 with no one hurt. Times are true UTC (the layer says so; in Central time the night low
  falls at 2-4 am). CrashIQ reads only Metro's **no-injury crashes, as O, for 2025 on** (TDOT has every crash before).
- Double count check, Davidson 2025: 103 of 18,488 (0.56%) no-injury Metro crashes have a state
  injury crash within 100 m and one hour; left in.
- Address on 99.0%, cross street (" & ") on 72.2%; "PKE" read as "PIKE" (shared-fixes.md).

### Licence

- TDOT layer (item licence field): "All data presented here is for informational purposes only. Every effort is made
  to provide and maintain accurate, complete, and timely information on this Web site. However, some data may be
  incomplete or outdated. Neither the Tennessee Department of Transportation, the State of Tennessee, nor any agency
  thereof, nor any of their employees, make any warranty, express or implied, nor assume any legal liability or
  responsibility for the accuracy, completeness, or usefulness of the data..." **unclear** for paid use (no licence, a
  disclaimer only).
- TDOSHS: nothing published on the service or the dashboard page: **unclear**.
- Metro Nashville: item licence points to Open Data Executive Order FO018; Nashville.gov Terms of Service: "Excluding
  publicly available data on Metro's Open Data Portal, commercial use of the materials is prohibited without the
  written permission of the Metro" (<https://www.nashville.gov/departments/government/terms-service>):
  **ok_with_attribution**.

## 4. Placement

Every crash in all three layers carries a point (TDOT 100%, TDOSHS 99.99%, Metro 100%). Neither state layer has street
names, so the hide-the-GPS name test can't run (not measured). TDOT's points are snapped to its route network
(LOCATE_TYP Automatic): not checked against officer GPS.

## 5. Importer

`backend/crashiq/sources/tn_tdot.py` (`fetch_contract`: TDOT for 2021-2024, TDOSHS + Metro for 2025 on), plug-in
`backend/crashiq/statepacks/tn.py`, status **active**, first_year 2021. Tests `tests/test_source_tn.py` on
`tests/fixtures/tn_crashes.json` (58 TDOT, 36 TDOSHS, 7 Metro rows, 79 KB), recorded by `tn_pull.py`.

## 6. End-to-end (Nolensville Pike, 0.92 mi, Thompson Ln to Harrison St)

- Default window 2021-2024 (TDOT): pulled 516, counted **406**: K 3 / A 9 / B 107 / C 41 / U 0 / O 246;
  110 outside the study, 0 unplaced, 0 contract errors. No crash cost (missing, cited). 11 findings. PDF
  79,172 B, Excel 38,971 B.
- The TDOSHS + Metro path was run end to end earlier the same day for 2024, before TDOT's layer was found
  (`e2e_result_tdoshs_metro_2024.json`): counted 94, K 0 / A 6 / B 28 / C 8 / O 52. The reader now uses that path for 2025 on;
  a 2025 window isn't final yet, so it wasn't rerun.

## 7. Other leads

- Memphis MPO "Crashes 2020-2025" and "MPO_PDO_Crashes_2020_2025" (ArcGIS Online, owner memphistn.gov) exist; not
  read (TDOT's statewide layer covers Memphis to 2024).

## Blockers / user actions

- Ask TDOT (and TDOSHS for 2025 on) in writing whether CrashIQ may show these layers in a paid tool: no licence, a
  no-warranty disclaimer only.
- TDOT's layer stops in January 2025 (a snapshot): ask TDOT whether it will publish 2025. Until then, 2025 on has no
  PDO outside Nashville and no route numbers.
