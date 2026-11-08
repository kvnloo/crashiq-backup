# Missouri crash data: import notes (Hermes, 2026-11-08)

All numbers measured live on 2026-11-08 unless marked. The 2026-11-02 screen called Missouri bucket D ("aggregate
only"); **wrong**: MSHP's public crash map runs on an open ArcGIS layer with every STARS crash report, statewide,
record-level, with GPS and the officer's street names. **Verified bucket: A\*** (open, record-level, GPS + street names;
catches: no B/C split, PDO missing from 2024 on, no licence).

## 1. Source: MSHP STARS crash layer (verified)

- Layer: <https://www.mshp.dps.missouri.gov/arcgis/rest/services/STARS_CRASHES/MapServer/0> ("CRASHES"), found in
  the script of MSHP's "Traffic Crashes Online Mapping" (<https://www.mshp.dps.missouri.gov/TR15Map/index.jsp>,
  `tr15map.js`: `gishost + "/arcgis/rest/services/STARS_CRASHES/MapServer"`). ArcGIS 10.81, Query, 10,000 rows a call,
  paging. **No login.** (MoDOT's own "Crash Statistics Map" is "Internal or Authorized users only",
  <https://www.modot.org/modatazone/safety>; not used.)
- Rows: 1,972,333, 2002-01-01 to 2026-11-04. Per year: 2002 168,643; 2003 80,110; **2004-2012 none**; 2013 139,324;
  2014 137,444; 2015 148,649; 2016 158,085; 2017 154,971; 2018 155,947; 2019 157,077; 2020 131,425; 2021 146,757;
  2022 138,479; 2023 137,125; 2024 59,769; 2025 34,338; 2026 (to 11-04) 24,190. first_year = 2013.
- Severity (SEVERITY): 2023 Fatal 922 / Personal Injury 34,861 / Property Damage 101,342; **2024: 899 / 34,247 /
  24,623; 2025: 870 / 33,468 / none**. Fatal and injury crashes are complete through 2025; property-damage crashes
  stop being loaded in 2024 (cause not known: the 2024 MUCR change, or a load lag).
- Columns (57): ACCIDENT (report number), AGENCY, ACC_DATE, INV_DATE, COMPLAINT, INJURED, KILLED, **MIN_INJ, DIS_INJ**,
  SEVERITY, COUNTY, CITY, TROOP, NO_VEHICLE, MOTOR_VEH, LEFT_SCENE, **DIST_FEET, DIST_MILE, INTER_LOC, DIRECTION,
  ON_STREET, AT_STREET**, LIGHT_COND, ACC_TYPE (first harmful event type), ON_OFF_RD, TWO_VEH (two-vehicle code),
  DAY_WEEK, driver flags (DR_DRINK, DR_DRUG, SPEED, DR_UNDER21 ... CELL_PHONE, TEXTING), vehicle flags (TRUCK,
  MOTORCYCLE, ATV, PICKUP, CMV, SCHOOL_BUS), **GPS_LAT, GPS_LONG**, ACC_TIME.
- **Injury levels**: only DIS_INJ (disabling = MUCR "Suspected Serious Injury", A) and MIN_INJ. MUCR 2019 has
  "Evident - Not Disabling" and "Probable - Not Apparent" (Preparation Manual p. 93, PDF p. 101), but the layer adds
  them into MIN_INJ, and MoDOT maps "Minor Injury" to "B & C" (EPG 905.3.6.1.4). So K / A / **U** / O.
- Roads: "On" and "Intersecting" with MUCR prefixes: CST city street, CRD county road, PVT private road, PP private
  property (parking lot), IS interstate, US, MO, RT letter routes, BU business, LP loop, NOR/SOR outer roads; the
  intersecting field also holds RP (MoDOT ramp/reference point), ERM (emergency reference marker), BRIDGE and CO
  (crossover). INTER_LOC = AT / A (After) / B (Before) the intersecting road along the roadway direction, with
  DIST_FEET (MUCR Preparation Manual 2019, Location, p. 40-41).
- No driver, vehicle or person rows; no weather or surface columns. ACCIDENT + AGENCY is unique (0 duplicates in
  Jackson 2023).

### Licence

None published: the service's copyrightText is empty; the MSHP pages carry no data licence (privacy statement only).
**unclear** for paid use.

## 2. Placement sample (Jackson County, Kansas City, 2023)

- 19,822 crashes; GPS on **95.0%**; On street 99.5%; On + Intersecting street 85.2%; a
  distance + direction 68.6%. Severity {'O': 13847, 'A': 537, 'U': 5316, 'K': 122}; interstate 12.7%.
- California way: 2,000 random crashes with GPS (seed 2026), GPS hidden, the road pair and offset placed on TIGER/Line
  2024 Jackson County with `locate.place` and `Gate(tiger_only_auto=True)` (TIGER-only network):
  - with a street pair 87.0%; tiers {'exact': 923, 'unique_pair': 315, 'review': 478, 'relaxed': 13, 'verified_typo': 5, 'near': 4, 'fuzzy': 1}
  - placed 63.0%, **auto-placed 61.9%**
  - auto-placed within 250 ft of the hidden GPS: **95.6%** (Wilson 95% low 94.3%); all placed 95.5%
  - not placed: {'no intersection of the two named streets': 421, 'no cross street in source': 261, 'exact: streets meet in more than one place': 49, 'relaxed: streets meet in more than one place': 7, 'fuzzy: streets meet in more than one place': 1}
- No-GPS crashes: 995 in Jackson 2023, 607 (61%) with a street pair; at the sample's auto rate
  that is about 432 more crashes placed (estimate, not measured on the no-GPS rows).
- House addresses: not measured (GPS on 95%).

## 3. Importer

`backend/crashiq/sources/mo_mshp.py` (`fetch_contract`: crashes with a point in the box plus no-GPS crashes in the
corridor's counties, which the core sorts by street name), plug-in `backend/crashiq/statepacks/mo.py`, status **active**,
first_year 2013. Tests `tests/test_source_mo.py` on `tests/fixtures/mo_mshp.json` (90 rows, 102 KB), recorded by
`mo_pull.py`.

## 4. End-to-end (Troost Avenue, 0.99 mi, E 31st St to E 39th St, Kansas City)

Default window 2020-2024. Read 5,143 rows (4,654 without GPS, from Jackson County, sorted by street
name), kept 523, counted **307**: K 1 / A 5 / U 116 / O 185; 5 unplaced, 211 outside the study,
0 contract errors. No crash cost (missing, cited). 8 findings. PDF 53,885 B, Excel 36,513 B. 2024 in the
window has few PDO crashes (§1).

## 5. Cities

- Kansas City Open Data "Kansas City Road Casualties" (<https://data.kcmo.org/d/62pj-bjfw>): MSHP STARS rows for KC,
  injury and fatal only, on/at street, no coordinates, no licence field. Adds nothing over the state layer: not read.
- St. Louis: no open crash table found (SLMPD daily accident report only).

## Blockers / user actions

- Ask MSHP (Statistical Analysis Center) in writing whether CrashIQ may show the STARS crash layer in a paid tool,
  and whether property-damage crashes for 2024 on will be loaded.
- Optional: ask MoDOT for crash costs (EPG: "Contact the MoDOT project core team for the appropriate values").
