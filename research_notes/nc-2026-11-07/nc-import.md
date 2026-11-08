# North Carolina: crash sources, placement sample, importers

Hermes, 2026-11-07. All counts were queried live on 2026-11-07 (ArcGIS REST `returnCountOnly` / `outStatistics`,
Opendatasoft `group_by`). Methods, rates and costs are in `nc-methods.md`.

**Bucket: D for the statewide all-crash file (TEAAS is gated), with A\* open pieces:** NCDOT's statewide
fatal + serious-injury layer and non-motorist layer, and Raleigh's and Durham's city tables. Licences: none of the
crash sources has an explicit grant for paid use; Charlotte's is CC BY-NC-SA (no).

## 1. Statewide (NCDOT)

| Source | URL | Access | Rows | Location | Severity | Keys |
|---|---|---|---|---|---|---|
| TEAAS (all reportable crashes since 1990) | https://connect.ncdot.gov/resources/safety/Pages/TEAAS-Crash-Data-System.aspx | **Gated**: "free of charge to state government personnel, municipalities, law enforcement agencies, planning organizations, and research entities"; a permanent account needs the online modules plus an instructor-led class (next: Dec 1-3, 2026, via UNC HSRC) | not measured | route + milepost, streets | KABCO + U | TEAAS Crash_ID |
| NC Fatal and Serious Injury Crashes | https://www.arcgis.com/home/item.html?id=a9125212cca34f2eb321de3bb0f1b7f2 (layer `services.arcgis.com/NuWFvHYDMVmmxMeM/.../NC_FatalAndSeriousInjuryCrashes/FeatureServer/0`) | open, no login | 53,917 (K 14,846, A 39,071), 2016-2025, "updated annually to reflect the most recent 10 years" | GPS on 53,604 (313 at 0/null); `MapMethod` XY 28,330, RTEMP (route/milepost) 25,587; On_Road + From_Road on 100%, Distance (miles) + Direction, Toward_Road | K / A only | Crash_ID (TEAAS); report link needs NCID login |
| NCDOT Non-Motorist Crashes | https://www.arcgis.com/home/item.html?id=11309c4876f844a593868e742143eca4 | open | 58,328, 2007-2025 (2,535-3,458 a year; 2025: 3,458) | GPS (3 missing); route + milepost; **no street names** | KABCO for the crash, the non-motorist and the driver (2025: K 291, A 445, B 1,394, C 986, O 320, unknown 22) | CrashID |
| Statewide Crash Table (behind the NCDOT Statewide Crash Dashboard, item c3daf738d1ae461e978434399c143e9f) | `services.arcgis.com/NuWFvHYDMVmmxMeM/.../StatewideCrashTable/FeatureServer/3` | open but undocumented (dashboard table) | 2021: 307,122; 2022: 302,196; 2023: 311,111; 2024: 310,162; 2025: 304,599; 2026 (to date): 212,353 | **county and city only** | crash KABCO + U (2024: K 1,629, A 4,228, B 24,865, C 44,453, O 223,990, U 10,997), injury counts | Crash_ID |
| NC Vision Zero Crash Query Tool | https://ncvisionzero.org/visualizations/crash-query-tool/ | open | aggregate charts/tables only; no record download found | - | - | - |

Licence for all NCDOT layers: a liability disclaimer only ("shall not be held liable for any errors in this data...
cannot be construed to be a legal document"). No open licence and no use restriction stated: **unclear**.

## 2. Cities

| City | Source | Rows | GPS | Streets | Severity | Persons | Licence |
|---|---|---|---|---|---|---|---|
| **Raleigh** | Reported Crash Locations + Persons, RPD, daily (https://data.raleighnc.gov/datasets/ral::reported-crash-locations, item 3f503c43a0bd4490be7dec17650bcda9) | 271,782 crashes, 2015-2026: 2015 24,482; 2016 25,727; 2017 25,186; 2018 25,314; 2019 26,566; 2020 17,937; 2021 20,947; 2022 21,497; 2023 21,995; 2024 22,306; **2025 21,591**; 2026 18,218 (to 2026-11-05); 665,631 person rows | 99.89% plausible in 2025 (21,567 / 21,591), but **the city publishes only crashes whose point is in Raleigh**, so this is not a statewide rate | On / At-or-From / Toward roads, feet or miles + direction: 99.87% have on + at; 2025 "At" 4,197, "From" 17,367; house number in the on-road field 4,498 (20.8%) | crash counts killed / A / B / C / unknown → KABCO + U (2025: K 36, A 245, B 1,858, C 1,599, U 998, O 16,855) | `key_crash` links; **Injury and PersonType are blank on every 2025+ person row** (77,796 rows) | Open Raleigh Data Policy (use at own risk; the city "reserves the right ... to require the termination of any and all displaying, distributing or otherwise using" the data) + RPD terms ("Misuse of the data may subject a party to criminal prosecution for false advertising under NC GS § 14-117"): **unclear** |
| **Durham** | All Durham Crashes (City of Durham Vision Zero), item cce39a051d34496498857046fde17f23 | 199,142 person rows = crashes 2016 7,991; 2017 8,129; 2018 8,527; 2019 8,429; 2020 5,902; 2021 9,152; 2022 7,227; 2023 7,004; 2024 6,932; **2025 6,716** (latest 2025-12-31) | 100% (0 missing per year) | OnRoad / FromRoad / TowardRoad on 100%, DistMiles; names without street type ("FAYETTEVILLE", "I 85"); DirFrom is mostly digits 1-6 (133,659 rows "2") | KABCO + U per crash and per person | Crash_ID (TEAAS) | not in the Durham open-data catalog (only behind the Vision Zero dashboard), no licence text: **unclear** (A\*) |
| Charlotte | CDOT TCLS Crashes, `gis.charlottenc.gov/arcgis/rest/services/CDOT/TCLS_Crashes/MapServer/0` (item e48e2174b51040dca22e9aec4fd894f6) | 553,976 crashes, 2010-2026 (e.g. 2024: fatal 91, serious 119, non-serious 1,891, possible 6,294, PDO 34,848), latest 2026-11-04 | 117 missing | **none** | 5 levels = K/A/B/C/O | none | **CC BY-NC-SA 4.0: no** for a paid product |
| Greensboro | Greensboro Crashes (MPO; owner apd_gis_content), item 861d3576a5624c55b03910240092a43e | 76,704, 2017-2023 (9,799-11,572 a year), nothing after 2023 | yes | none (route + milepost) | 4 levels (fatal, serious, minor-or-possible, none-or-unknown): B and C merged | none | disclaimer only: unclear |
| Cary | Crash Data, https://data.townofcary.org/explore/dataset/cpd-crash-incidents/ | 20,366: 2021 3,999; 2022 4,307; 2023 4,403; 2024 4,424; 2025 3,233 | **none** (no geometry column) | text only ("0.18 MILES FROM S.R. 1152 (HOLLY SPRINGS RD)") | fatality / possible-injury counts only | none | **CC0 1.0** |
| Winston-Salem | none found: only the eCrash report search (https://www.cityofws.org/2043/Accident-Reports) | - | - | - | - | - | - |

Raleigh is 7.1% of the state's 2025 crashes (21,591 / 304,599).

Raleigh format changes found (both handled in the reader):
- `DateOfCrash` was true UTC through Sept 2024; since Oct 2024 it is local wall time labelled UTC (UTC hour minus
  `Crash_Date_Hour` = 4-5 before, 0 after; 185 of 200 sampled Oct 2024 rows already switched). The reader uses
  `Crash_Date_Hour` to pick the right reading per row.
- Since Oct 2024 weather, road class, road feature, traffic control and relation-to-road are empty (0 of 500
  sampled 2025 rows have weather vs 500/500 in 2020).

## 3. Placement sample (Raleigh 2025, Wake County TIGER/Line 2024)

Script: `placement_sample.py` (and `placement_diag.py`); output `placement_summary.json`. 2,000 crashes drawn
(seed 20261107) from the 21,564 2025 crashes with GPS and both road names; GPS hidden; network = TIGER/Line 2024
EDGES + FEATNAMES for Wake (37183), 22,097 street keys; `locate.place` with the default `Gate()` (auto tiers exact,
unique_pair, freeway_offset). House-address crashes (on-road field "3955 NEW BERN AVE" with the same street as the
cross street, 129 = 6.45%) used `AddressIndex` on Wake County MAR address points (19,569 points fetched for the
sample's streets; CC BY 4.0). Address placements are counted as auto here.

| | As published | With NC pre-splits* |
|---|---|---|
| exact | 977 | 1,223 |
| unique_pair | 102 | 104 |
| address | 110 | 109 |
| verified_typo / relaxed / near / fuzzy | 45 / 25 / 10 / 19 | 50 / 25 / 15 / 19 |
| review | 712 | 455 |
| placed (any tier) | 64.4% | 77.25% |
| **auto-placed (gate + address)** | **59.45%** | **71.8%** |
| auto within 250 ft of the hidden GPS | 62.2% (Wilson 95% low **59.5%**) | 55.5% (low 52.9%) |

\* pre-splits in the script only: a bare "440", "40", "540", "87" (13% of on-road values) → "I-440" etc.;
"SR 1152 (HOLLY SPRINGS RD)" → the name; runs of spaces collapsed.

**The accuracy is far below California's, and the diagnosis says most of it is the reference, not the locator**
(`placement_diag.py`, exact tier, 977 crashes):
- crashes reported **at** the intersection (no offset): 197 / 236 within 250 ft = **83.5% (Wilson low 78.2%)**,
  median 45 ft;
- crashes 1-100 ft **from** the cross street: only 153 / 261 within 250 ft, median 169 ft from our point and 187 ft
  from the intersection itself, so the officer's point is often not where the report's offset puts it
  (Raleigh says the coordinates "are entered manually by the officer and may be subject to error");
- offsets of 300-1,000 ft: 110 / 199 (point) vs 16 / 199 if we ignored the offset, so the offset helps;
  over 1,000 ft: 16 / 61;
- 90 of 977 points have 2-3 decimals (±0.0005-0.005°, up to ~1,800 ft).
So the 250-ft test against Raleigh GPS is a lower bound on placement accuracy, and the "From" offsets are noisy.

**No-GPS crashes it would add:** Raleigh publishes only crashes with a point in the city (24 of 21,591 in 2025 fail
our in-state check), so for Raleigh there is almost nothing to add. Statewide KA has 313 crashes without GPS, all
with on/from roads: not run (not measured).

What breaks in the shared code (for Engineering; not changed here):
1. `names.street_key("440")` → core "440": a bare interstate number never matches TIGER "I- 440". A state-pack
   alias for NC: bare 40/85/87/95/440/540/885 → I-n (in Wake; bare "1", "70", "401" are US routes).
2. "SR 1152 (HOLLY SPRINGS RD)" → core "SR 1152" (the parenthesized name is dropped, and it is the name TIGER
   carries for local streets).
3. Durham/TEAAS names carry no street type ("FAYETTEVILLE"): only the relaxed tier matches, which the gate holds.
4. Freeway crashes are where the pre-splits lose accuracy: once "540" becomes "I-540", `exact` places it at the
   interchange plus the report's offset, and several miss by far ("540" & "GLOBE RD": 2,044 ft). The
   freeway_offset tier never fired on this sample (0 placements); why was not checked.
5. NC "From" offsets: feet in `LocationFeetFromRoad`, miles in `LocationMilesFromRoad` (the reader merges them).

## 4. House addresses

- **NAD**: NC points are present (65,830 in a Raleigh test box, 40,095 Greensboro, 27,073 Durham), but every
  attribute query on the NAD view returned HTTP 400, so county coverage and source are **not measured**.
- **AddressNC** (NC OneMap, statewide from NG911, monthly): 6,297,169 points, all 100 counties, downloadable per
  county as file geodatabase (https://www.nconemap.gov/pages/addresses). Terms (https://www.nconemap.gov/pages/terms):
  "committed to offering access ... at no charge ... free and unrestricted use policy ... Written release agreements
  ... are not required and will not be issued ... Any sale of this data must not violate applicable state laws";
  citation requested: **ok with attribution**.
- **Wake County MAR** address points: 695,398, `services1.arcgis.com/a7CWfuGP5ZnLYE7I/.../Wake_County_MAR_Address_Data_Public/FeatureServer/0`, **CC BY 4.0**.

## 5. Importers built (standalone, not wired)

- `backend/crashiq/sources/nc_arcgis.py`: ArcGIS paging by object id, KABCO letters, date + time, NC GPS check.
- `nc_raleigh.py`: crashes + persons, offsets, house addresses kept in `primary_road`, crash severity K/A/B/C/U/O.
- `nc_ncdot.py`: statewide KA and non-motorist layers (persons from the non-motorist layer).
- `nc_durham.py`: person rows grouped into crashes with persons.
- Fixture `tests/fixtures/nc_sources.json` (240 KB, real pages; `make_nc_fixtures.py` re-records), tests
  `tests/test_source_nc.py` (9, offline).

Wiring needs (issue #19 seam): a source registry entry per reader; NC county FIPS (Raleigh rows carry none);
NC severity rule for U (NCDOT's "injury unknown", not CA's "injured, level not stated"); the name aliases above; the
AddressNC / Wake MAR entries in `data/reference/address_points.json`; KA-only and non-motorist-only sources must be
labelled so studies don't read them as all crashes.

## 6. Blockers and user actions

- TEAAS is the only all-crash statewide source with locations; it is for agencies/consultants. User: if a client
  agency or MPO has TEAAS, ask for one TEAAS crash export (one county, one year) so a TEAAS "upload your export"
  reader can be built; Durham's layer suggests the column names.
- Licence: ask Raleigh (Open Raleigh) and NCDOT Traffic Safety whether displaying their crash data in a paid tool is
  allowed; Charlotte's CC BY-NC-SA rules its data out unless Charlotte grants permission.

## What we didn't check

- TEAAS export layout (no spec found publicly); NAD county coverage; the Statewide Crash Table's update cadence.
- Placement in a second county or on the statewide KA layer; Durham placement.
- Greensboro/Charlotte person data (none published).
