# Maryland: statewide crash data for CrashIQ (Hermes, 2026-11-08)

**Bucket D (bring your export)**, corrected from the 2026-11-02 screen's A. **No pack built.**

## What changed since the screen
- The statewide open copy, "Maryland Statewide Vehicle Crashes" on opendata.maryland.gov (crash `65du-s3qu`, person
  `py4c-dicf`, vehicle `mhft-5t5y`), now answers every API call with
  `"You must be logged in to access this resource"` (2026-11-08). The catalog search for "crash" on the domain lists
  only the story `ggbs-m2rv` ("Maryland Crash Data Resources") and a 2022 mapping example. The screen had already
  noted the copy froze in May 2023.

## The statewide source today: MSP's public dashboards (no login, no API)
- 2019-2023: <https://analytics.mdsp.org/t/Public/views/PublicCrashData/DownloadCrashData>
- 2024-present (ACRS 2.0): <https://analytics.mdsp.org/t/Public/views/PublicCrash2/PublicCrash>
- Tableau Server, guest session (`is_guest: true`, `allow_export_data: true`, `allow_view_underlying: true`).
- The full export is manual: pick dates, click the map, Download > Data, then per tab (Reports, Contributing
  Circumstances, Occupants, NonMotorists, Vehicles) Show Fields > (All) > Download. Files are UTF-16 tab-separated.
- Scripted sheet exports work but carry only what the sheet shows:
  - `PublicCrashData/CrashMap.csv`: 110,474 rows, one per report number, columns `Reportnumber, CircumstancesCode,
    DriverID, NonMotoristID, PassengerID, Vehicleid, CrashPoint, Latitude (generated), Longitude (generated)`;
    all 110,474 have a point. No date, severity or road, so not a usable crash table.
  - `PublicCrash2/PublicCrash.csv`: a county-by-severity summary (3.9 KB).
- The full "underlying data" call (vizql `get-view-data-dialog-tab-pres-model`) refused a scripted session
  ("Invalid data table ID"). Scraping a dashboard's session protocol is fragile and its terms are unknown, so no
  reader was built on it.
- Licence: none found on the dashboards.

## Column map (partial, for the export reader)
Known from a third-party analysis of these exports (Capital News Service R script, read 2026-11-08) and the sheet CSVs.
Not verified against a real export; the reader waits for one.

| CrashIQ key | MSP export column (tab) |
|---|---|
| crash_id | `Reportnumber` (Reports; also `ReportNumber Occ`, `ReportNumber NM`, `ReportNumber Veh` on the other tabs) |
| date | `Crashdate` (Reports) |
| lat / lon | `Latitude (generated)` / `Longitude (generated)` (CrashMap sheet) |
| county | `Crash County Description` |
| severity (crash) | `Crash Severity Description` ("Fatal Crashes", ...) |
| person KABCO | `InjuryStatus Occ` (Occupants), `InjuryStatus NM` (NonMotorists); code `01` = fatal in the script |
| ped / bike | NonMotorists tab rows |
| heavy truck / motorcycle | `BodyType Veh Description` (Vehicles) |
| contributing factors | `Contribs Description`, `Contribs Type` (Contributing Circumstances) |
| primary / secondary road | not known: needs a real Reports export |

## Other Maryland sources (not statewide)
- Montgomery County open ACRS feed, **Public Domain**: Incidents `bhju-22kf`, Drivers `mmzv-x632`, Non-Motorists
  `n7fk-dce5` (data.montgomerycountymd.gov), updated 2026-11-05. Incidents have `road_name`, `cross_street_name`,
  `latitude`, `longitude`; drivers and non-motorists have `injury_severity`. Crashes per year:
  2015: 11,470, 2016: 12,103, 2017: 12,104, 2018: 11,869, 2019: 11,665, 2020: 8,070, 2021: 9,353, 2022: 10,056, 2023: 10,776, 2024: 10,629, 2025: 10,312, 2026_to_2026-11-05: 8,533. About a tenth of Maryland's crashes.
- MDOT SHA Fatal Crash Locations (Public), fatal only on SHA roads, 269 rows, no street names.

## Placement sample, end to end
Not measured: no statewide file with road names could be downloaded without a manual export.

## What the user must do
1. Export one county-year from https://analytics.mdsp.org/t/Public/views/PublicCrash2/PublicCrash (e.g. Baltimore City, 1/1/2024-12/31/2024): click the map once, Download > Data, then for each tab (Reports, Contributing Circumstances, Occupants, NonMotorists, Vehicles) Show Fields > (All) > Download. Put the five files in ~/.hermes/cache/scratch/states/md/export/. A reader is built against them.
2. Ask MSP (Central Records / the dashboard owner) or MDOT SHA Office of Traffic & Safety whether Maryland's statewide crash data is available as a bulk file or API, and whether a paid tool may use it
3. Decide: should Montgomery County's open, public-domain ACRS feed (road + cross street + GPS, ~10k crashes a year) be offered as a Maryland county pack until the statewide data is reachable?

## Not checked
- MSP terms of use beyond the dashboard pages; MDOT SHA's own crash files (the SHA crash layers found on ArcGIS Online
  point to internal `*.mdot.mdstate` servers).
- Maryland's crash costs and rates (no pack, so no methods file).
