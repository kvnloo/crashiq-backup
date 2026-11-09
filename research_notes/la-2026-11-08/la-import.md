# Louisiana: crash data for CrashIQ (gated, no pack)

Hermes, 2026-11-08. Every number below was measured live today unless marked. Brief: `~/.hermes/states-BRIEF2.md`.

## Verdict

**Bucket D (gated), verified.** The 2026-11-02 screen was right for Louisiana. LADOTD's statewide crash records (kept by
LSU CARTS) come only through an access grant from the DOTD Highway Safety Section. ArcGIS Online was searched by owner
(DOTD's orgs `PLiuXYMBpMK5h36e` and `LADOTDOpenData`, CARTS, the parish and city orgs): DOTD publishes no crash layer,
only road inventory, AADT and a polygon VRU screening layer. No statewide pack is built; this folder holds the notes,
a "bring your export" column map (`la-column-map.json`) and a placement test of DOTD's location format.

## Sources checked

| Source | Access | Years | Location | Severity | Paid-use licence |
|---|---|---|---|---|---|
| LADOTD crash database (CARTS; Louisiana Crash Tool, CAT-Scan), https://dotd.louisiana.gov/about/office-of-project-delivery/planning/highway-safety/safety-data-analysis | **Gated**: "Send Access requests to <DOTDCrashData@LA.gov>" (DOTD class *Introduction to Crash Analysis*, Oct 2025, slide 6); "Contact DOTD Highway Safety Section to gain access to our current crash data system" (Crash Data Analysis Guidelines, Sept 2025, p. 11) | statewide; a year stays preliminary until DOTD closes it, "typically ... eight months after the previous year's end" (Guidelines p. 11) | DOTD map-spots every crash (dotd_latit/dotd_longi), plus primary road, intersecting road, distance, unit, direction, LRS id + log mile | KABCO (older files A-E, see column map) | **unclear**: every DOTD crash product is marked "exempt from discovery or admission under 23 U.S.C. 407"; no reuse terms published |
| CARTS Crash Data Reports, https://carts.lsu.edu/datareports/ | open | current | aggregate dashboards | aggregate | n/a: not record-level |
| **City of New Orleans** "Traffic Incidents 2019_2024" (the layer behind the city's public Traffic Safety Dashboard), https://services.arcgis.com/VhMjCzR3cIjEkh7L/arcgis/rest/services/Traffic_Incidents_2019_2024/FeatureServer/0 | open, no login | 2019 19,468; 2020 14,386; 2021 17,755; 2022 16,089; 2023 15,510; 2024 17,285 (100,493, Orleans only) | point geometry; **no street names** | KABCO ("100-(K) FATAL INJURY" ... "104-(O) PROPERTY DAMAGE ONLY": K 340, A 2,050, B 8,038, C 22,627, O 67,438) | unclear: "provided for general informational purposes only and are not intended for use as a legally authoritative source" |
| **Baton Rouge** Traffic Crash Incidents, https://data.brla.gov/Public-Safety/Baton-Rouge-Traffic-Crash-Incidents/7wah-qncc (updated 2026-11-08) | open | 2022 5,310 (from mid-year); 2023 14,758; 2024 15,350; 2025 15,581; 2026 13,387 so far | latitude/longitude, street_name, first_street_highway (shares not measured) | **no KABCO**: has_injury / has_fatality flags only | **ok**: Public Domain |
| Consultants' copies of the DOTD file: Toole Design `new_orleans_crashes` 2015-2019 (103,178 rows), Westwood/CSRS `DOTD_crash_data` (17,785 rows, one study area) | open, but not DOTD's | 2015-2019 | DOTD points + names | A-E | **no**: third-party copies of a 23 U.S.C. 407 file, no permission shown. Used here **only to measure the format** |

City feeds fill gaps under a state source (brief 2026-11-08); with no open state source they don't make a pack.

## The export's columns

DOTD publishes no column list. The consultants' copies show the field names (shapefile-truncated): crash_num,
crash_date, crash_time, pri_road_n, inter_road, pri_dist, pri_measur (FT/MI), pri_dir, severity_c, num_tot_ki,
num_tot_in, man_coll_c, lighting_c, dotd_latit, dotd_longi, parish_cd, hwy_type_c, pri_hwy_nu, lrs_id, lrs_logmil.
Map: `la-column-map.json` (`verified_against_real_export: false`).

Severity: files to about 2020 code severity_c **A-E** (Orleans 2015-2019: A 222, B 1,119, C 7,191, D 24,623,
E 70,022). The 2023 Guidelines say the injury SPF uses crashes "where Severity is not "E" (Property Damage Only)"
(p. 5); LTRC FR 721 (2026) names the five levels Fatal, Severe, Moderate, Complaint, No Injury. So A->K, B->A, C->B,
D->C, E->O. The 2025 Guidelines switch to KABCO letters ("is not "O"", p. 5), so a new export may already be KABCO.
Check before reading.

Distance unit matters: of 7,811 Orleans 2019 crashes with a distance, 6,207 are in FT, **1,424 in MI** and 180 blank.

## Placement sample, the California way

`placement_sample.py la <scratch>`, output `placement_sample.json`. 2,000 random Orleans Parish 2019 crashes from
the Toole Design copy (DOTD layout); DOTD's point hidden; placed from r_pri_road + inter_road, offset by pri_dist (MI
converted to feet) toward pri_dir, on TIGER/Line 2024 Orleans (22071) EDGES + FEATNAMES; scored against the hidden point.

- DOTD point present: 98.5%. Street pair: 96.1%.
- Placed from names: **76.0%** of all crashes (79.1% of pairs): exact 1,336,
  unique_pair 118, relaxed 27, near 18, verified_typo 12, fuzzy 9. Review: 402 (no intersection of the two names 328,
  streets meet more than once 68). No cross street: 78.
- Auto under the default `Gate()`: 0% (TIGER-only network, expected). With `Gate(tiger_only_auto=True)`: 72.7%.
- Within 250 ft of DOTD's point: **85.6%** of placed (Wilson low 83.8%), n = 1,516;
  offset 250 ft or less: 88.7% (low 86.9%, n = 1,428).
- What breaks: freeway exits and ramps as a cross street ("I-10 & SLIDELL EXIT", "RAMP & GENERAL DE GAULLE DR",
  "HOV & ELYSIAN FIELDS EXIT"), the I-10 service road ("I-10 SRVRD", "I 10 SERVICE RD"), and the Crescent City
  Connection ("CCC INBOUND"). A reader would map SRVRD to the service road and drop ramp rows to review; no shared
  change needed for the sample.
- House addresses: the DOTD layout has no house-number field; not measured.

## Methods (rates, costs)

DOTD's own crash costs (Crash Data Analysis Guidelines, Sept 2025, Appendix-A, p. 19, "2023 Cost"): K $2,133,496;
A $239,929; B $92,154; C $68,698; O $35,793. DOTD compares sites with its SPFs and the number-rate (Guidelines
pp. 5, 7). No pack, so no `methods_la.json`; these go into it when a pack is built. Manuals saved in
`~/.hermes/state-manuals/la/`.

## What the user needs to do

1. Email **DOTDCrashData@LA.gov** for Louisiana Crash Tool access, or a statewide crash / vehicle / person extract,
   2020-2024, CSV, with dotd_latit/dotd_longi, primary road, intersecting road, distance, unit and direction.
2. Ask DOTD in writing whether the extract may be used inside a paid tool (the 23 U.S.C. 407 marking).
3. Send Engineering one extract (one parish, one year) with its data dictionary to confirm `la-column-map.json`
   and build the upload reader.
4. Optional later: New Orleans (KABCO, points, no names) and Baton Rouge (Public Domain, no KABCO) as city sources
   once there is a state source to sit under.

## What we didn't check

The GPS share of Baton Rouge's rows; Lafayette, Shreveport and Jefferson Parish open data (ArcGIS Online search found
only consultant and student layers); DOTD's public-records route (https://dotd.la.gov public records page) as an
alternative to the Highway Safety Section; whether the LCT export has the same columns as the consultants' copies.
