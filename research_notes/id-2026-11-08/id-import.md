# Idaho: crash data for CrashIQ (Hermes, 2026-11-08)

Every number below was measured live on 2026-11-08 unless marked. Script: `id_pull.py` (placement sample + fixture);
sample result in `placement_sample.json`; end-to-end result in `e2e_result.json`.

## 1. Sources

### 1a. ITD CrashLayers MapServer: the source used
- Service: https://gis.itd.idaho.gov/arcgisprod/rest/services/ArcGISOnline/CrashLayers/MapServer (no login).
  The same crash layer is also published as layer 123 of `IdahoTransportationLayersForOpenData/MapServer`
  (ArcGIS Online item f0577496f6fb4e2f89d14b194bf496df). Copyright text: "ITD GIS and ITD Office of Highway Safety".
- Layers: 11 "Crash 2005 to Present" (one row per crash), 35 "Crash Unit 2005 to Present", 23 "Crash Person 2005 to
  Present", plus one layer per year. maxRecordCount 70,000; pagination supported. All share `Serial_Number`.
- Crash fields: Severity, Serial_Number, Accident_Year, Accident_Date_Time, Latitude/Longitude (text), County,
  Number_Of_Fatalities, Number_Of_Injuries, IntersectionRelated (Y/N), RouteID + Measure, Mile_Point (empty).
  **No street names, no lighting, weather or surface.**
- Unit fields: Unit_Number, Vehicle_Type (Car, Pickup, Pedestrian, Pedalcycle, Motorcycle, Tractor - 1 Trailer, ...),
  Most_Harmful_Event (Rear-End, Angle Turning, Head-On, Overturn, ...), Contrib_Circ_1-3 (Failed to Yield, Following
  Too Close, ...).
- Person layer: Severity is the **crash's** severity repeated on every person (2022: 461 "Fatal Accident" person rows vs
  194 fatal crashes), so there is no per-person KABCO.
- Rows per year (layer 11): 2005 28,347 · 2006 24,311 · 2007 26,643 · 2008 25,240 · 2009 23,063 · 2010 22,631 ·
  2011 21,179 · 2012 21,676 · 2013 22,577 · 2014 22,428 · 2015 24,146 · 2016 25,494 · 2017 25,921 · 2018 24,306 ·
  2019 27,136 · 2020 22,637 · 2021 27,620 · 2022 27,678 · **2023 18,488** · no 2024, no 2025. Total 461,521.
- **2023 is part-loaded:** its newest crash is 2023-10-01 (Jan-Aug about 2,100-2,350 a month, Sep 1,291, Oct 1, Nov-Dec
  0). ITD's 2024 annual report counts 27,679 crashes in 2023 (https://apps.itd.idaho.gov/Apps/OHS/Crash/24/Analysis.pdf).
  The reader treats any year after the layer's last full year as missing.
- Severity (all years): Fatal 3,828 · A 20,452 · B 54,278 · C 86,094 · Property Dmg Report 296,869. KABCO.
- GPS: missing on 28,253 (2005), 23,958 (2006), 10,862 (2007), 11 (2008), 2 (2009), 1 (2010), 0 since. 2018-2023
  every row falls inside Idaho's envelope (counts equal per year). `first_year` = 2008.
- Route id: `02290AIN084` = system `IN` (Interstate) 84; `US`, `SH` (state highway), `OH` (off the state system),
  `PO`. Ada 2022: OH 4,620 · IN 788 · SH 763 · US 454 · PO 57.
- Times: `Accident_Date_Time` is Idaho wall-clock time sent as UTC (matches `Accident_Time` "21:35" ↔ 21:35 UTC).

### 1b. Other ITD channels (not used)
- ITD Crash Data Dashboards (AASHTOWare Safety, https://itd.aashtowaresafety.net/itd-safety-dashboards): "the last
  five full years" (ITD safety page). It's a vendor web app; it has internal query/CSV endpoints but no documented API
  and no licence, so it isn't used. Its data is newer than the open layer, which makes it the best thing to ask ITD about.
- Single crash reports: $7 each (https://apps.itd.idaho.gov/apps/HWY_CrashReports). Not usable.
- City feeds: COMPASS (Ada/Canyon MPO) republishes ITD crash data (screen 2026-11-02); not needed, statewide covers it.

## 2. Licence (paid use: unclear)
ITD's spatial data disclaimer, on its ArcGIS Online items: "The Idaho Transportation Department (ITD) provides this
geographic data and any associated metadata "as is" without warranty of any kind … It is the sole responsibility of the
user to determine the usability of the data for their purposes. In no event shall ITD have any liability …". No reuse
grant and no restriction found. Verdict `unclear`; shown on every export page (`legal`).

## 3. Placement sample (Ada County / Boise, 2022, every row)
- n = 6,682; GPS on 100%; 99.97% inside Ada's box; Serial_Number unique; all map to FIPS 16001.
- Severity K 19 · A 216 · B 884 · C 1,185 · O 4,378. Intersection-related 54.8%.
- Units joined for 6,671 of 6,682 crashes; 68 pedestrian and 101 bicycle crashes.
- Hidden-GPS locator test: **not run**, the layer has no street text to place from. House-address share: 0 (none).

## 4. Reader and pack
- `backend/crashiq/sources/id_itd.py`: envelope query on layers 11 and 35, paged by OBJECTID, joined by Serial_Number;
  one statistics query for the newest crash date (part years → `years_missing`).
- `backend/crashiq/statepacks/id.py`: `status="active"`, `first_year=2008`, `final_lag_months=46` so the default
  window is 2018-2022 while ITD's lag lasts.
- Tests: `tests/test_source_id.py` on a 46 KB fixture of 58 live crashes and 105 units.

## 5. End-to-end
W Fairview Ave, Orchard St to Cole Rd, Boise (1.55 mi), 2018-2022: pulled 592, counted 230; K 0 / A 8 / B 24 / C 40 / U 0 / O 158;
cost $14,406,270 (ITD 2025 costs); 0 findings; PDF 33,291 B, Excel 33,843 B; 127 s. Contract errors 0 (`e2e_result.json`).

## 6. What we didn't check
- Whether ITD will grant paid use; whether the dashboard's newer years can be exported.
- Whether ITD's crash points on local roads were geocoded by the officer or by ITD (accuracy not measured).
