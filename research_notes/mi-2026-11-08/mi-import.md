# Michigan crash data: import notes (Hermes, 2026-11-08)

Bucket **D (gated for a paid product)**, verified live. The 2026-11-02 screen's D stands, but for a different reason
than "aggregate only": the statewide record-level data *is* reachable without login, but its terms forbid commercial
use and scraping. **No pack.** Notes, a "bring your export" column map and user actions only.

## Sources

1. **Michigan Traffic Crash Facts (MTCF) Data Query Tool** (MSP OHSP + UMTRI),
   https://www.michigantrafficcrashfacts.org/data/querytool. Public, no login. Years 2004-2025 (`tn=[2004,2025]` in
   the app; the front page says 2024 is live; the converter page has `MAX_YEAR = 2025`).
   - Record-level: the *List* output pages 90 rows at a time (`POST /qjson`, `v=list`). It gives crash-level columns,
     including **Crash Latitude / Crash Longitude**, Worst Injury in Crash (KABCO from the UD-10), crash
     month/day/year, time, county, city/township, highway class/number, control section, crash type, light, weather,
     surface, traffic control and flags (ped, bike, motorcycle, truck, deer, hit-and-run …). 72 columns are listed by
     `POST /qjson/group/list/0` (saved below as the column map).
   - Count, measured with `GET /qjson?q=1;0;2024;;`: **288,880 crashes in 2024, entire state.**
   - UD-10 report PDFs: Cloudflare Turnstile plus a per-session limit.
   - **Terms of Use** (`/page/json/terms`, quoted): *"MTCF grants permission to copy and distribute publications and
     query output for **noncommercial and non-profit use**, as long as the content remains unaltered and credit is
     given to MTCF. … there are limits placed on the amount of raw data … that can be downloaded directly from this
     site. **Attempts to circumvent these limits, including scraping data and repeated downloads, can lead to being
     restricted** from the future use of Michigan crash data. Bulk downloads should be requested via the Contact
     information."*
   - Verdict: **licence_paid_use = no.** A reader that pages the List output would be scraping, so none was built.
     I made one test List call; it returned `{"err":0}` with no rows (the app's session state is probably needed), and
     I didn't push further.
2. **MSP Traffic Crash Reporting Unit**: bulk data by request, CrashTCRS@michigan.gov, 517-241-1699
   (https://www.michigan.gov/msp/divisions/cjic/traffic-crash-reporting-unit/annual-reports-and-statistics). It's a
   records request, so gated.
3. **Mi-CAT** (Michigan Traffic Crash Analysis Tool): *"free to access for law enforcement agencies and approved
   traffic safety partners"*, by application. Gated. The public Michigan Traffic Crash Dashboard is aggregate only.
4. **SEMCOG "Crash Locations, 2016-2025"** (regional, SE Michigan's 7 counties),
   https://services1.arcgis.com/xUx8EjNc6egUPYWh/arcgis/rest/services/crash2025_10year/FeatureServer/0. Open
   ArcGIS layer.
   - Rows: 2016 145,510; 2017 145,427; 2018 144,104; 2019 141,390; 2020 105,485; 2021 124,631; 2022 128,821;
     2023 131,448; 2024 129,853; 2025 128,144.
   - 2024 is **45% of the state's 288,880.**
   - Fields include CRASHID_UD10, DATE_FULL, KCOUNT/ACOUNT/BCOUNT/CCOUNT (KABCO), MAINROAD, INTERROAD, XCORD/YCORD,
     PR/MP (MDOT physical-reference route and milepoint), PEDESTRIAN, BICYCLE, MOTORCYCLE, WEATHER, LIGHTING,
     SURFACE, NFC, AADTR.
   - Licence: the SEMCOG Copyright License Agreement
     (https://maps-semcog.opendata.arcgis.com/pages/copyright-license-agreement). It grants a *"perpetual,
     non-exclusive, royalty-free license to use, reproduce, modify, distribute, publish …"*, with the notice
     *"Copyright © <year> SEMCOG. All Rights Reserved."*. But §1(b) grants no third-party rights, and the crash
     records are MSP's.
   - Verdict: ok_with_attribution for SEMCOG's work, **unclear** for MSP's underlying records.
   - Not built: the user's rule is statewide, with regional or city feeds only filling gaps, and here there is no
     statewide base to fill.
5. City: **Detroit "Traffic Crashes"** (City of Detroit ArcGIS,
   https://services2.arcgis.com/qvkbeam7Wirps6zC/arcgis/rest/services/Traffic_Crashes/FeatureServer). Seen in an
   ArcGIS search, not measured.
6. MDOT GIS Open Data (moving to data.michigan.gov, Dec 2026). It has **no statewide crash layer**; only
   "Non-Motorized Crashes 2011-2021" (MDOT_GIS) turned up.

## Placement
Not measured: there's no open statewide record set to sample without breaking MTCF's terms. MTCF's List output has
lat/lon per crash and SEMCOG has XCORD/YCORD on every row. Michigan's UD-10 locations are geocoded to the Michigan
Geographic Framework by MSP (MSP/MDOT, GIS Users Meeting Aug 2014 minutes).

## Bring-your-export column map
`mi-column-map.json`. It maps an **MTCF List CSV export** (the column titles the tool exports) and an **MSP bulk/SEMCOG
extract** onto the CrashIQ crash contract. The spec is the MTCF list variable catalogue (`/qjson/group/list/0`,
72 columns, 2026-11-08) and the SEMCOG layer's field list. A reader can be built once the user has a real export.

## What the user must do
- Email MSP's Traffic Crash Reporting Unit (CrashTCRS@michigan.gov) to ask for a **bulk statewide crash extract
  (crash + unit + person, 2021-2025) and the terms for use in a paid product**. Ask for the TCRS/UD-10 field
  dictionary with it.
- Or, as a stopgap: decide whether a **SE-Michigan-only pack from SEMCOG** is acceptable (45% of the state's
  crashes; licence unclear for MSP's records). Ask SEMCOG whether its licence covers commercial redistribution.
- Optionally email UMTRI/MTCF (the Contact page) for commercial permission for the query tool's List exports.

## Not checked
- MDOT crash costs and rates (no pack, so not researched).
- Detroit's city feed.
- MTCF List output columns as exported (the call returned no rows).
