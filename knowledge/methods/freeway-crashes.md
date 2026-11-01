# Placing freeway crashes (bucket D1)

Status 2026-10-23, updated 2026-10-25 (#278; see "How the app finds the spot" below for the current rules): method agreed with the user; build = #246 (report placement), #247 (GPS repair), #248 (postmile
output). Measurements: Tester, run 9A basis (CCRS mirror 2026-10-19, OSM 2026-10-18).

## How CHP describes a freeway crash
`PrimaryRoad` = the freeway or ramp the crash was on; `SecondaryRoad` = a reference street, usually one that crosses
**over or under** the freeway (a bridge, not an intersection); `SecondaryDistance` + `SecondaryUnitOfMeasure` +
`SecondaryDirection` = how far from that street, measured along the freeway. The two roads never meet, so an
intersection matcher finds nothing. That's why 24,076 crashes (2021–25) sat in the difficult bin.

- `IsFreeway = True` means freeway **jurisdiction**, not the main lanes: ramps and freeway-to-freeway connectors carry it too.
- CCRS has `Milepost*` fields, and CHP filled them with real Caltrans postmiles, but only on 2–4% of 2021–22 freeway
  crashes and almost never since 2023 (D1: 830 of 24,076; `sources/ca-ccrs.md`). Too rare to place D1; useful as an
  independent third source to check the report against the GPS. Since CHP moved to CCRS (2015), Caltrans postmiles are
  no longer returned to SWITRS. Caltrans assigns postmiles afterwards in TASAS, from the
  same road-name description (`sources/ca-caltrans-tasas.md`).

## The user's method (2026-10-23, worked through three real crashes)
| Kind (D1 count) | How the report reads | Where to place it |
|---|---|---|
| Mainline (16,793) | `I-405 N/B` / `ARTESIA BLVD.` / S 200 F | Where the cross street crosses the freeway, then the stated distance **in the stated direction** along the stated-direction lanes |
| Ramp (2,528) | `NB I5 OFF RAMP` / `FLORA ST` / N 10 F | Where the ramp meets the cross street (the ramp terminal), plus the offset; a few feet = at the terminal |
| Freeway-to-freeway (1,683) | `I-680 S/B TO SR-4` / `SR-4` / N 1320 F | **On the connector ramp**, the stated distance from the second freeway along the connector |

**Report beats GPS** (2026-10-23; **replaced 2026-10-25**: officer GPS that fits is kept, see below): when the officer's GPS and the report disagree, place
by the report and keep the GPS as provenance. The officer's GPS is a weak answer key on freeways.

Worked examples (unit-test truth for #246):
| Record | Officer GPS | Truth | Why |
|---|---|---|---|
| 1456564 Lawndale | 33.8732, -118.3433 (NW corner of the crossing) | 200 ft S of the Artesia crossing, NB lanes | GPS contradicts the report |
| 2327267 Stockton | 37.957553, -121.311296 (inside a parcel) | 37.957310, -121.311389 (user pin, in the street) | a crash doesn't happen in a parcel |
| 1428399 Martinez | 37.9971, -122.0734 | the officer GPS | agrees with the report; on the connector |

The user misread two of these at first (S read as N; connector read as mainline). Read every field as written: the
direction is literal, and "X TO Y" names a connector.

## Measured evidence (Tester, 2026-10-23)
**GPS repair** (bin 2: 34,062 crashes with off-road GPS, 24,309 checked after 9,753 fit under the looser name check; "repaired" = exactly one repair fits the report, 400 ft + offset):
| Repair | Fixed | Repair fits | Chance control | Verdict |
|---|---|---|---|---|
| Degrees-minutes-seconds read as decimal (all agencies, mostly CHP areas) | 4,111 (D1 3,057) | 55.6% | 0.7% | real → #247 |
| Missing minus on longitude | 432 | 74% | 0.78% | real → #247 |
| Latitude ±1/2/3 whole degrees | ~980 "fits" | ±1°: 1.5% | wrong-way 2.1% | **chance; don't use** |
| Lat/lon swapped | 1 | | | not worth a rule |

**"GPS is on the named freeway" is not enough.** Of 16,329 D1 crashes with rejected GPS, 5,894 (36%) sit on the named
freeway or a link joined to it, but the 2 km random-shift control fits 1,263 (7.7%). Freeways are long, so about 1 in 5
fits is chance. Accept GPS only when it agrees with the **spot the report describes** (within 400 ft).

## The D1 waterfall (each crash stops at the first step that places it)
Measured on all 24,076 D1 crashes (Tester, 2026-10-23, run 9A basis):
| Step | Crashes | Fatal | KSI | Chance control |
|---|---|---|---|---|
| 1 GPS repaired (#247) | 3,139 | 1 | 88 | |
| 2 GPS within 400 ft of the report's spot | 1,925 | 8 | 56 | 0 |
| 3 Report spot found → placed by the report (#246) | 8,657 | 13 | 217 | |
| 4 Spot not found, GPS on the named freeway → review only | 2,247 | 17 | 67 | 395 |
| 5 Unplaced | 8,108 | 24 | 318 | |
Steps 1–3 place 13,721 (57%). Why step 3 fails: the cross street meets the route more than once or not at all (3,799),
route or street not on the map (2,134), no compass direction (1,784); ramps: no route number (981), terminals too far
apart (561). Step-3 hidden-GPS accuracy: on #246.

## How the app finds the spot (#259, 2026-10-25)
`backend/crashiq/freeway.py`, aligned with the Tester's reference method (`tests/statewide/freeway_report_point.py`):
- **Meeting point.** Where the reference street crosses the stated-direction lanes (crossings within 600 ft are one
  place). If it never crosses them (the map often draws an overpass without a crossing segment), where it passes within
  300 ft. A street that meets either carriageway in two places more than 3,300 ft apart is ambiguous and never guessed.
  A reference road that is another freeway (`I-5` / `SR-91`) meets the route where their main lanes cross.
- **Walk.** From the meeting point, snapped onto the lanes, the stated distance: the first step toward the stated
  compass direction, then along the freeway as it bends.
- **"X TO Y" by its cross street.** A local street: mainline on X from that street (user worked example 4630945),
  placed as approximate (user 2026-10-25). Y: along the connector from Y, Y's stated direction picking the connector
  (Martinez). X: along the connector from where it leaves X. True connectors (cross street X or Y) are held for review
  (user 2026-10-25).
- **Officer GPS that fits the named roads is kept** (user 2026-10-25, replacing "report beats GPS" above).

Measured (Engineering scratch run on the Tester's run-10 accuracy sample, 6,000 freeway crashes whose police GPS fits
the report, GPS hidden, the Tester's fixed `fwy_raw` street lookup):
| Method | Placed | Within 0.5 mi of the officer's GPS |
|---|---|---|
| Reference (`freeway_report_point`) | 4,203 | 3,971 (94.5%) |
| App before #259 | 4,073 | 3,783 (92.9%) |
| App after #259 | 4,285 | 4,055 (94.6%) |
| of which auto-placed (mainline, ramp, local-street "X TO Y") | 4,248 | 4,024 (94.7%) |
| of which local-street "X TO Y" | 74 | 64 (86.5%) |
| of which true connectors (held for review) | 37 | 31 (83.8%) |

## Reuse in another state
Look first for the state's own route/postmile (or milepost) field and a public linear-reference layer; if crashes carry
a milepost, place by it and skip most of this. Otherwise apply the three rules above, then check them with the
hidden-GPS test.
