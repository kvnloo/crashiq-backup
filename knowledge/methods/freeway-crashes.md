# Placing freeway crashes (bucket D1)

Status 2026-10-23: method agreed with the user; build = #246 (report placement), #247 (GPS repair), #248 (postmile
output). Measurements: Tester, run 9A basis (CCRS mirror 2026-10-19, OSM 2026-10-18).

## How CHP describes a freeway crash
`PrimaryRoad` = the freeway or ramp the crash was on; `SecondaryRoad` = a reference street, usually one that crosses
**over or under** the freeway (a bridge, not an intersection); `SecondaryDistance` + `SecondaryUnitOfMeasure` +
`SecondaryDirection` = how far from that street, measured along the freeway. The two roads never meet, so an
intersection matcher finds nothing. That's why 24,076 crashes (2021–25) sat in the difficult bin.

- `IsFreeway = True` means freeway **jurisdiction**, not the main lanes: ramps and freeway-to-freeway connectors carry it too.
- The public CCRS tables have **no route or postmile column** (all 30 crash columns checked). Since CHP moved to CCRS
  (2015), Caltrans postmiles are no longer returned to SWITRS. Caltrans assigns postmiles afterwards in TASAS, from the
  same road-name description (`sources/ca-caltrans-tasas.md`).

## The user's method (2026-10-23, worked through three real crashes)
| Kind (D1 count) | How the report reads | Where to place it |
|---|---|---|
| Mainline (16,793) | `I-405 N/B` / `ARTESIA BLVD.` / S 200 F | Where the cross street crosses the freeway, then the stated distance **in the stated direction** along the stated-direction lanes |
| Ramp (2,528) | `NB I5 OFF RAMP` / `FLORA ST` / N 10 F | Where the ramp meets the cross street (the ramp terminal), plus the offset; a few feet = at the terminal |
| Freeway-to-freeway (1,683) | `I-680 S/B TO SR-4` / `SR-4` / N 1320 F | **On the connector ramp**, the stated distance from the second freeway along the connector |

**Report beats GPS** (same as the city-street rule in docs/03): when the officer's GPS and the report disagree, place
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
**GPS repair** (bin 2, 24,309 crashes with off-road GPS; "repaired" = exactly one repair fits the report, 400 ft + offset):
| Repair | Fixed | Repair fits | Chance control | Verdict |
|---|---|---|---|---|
| Degrees-minutes-seconds read as decimal (all agencies, mostly CHP areas) | 4,111 (D1 3,738) | 55.6% | 0.7% | real → #247 |
| Missing minus on longitude | 432 | 74% | 0.78% | real → #247 |
| Latitude ±1/2/3 whole degrees | ~980 "fits" | ±1°: 1.5% | wrong-way 2.1% | **chance; don't use** |
| Lat/lon swapped | 1 | | | not worth a rule |

**"GPS is on the named freeway" is not enough.** Of 16,329 D1 crashes with rejected GPS, 5,894 (36%) sit on the named
freeway or a link joined to it, but the 2 km random-shift control fits 1,263 (7.7%). Freeways are long, so about 1 in 5
fits is chance. Accept GPS only when it agrees with the **spot the report describes** (within 400 ft).

## The D1 waterfall (each crash stops at the first step that places it)
1. GPS repaired (#247). 2. GPS within 400 ft of the report's spot. 3. Report spot found → place by the report (#246).
4. Spot not found, GPS on the named freeway → review only. 5. Unplaced.
Per-step counts and the step-3 hidden-GPS accuracy: Tester, on #246.

## Reuse in another state
Look first for the state's own route/postmile (or milepost) field and a public linear-reference layer; if crashes carry
a milepost, place by it and skip most of this. Otherwise apply the three rules above, then check them with the
hidden-GPS test.
