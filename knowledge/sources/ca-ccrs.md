# California: CCRS (California Crash Reporting System), CHP

**Where:** data.ca.gov, CKAN package `ccrs`. Tables per year: `Crashes_YYYY`, `Parties_YYYY`,
`InjuredWitnessPassengers_YYYY`, 2016 to the current year (current year partial). Queryable with
`datastore_search_sql` (SQL over the API, no login). Resource ids change when CHP republishes: resolve them
at runtime with `package_show` (code: `backend/crashiq/sources/ca_ccrs.py`).
**Licence:** "Other (Public Domain)", CHP. Commercial use OK.
**Replaces:** SWITRS raw files for new years.

## Location fields
`Latitude`, `Longitude`, `PrimaryRoad`, `SecondaryRoad`, `SecondaryDistance`, `SecondaryDirection` (N/S/E/W),
`SecondaryUnitOfMeasure` (F feet, M miles), `IsFreeway`, `NCIC Code` (reporting agency), `Report Number`.

## Quirks (with evidence)
- **GPS coverage depends on the agency, not the city.** 2024: statewide 78% have lat/long; SF 35%, Sacramento 33%,
  LA City 56%, Long Beach 97%, unincorporated (CHP) ~100%. (spike, 2026-10-15)
- **In San Francisco, crashes with GPS are almost all CHP freeway crashes.** SFPD (NCIC 3801) files ~4,100/yr with
  ~1% GPS; CHP files ~2,000/yr, 100% GPS, ~95% `IsFreeway`. So "hide the GPS on crashes that have it" does NOT test
  city-street placement in SF: wrong population. (2026-10-18)
- **Report numbers are not unique.** SFPD 2023–24: 9 blank, several repeated up to 4× with different streets.
  Never join on a non-unique report number. (2026-10-18)
- **Feet typed as miles.** Unit `M` with values like 33, 73, 233 "miles" inside a city. Rule: unit M and value > 2
  → treat as feet, flag `offset_fixed`. (3 of 5,309 SF crashes) (2026-10-18)
- **CCRS drops offsets that the agency's own record has.** In ~10% of SFPD injury crashes (261 of 2,654) DataSF
  has a distance from the intersection and CCRS doesn't. Caps how precisely CCRS alone can place a crash.
- **Officer street-name writing** (all real, SF): suffix variants (`ALEMANY BL`), zero-padded ordinals (`07TH ST`
  in DataSF), typos (`MISSINO`, `VALENICA`, `BUST ST`, `CAN NESS`), route numbers (`RT 101`, `I-280 S/B`), house
  addresses in the cross-street field (`GENEVA AV 1677`, `975 3RD ST`), landmarks (`MARX MEADOWS`, `GIANTS DR`),
  wrong suffix (`GEARY ST` where it's Geary Blvd), streets that don't meet (`15TH AV & MISSION ST`).
- **GPS format errors (2026-10-23, #247):** degrees-minutes-seconds written as decimal in many agencies, not only
  San Jose (4,111 difficult crashes, mostly CHP areas 9370, 9675, 9252, 9550, 9530); longitude missing its minus
  (432); 1,676 raw points outside California. Whole-degree latitude errors exist but can't be told from chance.
- **Default / dispatch GPS points** (1,755 crashes on 50 points) and coarse coordinates (≤ 2 decimals, 547). (#218)
- **The live Crashes table has 74 data columns** (our mirror keeps 30; 75 with the datastore `_id`), Parties 48. Check the live schema, not a
  local copy, before saying a field doesn't exist (a wrong "no postmile" claim stood for a day, 2026-10-23).
- **Milepost fields exist but are rarely filled:** `MilepostMarker`, `MilepostDistance`, `MilepostDirection`,
  `MilepostUnitOfMeasure`. CHP filled them with a real Caltrans postmile ("route county postmile", e.g. `80 SAC M7.128`, plus distance and
  direction from it) on 3.7% of 2021 and 2.3% of 2022 freeway crashes, and essentially never from 2023 (it switched to
  `IsLocationReferToNarrative`). City PDs use the field for a reference line ("W CURBLINE OF MARINA BLVD"), not a
  postmile. D1: 830 of 24,076 have one. (Tester, live data, 2026-10-23)
- Other fields the mirror drops: `Beat`, `IsHighwayRelated`, `IsCountyRoad`, `IsLocationReferToNarrative`,
  `SketchDesc`; Parties: `Lane`, `ThruLanes`, `SpeedLimit`, `StreetOrHighwayName`, vehicle make/model/year.
- `IsFreeway` = freeway jurisdiction, including ramps and connectors. Freeway crashes: `methods/freeway-crashes.md`.
- **Parties_2025** was downloadable but not loaded in the datastore (`datastore_active = false`) from ~2026-09-30;
  fallback = the file (docs/03, 2026-10-22).
- Most recent ~12 months may be preliminary (`Is Preliminary`).
- To check: LA City 2024 total (28.8k) looked low vs. historic SWITRS. (open, F2)

## Cleaning rules in code
`ca_ccrs._normalize`: unit conversion + feet-as-miles fix, trimmed strings, report number as string.
Street names: `backend/crashiq/names.py` (see `methods/geocoding.md`).
