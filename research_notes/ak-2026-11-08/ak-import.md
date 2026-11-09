# Alaska crash data for CrashIQ (Hermes, 2026-11-08)

**Bucket A\* (open, catches), status `active`.** The 2026-11-02 screen called Alaska gated (D): it found only DOT&PF's 2023 table, which has no location. Live checks found DOT&PF's **Public Crash Portal** (https://public.alaskadata.net/), which serves every crash of the latest five complete years with a map point and KABCO, no login.

## 1. Sources (verified live 2026-11-08)

### Public Crash Portal (used)
- An Angular app on CARE (University of Alabama CAPS). Its config (`/assets/config/config.json`) names the API `https://pub-ds.alaskadata.net/api/`, agency state `ALASKA_PUB_X`, dataset `DOTPFDataCrash`, and `showDownload: false`.
- `POST Datasource/PostExtendedMatchingDatasourceList {"state":"ALASKA_PUB_X"}`: `DOTPFDataCrash`, 42,988 crashes, MinimumDate 2021-01-01, MaximumDate 2025-12-31, BuildDate 2026-11-04, 43 categorical + 8 non-categorical variables.
- Reading rows: `POST FilterCache/PostReplacementFilterToCache?datasourcename=DOTPFDataCrash` with a date-range builder returns a filter id (2024: SelectedCount 9,209), then `GET VariableData/GetFileDownload?fileFormat=1&datasourcename=DOTPFDataCrash&filterid=<id>&CategoricalVariableName=...&NonCategoricalVariableName=...` returns CSV. This is the call the portal's map makes for its point layer (`_buildCSVLayerURL` in `main.*.js`).
- Variables: Crash Number, DateTime, Latitude, Longitude, Crash Severity, City, County-Borough, Manner of Collision, Lighting, Weather, Road Surface, Functional Class, Junction, First Harmful Event (+ animal), counts of pedestrians, pedalcycles, motorcycles, commercial vehicles, alcohol/drugs and speeding flags, fatal / serious / any-injury flags, CDS route number. **No street names, no person/vehicle records, no counts of people killed or injured.**
- Rows per year: 2021 7,924, 2022 7,924, 2023 9,284, 2024 9,209, 2025 8,647. Against the open 2023 table: 2021 7,924 vs 7,905; 2022 7,924 vs 7,877; 2023 9,284 vs 9,212 (portal "living repository": within 1%).
- Points: 42,542 of 42,988 (99.0%); 446 carry 0/0. None east of 180°.
- KABCO 2021-2025: K 319, A 1,103, B 6,063, C 5,290, O 30,205; "Died Prior to Crash" (8) read as O (not a crash injury).
- Boroughs: the portal writes Census names (matched to FIPS) plus "Unorganized Borough" and "Valdez-Cordova"; those get the smallest county box holding the point (a shortcut, noted in code).

### Checked, not used
- `AKDOT_GIS/Crash_2023Table` (2013-2023, 106,364 rows): commercial use allowed with attribution, but no crash id and no location (city/borough only).
- `MSB_Crash_Data` (Mat-Su, 2013-2022): "Data source is Alaska DOT. Provided to Michael Baker Intl": a consultant re-host, never a source. It shows the full DOT&PF export has Street, Intersecting_Street, Distance_from_Intersection, Route, Milepoint and injury counts.
- `Crash_App`, `Crash_Entry` (AKDOT_GIS): reference layers for crash entry, no crashes. `RH_CrashProcessors_Data`: internal server, unreachable.
- Anchorage: the Municipality publishes high-crash hotspots and corridors only (AMATS_HighCrashNetwork_Hosted); no crash points. The portal covers Anchorage (24,963 crashes).

## 2. Licence

- Portal notice, quoted: "This portal contains the best available data for the most recent five (5) complete years, and slight modifications should be expected over time. Although Alaska DOT&PF provides this portal, the Alaska Department of Motor Vehicles (DMV) is the official custodian of the data. ... The information in this report is compiled for highway safety planning purposes. Federal law prohibits its discovery or admissibility in litigation against state, tribal or local government that involves a location or locations mentioned in the collision data. 23 U.S.C. § 407; 23 U.S.C. § 148(h)(4); Walden v. DOT, 27 P.3d 297, 304-305 (Alaska 2001). ... DOT&PF does not endorse interpretations and conclusions drawn from this portal. By using this site, you acknowledge that you have read and agree to the above."
- No redistribution ban, no reuse grant. The portal hides its download button; the reader uses the map's own feed.
- Verdict: **unclear for paid use.** `active` on the WA/OR/AR footing; one-line flip to `reader_only`.

## 3. Placement

99.0% have a point; the 1% without one has no street names, so they stay unplaced. Street-name test: **not measured** (no names).

## 4. Reader and pack

- `backend/crashiq/sources/ak_dotpf.py`: one year per call pair, cached per year statewide (~9,000 rows); an empty year (outside the portal's five) is reported missing and not cached.
- `backend/crashiq/statepacks/ak.py`: `first_year` 2021, `final_lag_months` 10 (the portal held 2025 complete by Nov 2026), default window 2021-2025. Bounds stop at 180° (Near Islands left out; no crash there).
- `is_freeway` = functional class Interstate or Freeway/Expressway. Alaska's Interstate class includes town arterials (Parks Hwy in Wasilla, Sterling Hwy in Soldotna): an arterial study there loses those crashes (data note, as WA's SR 99).
- `data/reference/county_boxes_ak.json`: 30 boroughs/census areas, western-hemisphere part only (Aleutians West would otherwise span the state).
- Tests: `tests/test_source_ak.py` on `tests/fixtures/ak_dotpf_2024_sample.csv` (37 live rows, 9 KB).

## 5. End to end (port 8103, 2026-11-08)

East Tudor Road, Anchorage, Lake Otis Pkwy to Elmore Rd, 1.04 mi, 2021-2025: pulled 409, **counted 349**: K 1, A 6, B 58, C 48, O 236; excluded 60 (breakdown not recorded on this run; the earlier 2021-2024 run's 44 were 16 outside the buffer and 28 outside the study limits, no freeway). **Cost $60,488,000** (DOT&PF HSIP Handbook costs; checked by hand: 1×2,986,000 + 6×1,493,000 + 58×567,000 + 48×179,200 + 236×29,900). PDF 66,335 B, Excel 39,104 B, 9 findings.

## 6. Methods

See `ak-methods.md`: crash costs cited (HSIP Handbook 24th ed., App. A, PDF p. 39); statewide rates missing; minimum years unverified (worksheet input only).

## What we didn't check

The licence with DOT&PF/DMV; whether the portal's feed stays open; borough assignment near census-area lines; the alcohol/drug/speeding flags (not read yet).
