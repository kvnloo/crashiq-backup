# Hawaii crash data: verified 2026-11-08 (Hermes)

**Verdict: no pack.** HDOT does publish record-level crash points with no login, so the 2026-11-02 screen
("public HDOT ArcGIS layers only give Oahu 2007-2018 per-location counts") was wrong. But those layers give the
**year only** (no date, no time), **no KABCO** (one "major injury" flag), **no street names, route or milepost, no
report number**, and **state highways only before 2023**. A corridor study can't be built on that without inventing
dates and severity, so Hawaii stays gated (bucket D) until HDOT releases a SHACA export. Below: what exists, measured.

## 1. Sources found (all checked live 2026-11-08)

Searched ArcGIS Online by the agency as owner (`owner:dot_zwu`, `owner:dot_mmekuria`, `owner:dot_rwollenbecker`,
`owner:HawaiiStateGIS`; HDOT's org is `HQ0xoN0EzDPBOEci`) and HDOT's Socrata site (`highways.hidot.hawaii.gov`).

| # | Layer | URL | Rows | Years | What it has |
|---|---|---|---|---|---|
| 1 | HDOT_Crash_Layer (owner dot_zwu, edited 2025-11-26) | https://services.arcgis.com/HQ0xoN0EzDPBOEci/arcgis/rest/services/HDOT_Crash/FeatureServer/0 (also Socrata `kktn-udgf`, `qtij-gda6`) | 31,644 | 2015-2023 | `crash_year`, `county` (HON/HAW/MAU/KAU), `gps_latitude/longitude`, `prim_jurisdict` (S1U...C7R), `crashseveritymajorinjury` (0/1/null), mode flags (ped, bike, moped, motorcycle), factor flags (alcohol, drugs, speed, distraction...), `crashactions` codes |
| 2 | HDOT_Crash_Layer_2024 | https://services.arcgis.com/HQ0xoN0EzDPBOEci/arcgis/rest/services/HDOT_Crash_Layer_2014/FeatureServer/0 | 5,671 | 2024 | same fields |
| 3 | FatalCrash_2012-2025 (edited 2026-09) | https://services.arcgis.com/HQ0xoN0EzDPBOEci/arcgis/rest/services/FatalCrash/FeatureServer/0 | 1,416 | 2012-2025 | fatal crashes only: `Crash_Date`, x/y, `Total_Fatalities`, road-user flags, contributing factors; `CrashId` only from 2019 (458 rows) |
| 4 | HiDOTFatalCrashEntry | https://services.arcgis.com/HQ0xoN0EzDPBOEci/arcgis/rest/services/HiDOT_Fatal_Crash_Entry_View/FeatureServer/0 (Socrata `7cny-nhb8`) | 1,506 | fatal | route, road name, milepost for fatal crashes |
| 5 | HIDOT_Crashes_Layer_2015-2019 | .../State_jurisdiction_accidents/FeatureServer/0 | 18,560 | 2015-2019 | older copy of #1 (state roads) |

Older layers (Oahu_Crashes_2007to2016, 2017to2018 by owner bbutoaj) are the per-location counts the screen saw.

**Measured from #1 + #2** (`hi_measure.py`, output `hi_measure.json`):

| Year | Rows | State roads | County roads | "Major injury" = 1 |
|---|---|---|---|---|
| 2015 | 3,921 | 3,921 | 0 | flag blank |
| 2016 | 4,087 | 4,087 | 0 | flag blank |
| 2017 | 3,442 | 3,442 | 0 | flag blank |
| 2018 | 3,637 | 3,637 | 0 | 158 |
| 2019 | 3,472 | 3,472 | 0 | 248 |
| 2020 | 2,400 | 2,400 | 0 | 197 |
| 2021 | 2,720 | 2,720 | 0 | 231 |
| 2022 | 2,322 | 2,322 | 0 | 208 |
| 2023 | 5,643 | 2,401 | 3,239 | 495 |
| 2024 | 5,671 | 2,357 | 3,304 | 524 |

- Points inside Hawaii: 99.93% of 37,315. 27 rows sit at 0,0 and 36 at the Honolulu default point
  (21.480852, -157.923130), which the layer's own description says replaces missing coordinates.
- County roads appear only from 2023: a 5-year study of a Honolulu city street (2020-2024) would see 2 years of
  crashes and 3 empty ones. Example: Honolulu 2024 has 4,025 crashes, 60% on county roads; Honolulu 2022 has none.
- No severity beyond the flag. "HDOT Serious Crashes by Year" (Socrata `25hu-fvne`) is a count of the flag; there is no
  fatal flag in #1/#2, and the rest (flag 0) mixes minor-injury and property-damage crashes.
- No date: `crash_year` only. HDOT's own fatal map says "All crash date prior to 2019 is defaulted to 12/30 or 12/31
  due to lack of exact date and time" (https://experience.arcgis.com/experience/3b630bae39bd4d4e824f55d854450a84/page/Fatal-Crash).
- No key: no report number, so the fatal layer (#3) can't be joined to #1 except by point and year (not attempted).

**Honolulu open data:** `data.honolulu.gov` has no crash dataset (Socrata catalog query "crash" = 0 results,
2026-11-08). Its "Traffic Incidents" (`ykb6-n5th`) is a 24-hour police dispatch feed, not crash reports.

## 2. Licence

- #1/#2: no licence or description on the items. HDOT's public crash pages say: "This data is provided for highway
  safety and educational purposes only. Use of this website constitutes agreement with this policy" (23 USC 407;
  same page as above). That doesn't grant use in a paid product: **unclear / no**.
- #3: item licence "State of Hawaii Terms of Use. The contents of this web page are public domain..."
  (https://www.arcgis.com/home/item.html?id=8aa60d9c408b41449b248e3e7623d77d): **ok** (fatal only, as FARS).

## 3. Where the full data lives

SHACA (State of Hawaii Advanced Crash Analysis), HDOT Traffic Safety's crash system fed electronically by all four
county police departments since 2021 (HDOT 2021 Highway Safety Annual Report). HDOT's HSIP analyses use "major traffic
crashes" (fatal, injury, or property damage over the reporting threshold) and "high crash listings and crash data for
county roads are submitted to the county offices" (HSIP 2025 report). No public export spec was found: the column map
(`hi-column-map.json`) names the fields a SHACA export must carry, from the open layer and the HSIP report.

## 4. Placement, the California way

No street names, route or milepost in any open all-crash layer, so name placement can't be run: GPS is the only
location. Honolulu (15003) 2024: 4,025 crashes, 99.78% with a usable point. Accuracy against hidden GPS: not
measurable (nothing else to place from). House addresses: not in the layer.

## 5. Methods (see hi-methods.md)

HDOT uses the Number-Rate method and "crash costs established by FHWA" (HSIP 2025 report). No HDOT rate or cost
table found.

## What you need to do

1. Ask HDOT Traffic Safety (SHACA) for one statewide export, 2019-2024, with crash date, KABCO severity per crash,
   route + milepost or street names, report number, and written permission to use it in a paid product.
2. Or ask HDOT to add the date and KABCO severity to its open HDOT_Crash_Layer; with those it becomes a pack
   (GPS on 99.9%).

## What we didn't check

- What `crashseveritymajorinjury` means exactly (A only, or K+A): no data dictionary is published.
- Whether 2015-2022 county-road crashes exist in SHACA but were left out of the open layer (likely, not confirmed).
- The HSIP 2025 PDF itself: highways.dot.gov blocks scripted downloads (403), so its text came from a web extract.
