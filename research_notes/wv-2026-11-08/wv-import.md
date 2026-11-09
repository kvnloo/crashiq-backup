# West Virginia crash data: gated (bucket D), verified 2026-11-08

**Verdict:** no pack. WVDOT's crash database (ReportBeam electronic reports) comes only by email request. No agency layer or download exists.

## Checked live on 2026-11-08
| Where | Result |
|---|---|
| https://transportation.wv.gov/traffic-accident-data | "To obtain traffic accident data, please contact Marsha Mays … Marsha.K.Mays@wv.gov". |
| WV GHSP Highway Safety Plan FY2027-2029 (saved `~/.hermes/state-manuals/wv/`, sha256 c0363b1f…) | "ReportBeam Crash data, housed in the West Virginia DOT Crash Database (reported by law enforcement agencies)". |
| WVDOT's ArcGIS Online org (`WVDOT_Publisher`, services2.arcgis.com/xLpB90lOmCXYDAWo, 326 services; it hosts the WVDOT Open Data Portal) | `orgid:… crash` and `orgid:… accident` find 0 items. The `safety` items are signs and guardrails, plus CamSys aggregates: `WV_SafetyData_2021` (220 rows of county 5-year averages) and `WV_SafetyCountiesDistricts_2020` (55 county polygons with yearly fatal and serious counts). No crash points. |
| WVDOT ArcGIS server https://gis.transportation.wv.gov/arcgis/rest/services | 112 services, no crash layer. It has `Roads_And_Highways/Publication_LRS` (route + milepost) and `Projects/AADT`. |
| ArcGIS Online `crash "West Virginia"`, `crashes WV`, `crash WVDOT` | Only consultant and university re-hosts: Burgess & Niple (`WV_Pedestrian_Crashes_2019_2023`, `WV_Bicycle_Crashes_2019_2023`, for the WV VRU Systemic Analysis) and Marshall University (CMV crashes 2017-2021). These aren't agency publications and have no grant, so they're not a source. |

## The export's layout (from a consultant copy, not a source)
`WV_Pedestrian_Crashes_2019_2023` has 297 crashes: 108 fatal, 189 serious, pedestrian only. Its item text says "downloaded 8/1/2025". The columns are MMUCC-coded:
- `C___Crash_Record_Number` (R201900191), `C01` date, `C02` time
- `C03` severity
- `C05` sign system (Interstate 15, US 111, WV 112, County/HARP 59)
- `C06` location name ("Kanawha WV 061/00")
- `C08` county-based route ID, `C09` milepost
- `C14`-`C19` manner of collision, light, surface, first harmful event
- `C26` agency type
- `C___Latitude`/`Longitude`: 288 of 297 = **97.0%** have them

It has no street names. The route ID decodes as CC S RRRR SS PP: `20300610000` = Kanawha (20), WV (3), route 0061.

## Bring-your-export column map
`wv-column-map.json`. It's built from the WV Uniform Traffic Crash Report (DMV-17-F, ReportBeam sample) and the layout above. It hasn't been checked against a real WVDOT export.

## Methods
- Severity is KABCO on the form (K, A, B, C person classes).
- Crash costs, base rates, critical rate: `missing`. The WV HSIP 2024 report on highways.dot.gov 403s scripted downloads, and web_extract returned only its first pages. No WVDOT safety-study manual was found online.

## Placement
Not measured. There's no open record set. The consultant copy has GPS on 97%, but it covers fatal and serious pedestrian crashes only, so it can't stand for all crashes. Without GPS, `Publication_LRS` route + milepost would place on-system crashes (bucket C method).

## User actions
1. Email Marsha.K.Mays@wv.gov for a 2021-2025 statewide crash extract: crash, vehicle and person tables, the data dictionary, lat/lon, the county-based route ID + milepost, and street names, as CSV.
2. In the same email, ask whether a paid tool may use it, and whether WVDOT will publish an open crash layer.
3. Send one delivered file (one county, one year is enough).

## Not checked
- WVDOT HSIP/safety manuals (costs, rates).
- City feeds: none found for Charleston, Huntington or Morgantown.
- Whether the export carries street names for city streets.
