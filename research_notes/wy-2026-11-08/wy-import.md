# Wyoming: crash data for CrashIQ (Hermes, 2026-11-08)

Bucket **D (verified live 2026-11-08): gated.** No pack: notes, a "bring your export" column map, user actions.

## 1. Statewide: records request only
- WYDOT Highway Safety, Crash Data (https://dot.state.wy.us/home/dot_safety/crash-data.html): "If you would like to
  obtain crash data that is not available in the current publications or through the standard crash data reporting
  tool, you may submit a crash data request ... Please allow approximately 10 business days". Contacts: Kari Fictum,
  Highway Safety Records & Data Management Manager, (307) 777-4258.
- Public side: the Standard Crash Data counts report (statewide / district / county, 8 topics), the fatal-crash web app
  (webapp.dot.state.wy.us), and the annual Report on Traffic Crashes (2025 edition downloaded to
  `~/.hermes/state-manuals/wy/`, sha256 5420f271…2865). The data lives in WECRS (Wyoming Electronic Crash Reporting
  System), "a database containing all reportable crashes occurring in the state of Wyoming (with the exception of
  Yellowstone National Park and some Wind River Indian Reservation crashes)" (Report 2025, Background).
- WYDOT's own GIS server (https://gisservices.wyoroad.info/arcgis/rest/services, all 17 folders listed): ALRS, mileposts,
  roadway names, ITS/AADT, PIRS, roadkill, snow fence. **No crash layer.** (Roadkill_Reports is carcass pickups, not crashes.)
- ArcGIS Online by owner: `owner:wydot*` finds nothing; "WYDOT" / "Wyoming crashes" find student projects (UWyo), a
  Casper layer on a private IP (`http://10.130.99.51:6080/.../WYDOT_Crash_Data`, unreachable), and the Cheyenne layer below.

## 2. Cheyenne urban area: an open local layer (not built)
| | |
|---|---|
| Layer | `Cheyenne Wyoming Crash Data_updated` (item 5fe2f80b1ed5475f83388f705bca7b73), user Ge.Shi@fhueng.com in the **Cheyenne and Laramie County GIS Cooperative** org (CLCGISC, e5t4ywWgRBNUuDeU), public |
| URL | https://services1.arcgis.com/e5t4ywWgRBNUuDeU/arcgis/rest/services/Cheyenne_Wyoming_Crash_Data_updated/FeatureServer/0 |
| Rows | 8,440 (2020 1,636 · 2021 1,849 · 2022 1,614 · 2023 1,708 · 2024 1,633), Laramie County, Cheyenne 8,199 |
| GPS | LATITUDE/LONGITUDE on 100% |
| Streets | STREET_1 on all, STREET_2 on 30% (`COLLEGE DR \| WY 212` & `COLUMBIA DR \| CR 591`, `I 25 / US 87`) |
| Severity | KABCO as given: O 6,106 · C 745 · B 785 · A 166 · K 42 · U 596 |
| Also | yearly `20xx_All_Crashes` layers (2017-2021, 2024) for the City's "Urban Area 10 Year Total Crashes" map |
| Licence | none stated (no licenceInfo, no description) → **unclear** |

Not built: it covers one urban area (about 11% of Wyoming's people), it's a dashboard extract a consultant loaded for
the MPO, not a WYDOT release, and the brief says a gated state gets no pack. Its columns are the column map below.

## 3. "Bring your export" column map
WYDOT doesn't publish a crash data dictionary (searched 2026-11-08). The crash report form (Report 2025, Appendix,
"Wyoming Investigator's Traffic Crash Report Form", PDF p. 141) records: date, 24-h time, county, city, GPS latitude and
longitude, "Crash Occurred on: Highway/Street", "At Intersection with: Highway/Street", Highway LRS #, milepost,
# injured, # killed, and per-person injury K/A/B/C/O. The Cheyenne layer (a WECRS extract) names them:

| CrashIQ contract key | WECRS extract column (Cheyenne layer) | Rule |
|---|---|---|
| crash_id | CRASH_ID | text |
| date / year / hour | DATE (yyyy-mm-dd), YEAR, MIL_TIME (HHMM) | hour = MIL_TIME // 100 |
| lat / lon | LATITUDE / LONGITUDE | inside 40.99-45.01 N, 104.05-111.06 W |
| primary_road | STREET_1 | split `A \| B` aliases; keep the first |
| secondary_road | STREET_2 | same split; empty on segment crashes |
| county_fips | COUNTY (name) | Census name → 560xx |
| city | CITY | upper case |
| severity | KABCO (K/A/B/C/O/U) | as given; U = injury, level not reported |
| killed / injured | n_FAT / n_INJ | int |
| is_freeway | IS_INTERSTATE == "Interstate" | |
| collision_type | MANNER_OF_COLLISION, CRASH_TYPE, FIRST_HARMFUL | map to CCRS words |
| lighting / weather / surface | LIGHTING / WEATHER_1 / V1_RD_SURF | upper case |
| ped / bike / motorcycle / heavy_truck | INV_PEDESTRIAN / INV_CYCLIST / INV_MOTORCYCLE / INV_TRUCK | "Yes" |
| hit_run, alcohol, drugs, speeding | INV_HIT_RUN, INV_ALCOHOL, INV_DRUGS, IS_SPEEDING | |

Ask WYDOT for these columns (crash level, with person KABCO) when requesting.

## 4. Placement sample, end to end, methods
Not run: no record-level statewide data. (Cheyenne layer, read only for counts above.) No methods file: no pack.

## 5. User actions
1. Submit a WYDOT crash data request (https://dot.state.wy.us/home/dot_safety/crash-data.html, keep the form's drop-down
   as is): crash-level WECRS export with the columns in §3, for the counties and years needed, and ask whether a paid
   tool may load it and what notice to show.
2. Optional: ask the Cheyenne and Laramie County GIS Cooperative / Cheyenne MPO whether their crash layer may be used in a
   paid tool; if yes, a Laramie-County-only reader is about 150 lines (same shape as NM's).
3. Ask WYDOT Highway Safety for its per-level crash costs (none published).
