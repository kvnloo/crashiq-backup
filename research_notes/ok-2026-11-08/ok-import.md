# Oklahoma: crash data for CrashIQ (gated, no pack)

Hermes, 2026-11-08. Every number below was measured live today unless marked. Brief: `~/.hermes/states-BRIEF2.md`.

## Verdict

**Bucket D (gated), verified.** The 2026-11-02 screen was right for Oklahoma's full crash file, but missed the open
partial layers. ArcGIS Online was searched by owner: ODOT (`OKDOT_GIS`, org `RBtoEUQ2lmN0K3GY`, 1,163 items) and
DPS/OHSO (org `1RKb5IC5HFxsUYMS`, 502 items). What is open statewide is **fatal, serious and minor-injury crashes
only, 2019-2021** (OHSO's KAB layers): no possible-injury or property-damage crashes, and nothing after 2021. That
can't support a corridor study (no crash rate, most crashes missing), so no pack is built. Every crash, every year,
is in ODOT's SAFE-T, which needs a personal account and bars private projects. This folder holds the notes, a "bring
your export" column map (`ok-column-map.json`) and a placement test on OHSO's open rows.

## Sources checked

| Source | Access | Years | Location | Severity | Paid-use licence |
|---|---|---|---|---|---|
| ODOT **SAFE-T**, https://www.oksafe-t.org/ (login page; contact ODOT-CollisionData@odot.org) | **Gated**: "Accounts belong to persons ... Eligibility is conditional on your employment"; "Private sector employees (only) are required to sign a Permit" (ODOT SAFE-T Training, Aug 2018, p. 5) | "all reported traffic accidents on public roads in OK since 1998" (p. 2) | Latitude/Longitude (Derived); "Not all crashes found are mappable" (p. 102); on street / at street; highway + control section + milepoint | 5/K ... 1/O (p. 18) | **no**: "Collision data may only be queried, distributed, or used as required by government agencies for transportation safety related activities. It may not be used for private projects" (p. 5); exports carry the 23 U.S.C. 409 restriction |
| **OCERS** (Oklahoma Collision Electronic Records System, DPS/OHSO), linked from https://oklahoma.gov/highwaysafety.html | **Gated** (agency login; single reports by request) | official record since its rollout (about 2023; FMCSA FY25 Oklahoma CVSP says rollout to all agencies is still under way) | Latitude/Longitude, street, intersecting street (seen in OHSO's SORTPO copy) | KABCO words | unclear |
| **OHSO KAB layers** `kab_crashes_2019`, `2020_kab_crashes`, `2021_kab_crashes`, https://services2.arcgis.com/1RKb5IC5HFxsUYMS/arcgis/rest/services/2021_kab_crashes/FeatureServer/0 | open, no login | 2019 9,763; 2020 8,609; 2021 9,360 | LATITIDE/LONGITUDE (100% of the Tulsa County 2021 sample); STREET_HIGHWAY + NEAREST_INTERSECTING_ROAD (79.5% have both) | **K/A/B only**: 2021 Fatal 681, Serious 1,703, Minor 6,976 | unclear: no licence or use terms on the items |
| OHSO `SORTPO_OCERS`, https://services2.arcgis.com/1RKb5IC5HFxsUYMS/arcgis/rest/services/SORTPO_OCERS/FeatureServer/0 | open | 2023 1,502; 2024 2,176; 2025 3,805 | Latitude/Longitude, Street, IntersectingStreetName | KABCO: O 5,210, B 1,084, C 615, A 390, K 128, Unknown 61 | unclear. **One region only** (16 southern/western counties, McClain 1,349 ... Harmon 32) |
| ODOT `AllCollisions_2012_2021`, https://services6.arcgis.com/RBtoEUQ2lmN0K3GY/arcgis/rest/services/AllCollisions_2012_2021/FeatureServer/10 | open | 2012-2021, 3,294-4,456 a year | route + milepoint, derived lat/lon | 1-5 | unclear. **I-35 corridor only** (39,688 of 39,752 rows) |
| OHSO Crash Facts (2021 latest), https://oklahoma.gov/highwaysafety/data/current-crash-data.html | open | to 2021 | aggregate PDFs | aggregate | n/a |
| Oklahoma City `OKC VZAP- Crashes`, https://services5.arcgis.com/2mOVdIcRtNH2JsSF/arcgis/rest/services/OKC_Crash_Map_WFL1/FeatureServer/0 | open | 2017 17,157; 2018 15,533; 2019 13,889; 2020 1,166 and 2021 1,504 (partial) | LATITUDE/LONGITUDE, ON_STREET, AT_STREET | 1-5 (Fatal 223 ... No Injury 33,633) | none stated |
| INCOG (Tulsa region) `AGOL_Crashes_2011_thru_2020`, https://services2.arcgis.com/Yl3gDnSPJVdpCPgG/arcgis/rest/services/AGOL_Crashes_2011_thru_2020/FeatureServer/0 | open | 2011-2020, 6,241-13,038 a year | Lat/Long | all levels | none stated |

## The export's columns

SAFE-T's "Export Collisions" gives "a table with one line for every crash report and one column for every data field
selected" (Training p. 103), with a "User Data Dictionary" for the codes (p. 109); each unit and person has its own
ID and carries the Collision ID (pp. 112-113). ODOT publishes no column list; the public copies built from SAFE-T
(ODOT's I-35 layer, INCOG, OKC) and from OCERS (SORTPO) show the names to expect. Map: `ok-column-map.json`
(`verified_against_real_export: false`).

Severity: SAFE-T codes 5/K Fatality, 4/A Incapacitating, 3/B Non-Incapacitating, 2/C Possible, 1/O Property
Damage Only (Training p. 18). OCERS writes KABCO words. **Trap:** OHSO's KAB layers label "A Fatal", "B Serious",
"C Minor"; those letters are sort keys. Fatal is K, Serious is A, Minor is B.

## Placement sample, the California way

`placement_sample.py ok <scratch>`, output `placement_sample.json`. 2,000 random Tulsa County 2021 crashes from
OHSO's KAB layer (the county's whole 2,093 is the frame); GPS hidden; placed from STREET_HIGHWAY +
NEAREST_INTERSECTING_ROAD on TIGER/Line 2024 Tulsa (40143) EDGES + FEATNAMES; scored against the hidden GPS. A
parenthesised second name ("E 151ST S (ST HWY 67)") is tried as a second spelling (35 crashes placed that way).

- GPS plausible: 100%. Street pair: 79.5% (no cross street: 411).
- Placed from names: **48.8%** of all crashes (61.4% of pairs): exact 775, unique_pair 173,
  fuzzy 12, near 9, verified_typo 6, relaxed 1. Review: 613 (no intersection of the two
  names 435, streets meet more than once 159).
- Auto under the default `Gate()`: 0% (TIGER-only network, expected). With `Gate(tiger_only_auto=True)`: 47.4%.
- Within 250 ft of the hidden GPS: **63.2%** of placed (Wilson low 60.2%), n = 976. No offset
  distance in the layer, so every crash is put at the intersection;
- What breaks (the officers' free text, not a code list): Tulsa's grid names written many ways ("71 ST. S.",
  "E. 71ST STREET", "S 116TH EA" for East Avenue, "E. 21S ST."), travel direction in parentheses or after the route
  ("US HIGHWAY 64 (EASTBOUND)", "I-244 WESTBOUND", "SH-20 E/B"), ramps ("US 75 S/B OFF RAMP"), "COUNTY ROAD
  (161ST W AVE)", and the N/S and E/W twins of the same grid number (streets meet more than once). Notes for the
  shared code when a reader is built: `research_notes/ok-2026-11-08/shared-fixes.md`.
- House addresses: no house-number field; not measured.

## Methods (rates, costs)

Not collected: no pack, so no `methods_ok.json`. ODOT's critical-rate analysis sits in SAFE-T advanced accounts
(Training p. 120).

## What the user needs to do

1. Ask ODOT Traffic Analysis (**ODOT-CollisionData@odot.org**) two things: may a private firm hold a SAFE-T account
   (with the Permit) and use exports inside a paid tool, and if not, will ODOT provide a statewide 2020-2024
   extract (collision, unit, person; CSV with Collision ID, lat/lon, on street, at street, severity) for that use.
2. Or ask OHSO (405-523-1570) for a statewide OCERS extract, 2023 on, all severities.
3. Send Engineering one SAFE-T "Export Collisions" CSV (one county, one year, all fields) and the User Data
   Dictionary, to confirm `ok-column-map.json` and build the upload reader.
4. Decide whether a KAB-only screening view (OHSO 2019-2021) is worth anything to you; we think not.

## What we didn't check

OKC's and INCOG's GPS shares and licence terms (none stated on the items); Tulsa's `Live_Crashes` map service
(looks like live incidents, not history); Norman, Broken Arrow, Lawton open data; ODOT's crash costs.
