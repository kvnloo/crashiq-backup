# Delaware: DSHS Public Crash Data, statewide (2026-11-08)

Written by Hermes. Every number measured on 2026-11-08 from the URLs named here.

## 1. Source

- **Public Crash Data**, Delaware Department of Safety and Homeland Security (DSHS), data.delaware.gov Socrata
  `827n-m6xc` (https://data.delaware.gov/Transportation/Public-Crash-Data/827n-m6xc), mirrored on FirstMap
  (https://enterprise.firstmap.delaware.gov/arcgis/rest/services/Transportation/DE_Public_Crash_Data/FeatureServer/0).
  No login. Updated monthly (5th), "crashes that occurred since 2009 through six months ago". Latest crash
  2026-05-01 (UTC).
- One table, one row per crash, 43 columns: `crash_datetime` (UTC: FirstMap's `CRASH_TIME` 1155 is `16:55Z` on
  2024-02-01, so the reader converts to America/New_York), `crash_class`, `impact`, `light_cond`, `weather_1`,
  `road_surface`, pedestrian/bicycle/motorcycle/alcohol/drug/seatbelt/work-zone flags, `pri_contrib_circum`,
  `latitude/longitude`, `county` (K/N/S), `year`.
- **No** street names, route/milepost, road class, report number, or person/vehicle tables. The reader uses the
  portal row id (`:id`) as `crash_id`; whether it survives the monthly refresh was not checked.
- The 2026-11-02 screen was right (bucket A except KABCO).

## 2. Licence
The portal's licence field is empty. The description (DSHS) says: "The data contained on FirstMap and the Open Data
Portal represents the best available information at DSHS and is not an official record of what transpired in a
particular crash or for a particular crash type and does not contain personal information. This data is generated
from crash reports and allows any member of the public to engage in interactive analysis and data exploration for the
purpose of identifying, evaluating or planning the safety enhancement of potential crash sites…" Verdict for a paid
product: **unclear**: ask DSHS in writing.

## 3. Rows and severity (SoQL `$group=year,crash_class_desc`)

| Year | Rows | Fatality | Personal injury | PDO | Non-reportable |
|---|---|---|---|---|---|
| 2009 | 19,115 | 101 | 5,029 | 13,789 | 196 |
| 2010 | 31,272 | 91 | 5,154 | 13,736 | 12,291 |
| 2011 | 31,066 | 85 | 5,103 | 14,397 | 11,481 |
| 2012 | 31,232 | 97 | 5,177 | 14,706 | 11,252 |
| 2013 | 32,450 | 90 | 5,248 | 15,957 | 11,155 |
| 2014 | 32,739 | 105 | 5,129 | 17,690 | 9,815 |
| 2015 | 35,015 | 125 | 5,463 | 18,495 | 10,932 |
| 2016 | 36,955 | 109 | 5,752 | 20,594 | 10,500 |
| 2017 | 37,145 | 103 | 5,653 | 22,311 | 9,078 |
| 2018 | 37,496 | 94 | 5,516 | 23,245 | 8,640 |
| 2019 | 37,441 | 110 | 5,770 | 23,237 | 8,318 |
| 2020 | 31,665 | 103 | 4,986 | 19,084 | 7,492 |
| 2021 | 37,766 | 126 | 5,585 | 22,762 | 9,293 |
| 2022 | 37,445 | 134 | 5,405 | 22,264 | 9,642 |
| 2023 | 37,270 | 130 | 5,181 | 22,153 | 9,806 |
| 2024 | 37,184 | 127 | 5,075 | 22,388 | 9,594 |
| 2025 | 36,868 | 99 | 4,942 | 22,540 | 9,287 |
| 2026 | 11,095 | 22 | 1,364 | 6,742 | 2,967 |

GPS: 591,221 of 591,222 rows have latitude; 2 points fall outside Delaware's box. 3 rows have no year, 7 have
crash class `NA` (left out).

Severity map: 04 Fatality → K, 03 Personal Injury → U (no A/B/C published), 02 PDO → O. **01 Non-Reportable is left
out**: per DSHS's own column note it is "all collisions on private property" plus trafficway PDO under the $2,000
duty-to-report threshold (21 Del. C. § 4203), and DelDOT's HSIP (its HRRR intersection rule) counts "fatal, personal injury, and/or property damage
only crashes" (DelDOT HSIP presentation, 2024, PDF p. 18). The pull log counts them (`non_reportable_left_out`).

## 4. Placement sample (`placement_sample.py`, `placement_sample.json`)

New Castle County 2025: 20,607 rows, 15,753 reportable, **15,753 with a plausible point
(100%)**, all inside the county box; 15,456 distinct points (564 crashes share a point).
There are no street names or addresses, so the California-way locator test doesn't apply (name_placed: n/a).

## 5. End to end (port 8103, 2026-11-08)

Kirkwood Highway (DE 2), Prices Corner, New Castle County: 0.91 mi, 5 study intersections, 2021-2025. Pulled 1,327
source rows (282 non-reportable left out), 1,045 read, 0 contract errors, kept 778, **counted 470**:
K 0 / U 57 / O 413. No crash cost (DelDOT has none published). 6 findings shown, 2 rejected
("number 2 in the text is not backed by a cited table cell"). PDF 49,487 bytes, Excel 38,897 bytes.
(A first try with a straight 2-point line counted only 55: Kirkwood Hwy curves ~150 m off the chord, so the line
was redrawn from OSM's geometry.)

## 6. Wiring
Plug-in only: `statepacks/de.py` → `sources/de_dshs.fetch_contract`. No shared file changed, no shared fix needed.
Possible later: map `pri_contrib_circum` "Driving under the influence"/"Speeding" and `alcohol_involved` to T14
(the T14 rows read California Vehicle Code sections today).

## 7. Not checked
FHWA's HSIP 2025 PDF (Access Denied to scripts; read via a search extract only), row-id stability across refreshes,
Wilmington city data, AADT.
