# Nevada: crash data for CrashIQ (gated, no pack)

Hermes, 2026-11-08. Every number below was measured live today unless marked. Brief: `~/.hermes/states-BRIEF2.md`.

## Verdict

**Bucket D (gated), verified.** The 2026-11-02 screen was right for Nevada. NDOT's statewide crash data comes only on
request. No statewide pack is built; this folder holds the notes, a "bring your export" column map
(`nv-column-map.json`) and a placement test of NDOT's location format on real Las Vegas rows.

## Sources checked

| Source | Access | Years | Location | Severity | Paid-use licence |
|---|---|---|---|---|---|
| NDOT Traffic Safety Engineering crash data (NCATSDW) | **Request only**: Survey123 form https://survey123.arcgis.com/share/2361c89935aa497183387106ec46e18d, or publicrecordsreq@dot.nv.gov | 2020-2024 offered | street + cross street + distance + direction, mile marker | KABCO (Crash Severity + Injury Type) | unclear: no grant; 23 U.S.C. 407 notice |
| NDOT open layer `gis.dot.nv.gov/arcgis/rest/services/TrafficSafety/CrashData_OpenData_2019_2023/FeatureServer` | **down**: `{"code":500,"message":"Service ... not started"}`; the TrafficSafety folder lists only `RSA_Network` | 2019-2023 (by name) | points (by name) | n/a | n/a |
| City of Las Vegas "CLV Traffic Crashes" https://services1.arcgis.com/F1v0ufATbBQScMtY/arcgis/rest/services/Traffic_Crashes/FeatureServer/0 | open, no login | **2015-2020 only** (2015 9,957; 2016 13,112; 2017 14,140; 2018 13,457; 2019 11,351; 2020 8,871; total 70,888). Item metadata says updated 2026-10-11, but the rows are the same as on 2026-11-02 | **no points**: rows carry ward polygons (AREA, WARD, SQ_MILES), not crash points; street pair 90% | KABCO via Crash_Seve + Injury_Typ | unclear: licence text is only "makes no warranty, representation or guarantee" |
| Consultant re-hosts of NDOT data on ArcGIS Online (Jacobs `NDOT_FY2024_Crashes_2019_2023`, PMX `NDOT_Crashes_2019to2023_Clean` 1,017 rows, `Washoe_Crashes_2019to2023_1020`, `Reno_Crash_Data_2020_to_2024`; UNLV ped/bike layers) | public URLs, but not NDOT's publication | 2019-2024 | points | as NDOT | **no**: request data shared by a third party, no grant. Not used |

NDOT's page (https://www.dot.nv.gov/safety/traffic-crash-data, read 2026-11-08; direct fetch returns 403, read through
an extractor): "The Crash Data Web Map is currently under construction and temporarily unavailable ... all available
NDOT crash data from 2020-2024. In the meantime, this data can be requested through the link below." And: "All crash
data listings, reports and dashboards are protected under 23 U.S.C. Section 407 ... All users shall comply with and be
subject to all applicable laws and regulations ... in connection with any receipt and use of NDOT crash data."

## The export's columns (published spec)

Nevada TRCC Data Dictionary (Jan 2021), section 2.1 "Crash Data Columns", pp. 4-6, saved at
`~/.hermes/state-manuals/nv/2021-01-NV-TRCC-Data-Dictionary.pdf` (sha256 prefix f6dcefc9d0444661). One row per crash
with vehicles 1 and 2 flattened onto it: Crash Severity, Crash Date/Year/Time, Primary Street, Distance, Dir, Secondary
Street, Mile Marker, Adj. Mile Marker, Weather, Fatalities, Injured, Property Damage Only, Injury Type (A/B/C), Crash
Type, Total Vehicles, V1_*/V2_* (type, direction, driver age, lane, action, driver factors, distraction, vehicle
factors, most harmful event, all events), First Harmful Event, Nonmotorist Factors, Factors Roadway, Lighting, HWY
Factors, Agency, Accident Rec Num. Severity codes (2.1.1, p. 7): K, A, B, C, O, U (unknown), N (not reported).
The Las Vegas feed uses exactly these columns, so it is a real sample of the layout. **No latitude/longitude** is in the
documented list; NDOT's own (stopped) open layer and the consultants' copies are point layers, so ask for X/Y with the
request. Full map to CrashIQ's keys: `nv-column-map.json`.

Example row (CLV, 2020): `Primary_St "NARROW CANYON ST", Distance "210.0", Dir "S", Secondary_ "ALEXANDER RD",
Crash_Seve "INJURY ACCIDENT", Injury_Typ "B", Agency "LVMPD"`. That is the California shape: a street, a cross street
and an offset.

## Placement sample, the California way

`placement_sample.py nv`, output `placement_sample.json`. 2,000 random City of Las Vegas 2020 crashes; TIGER/Line 2024
Clark County (32003) EDGES + FEATNAMES clipped to the Las Vegas box; `locate.place` with the reader's offset (Distance
+ Dir; "AT INT" = no offset).

- GPS in source: **0%** (no points), so **accuracy is not measured**.
- Street pair present: 90.1% (1,801). Ramp text in the primary street ("IR15N TO SR589 INT40") excluded: 199.
- Placed from names: **66.0%** of all crashes, 73.2% of those with a pair (unique_pair 624, exact 686, fuzzy 5,
  relaxed 3, near 1). Review: 482 (no intersection of the two names 438; streets meet more than once 44).
- Auto under the default `Gate()`: 0% (TIGER-only network, `tiger_only_auto` off: expected). With
  `Gate(tiger_only_auto=True)`: 65.5%.
- House addresses: not in the layout (not measured).

What breaks: NDOT runs route codes together with a direction (`IR15N`, `US95S`, `SR159`, `CC215S`; the sample rewrote
them as `I-15`, `US 95`, `NV 159`, `CC 215`), ramps are written `X TO Y INTnn` in either street field, and freeway
crashes name the freeway as both the road and the ramp. A Nevada upload reader has to split these; `names.py` needs no
change for the plain forms. The "no intersection" failures are mostly freeway/ramp pairs (`US95S & LAS VEGAS BLVD TO
US95S INT75`), which need the milepost or a ramp table, not a street pair.

## Methods (rates, costs)

Not collected. FHWA's 2025 Nevada HSIP report says NDOT's methods are in the "NDOT HSIP Manual"
(https://highways.dot.gov/sites/fhwa.dot.gov/files/2026-09/NEVADA_HSIP%20REPORT_2025_508.pdf); it was not downloaded
or read. No pack, so no `methods_nv.json`.

## What the user needs to do

1. Submit NDOT's Crash Data Request form (https://survey123.arcgis.com/share/2361c89935aa497183387106ec46e18d) for
   **statewide, 2020-2024**, digital format. Ask for: crash latitude/longitude (X/Y), the person table if there is one,
   and written permission to use the data inside a paid engineering tool. Or email publicrecordsreq@dot.nv.gov.
2. Ask NDOT when the Crash Data Web Map / `CrashData_OpenData_2019_2023` service returns, and under what licence. If it
   returns open, Nevada becomes a normal reader (re-run this check).
3. Send Engineering one delivered file (one county, one year is enough) to confirm `nv-column-map.json`.

## What we didn't check

The NDOT HSIP Manual (rates, crash costs); Reno/Washoe city feeds beyond the consultant copies; whether Clark County or
RTC Southern Nevada publish their own crash table (ArcGIS Online search found only RTC's HIN/top-25 summary layers, not
records); the licence of the UNLV research layers.
