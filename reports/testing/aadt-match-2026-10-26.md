# #287 Tester first: state-highway crashes matched to Caltrans AADT (2026-10-26)

Measure only. The basis is run 10's per-crash files with the freeway step on main (`coverage_crashes_r10c_*`).

- **Postmile:** each crash's postmile comes from `crashiq.postmile.nearest` (#248) on SHN Postmiles Tenth (2026-10-24).
- **Traffic counts:** Caltrans Traffic Census 2021–2024 workbooks, downloaded 2026-10-26 (user-approved in the Tester
  session): annual traffic volumes, truck AADT, and ramp ADT for all 12 districts. That's 60 files, 23.9 MB, plus the
  Traffic_AADT and Truck_Volumes_AADT layers. Each annual workbook has about 7,100–7,250 count points on 525–527
  route-county lines.
- **Segment rule (Tester's):** on the crash's route, suffix and county, the count point at or before its postmile
  gives its AHEAD leg. When that leg is blank, the next point's BACK leg is used. A "BREAK IN RTE" is never bridged.
- **Year:** each crash uses its calendar year's workbook, and 2025 uses 2024.
- **Engineering's join (PR #289)** is measured on the same crashes below.

## Statewide

802,493 SHS crashes in 2021–25 (freeway 652,058; state highway off freeway 150,435). 778,379 are on the map.

| Result | Crashes |
|---|---|
| **Segment AADT found** | **722,016 (92.8% of on the map)** |
| No postmile within 100 m of the point (GPS on a cross street, a frontage road, the far side) | 31,892 |
| Placed by CrashIQ (street names / FARS / approximate): no point in this test | 16,498 |
| No route number in the road names | 4,243 |
| Postmile before the first / after the last count point on the line | 1,434 / 1,041 |
| Break in route at the count point before | 749 |
| Count point with no AADT on that leg | 463 |
| No count points on the route in that county | 43 |
| Not on the map | 24,114 |

The "placed by CrashIQ" group will get a postmile in the app, from where CrashIQ placed it (#248). This test has no
point for it, so its count is a gap of the test, not of the data.

## By district and route type (segment AADT as % of on the map)

| District | On map | Segment AADT | % |
|---|---|---|---|
| 1 | 9,843 | 9,088 | 92.3 |
| 2 | 9,674 | 8,680 | 89.7 |
| 3 | 52,702 | 47,347 | 89.8 |
| 4 | 152,910 | 143,074 | 93.6 |
| 5 | 31,668 | 28,989 | 91.5 |
| 6 | 47,919 | 43,462 | 90.7 |
| 7 | 215,457 | 203,894 | 94.6 |
| 8 | 105,426 | 96,990 | 92.0 |
| 9 | 2,336 | 2,139 | 91.6 |
| 10 | 42,223 | 38,619 | 91.5 |
| 11 | 55,639 | 51,351 | 92.3 |
| 12 | 52,582 | 48,383 | 92.0 |

| Route type (from the crash's road names) | On map | Segment AADT | % |
|---|---|---|---|
| Interstate | 391,189 | 373,687 | 95.5 |
| US route | 86,816 | 81,691 | 94.1 |
| State route | 296,112 | 266,638 | 90.0 |
| Freeway (CCRS IsFreeway) | 643,893 | 615,172 | 95.5 |
| State highway off freeway | 134,486 | 106,844 | 79.4 |

Off-freeway state highways are the weak spot (79.4%). Their crashes' GPS often sits on the cross street more than
100 m from the route line, so #248 finds no postmile.

Route type is read from the crash's road names, so a crash naming two routes takes the higher class. SR-108 in Mono
County shows as "US route" below because US-395 was named too. In the app, the segment's own route decides.

## Ramps

7,370 ramp crashes are identified by a ramp word in the road names. 5,893 are on the map, and 4,424 of those have a
postmile.

| Ramp match (district ramp file, same route and county, within 0.3 mi) | Crashes |
|---|---|
| A ramp row within 0.3 mi | 3,732 |
| A count **in the crash's year** | 1,470 (33%) |
| The **latest count at or before** the crash year | **3,592 (81%)** |

- **Count age:** Caltrans counts ramps on rotation. With the latest-count rule, the count is from the crash year for
  1,470 crashes and 1–9 years older for the rest (1 yr 571, 2 yr 423, 3 yr 246, 4 yr 219, 5 yr 214, 6 yr 364, 7+ yr
  85). A latest-count rule needs the count year on every rate.
- **By district, latest-count rule:** D1 85/102, D2 66/68, D3 402/456, D4 424/670, D5 275/302, D6 267/329,
  D7 510/621, D8 674/762, D9 0/4, D10 305/489, D11 279/291, D12 305/330.
- **Not solved:** which ramp. An interchange has several ramps within 0.3 mi (on and off, each direction). The
  nearest row isn't necessarily the crash's ramp, and CCRS ramp crashes rarely say which one.
- **Data quirk:** District 7's 2021 file has placeholder-looking values (1001, 999 on several ramps).

## Engineering's join (PR #289, `AadtCache.for_crash`), on the same 725,746 crashes with a postmile

The rule differs from mine in two ways. It uses the October–September count year, and the nearer point's leg (the
AHEAD leg in the first half of a segment, the next point's BACK leg in the second half).

| | Crashes |
|---|---|
| Both match | 717,250 |
| Tester only | 4,766 (mostly postmile past the last count point, or a blank AHEAD leg where the next point's BACK fills it) |
| #289 only | 185 |
| Neither | 3,545 |
| Where both match: same AADT / within 10% / differs by more | 568,007 / 89,646 / 59,597 |
| #289 used the latest year (count year 2025) | 183,160 |
| Segment spans a postmile prefix change (R / M ...) | 86,902 |

The two joins agree on coverage. AADT differs by more than 10% on 8% of crashes, from the half-segment leg rule and
the October–September year. That's expected, not a defect. The 86,902 crashes on prefix-change segments are the ones
to check before rates are shown: a realignment can make the postmile difference a poor length.

## Rate sanity check (hand-picked segments, 2021–24, all crashes, Tester segment rule)

Crashes per million vehicle-miles = crashes / Σ(AADT × length × 365) × 10⁶. These are CCRS crashes, not Caltrans'
on-highway counting rule.

| Segment | Type | Length mi | AADT 2021 → 2024 | Crashes | Per MVM |
|---|---|---|---|---|---|
| I-110 LA PM 19.996–21.444 | Interstate (busiest by crashes) | 1.45 | 254,000 → 271,000 | 1,340 | 2.41 |
| I-880 ALA PM 18.353–20.162 | Interstate | 1.81 | 263,000 → 240,000 | 1,234 | 1.84 |
| I-80 SF PM 5.588–7.719 | Interstate (Bay Bridge approach) | 2.13 | 119,000 → 118,000 | 1,193 | 3.14 |
| I-880 ALA PM 23.644–24.767 | Interstate | 1.12 | 196,000 → 211,000 | 386 | 1.15 |
| I-15 RIV PM 33.387–35.641 | Interstate | 2.25 | 140,000 → 151,000 | 235 | 0.48 |
| SR-99 BUT PM 32.445–33.282 | State route | 0.84 | 51,000 → 86,000 | 97 | 1.02 |
| SR-9 SCR PM 5.64–6.46 | State route (mountain two-lane) | 0.82 | 6,500 → 6,500 | 49 | 6.30 |
| SR-46 SLO PM 2.372–11.471 | State route (rural) | 9.10 | 4,500 → 4,550 | 17 | 0.28 |
| US-101 MON PM 32.015–37.309 | US route (rural) | 5.29 | 17,500 → 20,800 | 42 | 0.28 |
| SR-108 MNO PM 0.0–7.9 | rural (labelled US, see above) | 7.90 | 700 → 660 | 3 | 0.26 |

The orders of magnitude are plausible: congested urban interstates 1.2–3.1, rural roads about 0.3, and a winding
mountain two-lane far higher. Two things to check by hand:
- **SR-99 Butte:** the AADT jumps 51,000 → 86,000 between 2021 and 2024.
- **SR-9 Santa Cruz:** 6.3 per MVM on 0.8 mi.

No Caltrans statewide average is compared here; that needs its published table (#287 item 1).

Scripts: `tests/statewide/aadt_match.py` (match, gaps, ramps), `aadt_compare_289.py` (the #289 join on the same
crashes). Outputs in the Tester worktree: `aadt_match.json/.csv`, `aadt_ramps.json`, `aadt_rate_check.json`,
`aadt_compare_289.json`. The source note is for Engineering's `knowledge/sources/ca-caltrans-traffic-census.md`
(#287).
