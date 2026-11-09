# Illinois crash data: import notes (Hermes, 2026-11-08)

**Verdict: bucket A, `status="active"`.** The 2026-11-02 screen (bucket D, "IDOT Safety Portal needs County Engineer
vetting") was wrong: IDOT also publishes every crash, statewide, as open ArcGIS layers.

## 1. Source (checked live 2026-11-08)
IDOT open data hub <https://gis-idot.opendata.arcgis.com/>, items "Crashes - 2014" … "Crashes - 2025" (owner
IDOTAdmin), hosted layers under `https://services2.arcgis.com/aIrBD8yn1TDTEXoz/arcgis/rest/services/<name>/FeatureServer/0`
(names in `il_idot.LAYERS`). Description: "Crash data shared out to the public. Created after the year is frozen."

| year | rows | | year | rows |
|---|---|---|---|---|
| 2014 | 296,194 | | 2020 | 246,868 |
| 2015 | 313,319 | | 2021 | 295,634 |
| 2016 | 324,496 | | 2022 | 298,431 |
| 2017 | 311,930 | | 2023 | 300,144 |
| 2018 | 319,213 | | 2024 | 303,927 |
| 2019 | 313,185 | | 2025 | 303,087 |

- **Coverage:** every police-reported crash in Illinois, Chicago included (2025: 100,055 rows with CityName Chicago;
  Cook County 163,543).
- **GPS:** 2025: 538 of 303,087 without a point (99.82% with). Use the layer geometry: the 2014 layer's own
  `TSCrashLongitude` column is unsigned (87.89).
- **Severity:** IDOT crash KABCO (`CrashInjurySeverity` Fatal / A / B / C Injury Crash / No Injuries; `CrashSeverityCd`
  4-0) plus `TotalFatals`, `AInjuries`, `BInjuries`, `CInjuries`. The worst count equals IDOT's KABCO row for row
  (2025: K 1,073, A 6,382, B 33,160, C 22,131, O 240,341; 2014 the same; 0 injury crashes without a level).
- **Street names: 2025 only.** `HighwayorStreetName` (3 blank in 2025), `AtIntersectionWith` ("<road>/<cross>"),
  `AddressNo`, `NonIntersectionDistance/Units/Direction`. 2014-2024 have `RouteNumber` + `Milestation` only.
- **2019 layer defect:** ~25% of rows have every column after `TrafficwayDescrip` shifted one place by an unquoted
  comma ("Divided, No Median Barrier"): `CrashSeverityCd` reads "C"/"I"/"M", `RoadwayFunctionalClass` reads
  " No Median Barrier". Counts, dates, light, weather, surface and first-crash type come before it and are fine.
  The reader takes severity from the counts and freeway from `RoadwayFunctionalClass` or `ClassOfTrafficway`.
- **Persons and vehicles:** only 2025, in "Crashes Extract - 2025" (`CrashExtract2025` layers 1 and 2: 692,501
  persons with `PersonInjuryClass`, 574,716 vehicles), linked by CrashID/ICN. Not read yet.
- **Gated:** IDOT Safety Portal / I-CARS (<https://webapps1.dot.illinois.gov/SafetyPortal/>): "please work with your
  specific County Engineer to be vetted by them" (CL 2026-09). Not needed.

### Licence
- 2014-2020 items: "This work is licensed under a Creative Commons … by-sa/2.0".
- 2024 item (licenseInfo): "The Illinois Department of Transportation and the State of Illinois hereby give notice to
  all users that these maps and the data included hereon, lack the accuracy required for site-specific uses … make no
  representation, guarantee, or warrant …".
- 2021-2023 and 2025 items: no licence text. **Paid use: unclear** (CC BY-SA is share-alike for the old years).

## 2. Placement, the California way (2025 layer, TIGER/Line 2024, `Gate(tiger_only_auto=True)`)
`il_pull.py` → `placement_sample.json`.
- **DuPage County** (suburbs, 13,192 rows in the box): random 2,000 with GPS. Road + cross street on 39.6%.
  Auto-placed **32.0%**; within 250 ft of the hidden GPS **92.5%** (Wilson 95% low 90.2%). House number on 7.4%.
- **Chicago** (Cook, 37,696 rows in the box): Chicago reports locate by house number (84.6%), not a cross street
  (0.5%): street-pair placement 0.4%. House-address placement not measured (no address-point layer run).
- GPS is on 100% of both samples, so name placement only matters for the 0.18% with no point (not read; see below).
- What breaks (shared-fixes.md): `Il Route 59`, `E Il-38`, `Route 30` (US or IL?), `S S Highland Ave`,
  `North Ave / Il-64`, ramp text in the cross street.

## 3. Reader and wiring
- `backend/crashiq/sources/il_idot.py`: envelope query → object ids → rows by id (1,000 a page, POST), cached per box
  and year. No-GPS crashes are not read (queried by point).
- `backend/crashiq/statepacks/il.py`: `status="active"`, first year 2014, `final_lag_months=8` (2025 posted in
  August 2026).
- Not used: Chicago's portal (<https://data.cityofchicago.org/d/85ca-t3if>, "See Terms of Use", 2025: 109,117 rows,
  daily to 2026-11-08). IDOT covers Chicago; the only gap is the current, non-final year.

## 4. End-to-end (port 8101, 2026-11-08)
N Western Ave, Chicago, Fullerton Ave to Belmont Ave, 1.01 mi, 2021-2025: pulled 1,773, **counted 796**, excluded 977,
unplaced 0. K/A/B/C/U/O = 1/13/67/49/0/666. No crash cost (methods: missing). 9 findings shown. PDF 88,752 B,
Excel 39,588 B, 112 s. `e2e_result.json`.

## 5. Not checked
House-address placement in Chicago; the 2025 person/vehicle extract; whether IDOT minds automated queries; IDOT's
current HSIP crash costs.
