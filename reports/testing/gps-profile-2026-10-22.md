# Agency GPS quality profile, and the "GPS right, names wrong" re-check (#219)

Tester, 2026-10-22. Measure only. Basis: CCRS mirror 2026-10-19, 2021-2025, latest version, not deleted, GPS inside California; fit = corrected #199 check; pile = gps_piles.json (pooled, #218 thresholds); OSM 2026-10-18.

## Findings
1. **Nine in ten police GPS points fit the report's own streets:** 90.0% of 1,554,835.
2. **The biggest problem is GPS that fits but sits at the intersection while the report places the crash farther along the road:** 78,095 crashes, 5.0%. Each is within 50 ft of where the two named roads meet, with a stated offset over 50 ft.
   - These are on the map today, at the intersection rather than the stated point; #218 rule 1 targets them.
   - Highest: Vacaville, South Gate and Glendale at about 38–40%, Vallejo, Woodland and Pomona at about 35–36%, Santa Ana 11.0%.
3. **More than a mile from the named roads:** 1.8% statewide.
   - Falling: 3.2% in 2021 → 1.1% in 2025.
   - San Jose PD is the outlier at 27.2%, alongside 63.2% of its GPS in degrees-minutes-seconds format (#143).
4. **Shared default / dispatch points are rare but real:** 1,755 crashes (0.1%) on 50 points.
   - The biggest are statewide CHP defaults: one point near Auburn holds 333 crashes from 59 CHP areas (2021–22), and two downtown Sacramento points hold 256 (2025 only) and 225.
   - There are also whole-degree points (34, −118), a placeholder (38.12346, −121.12346), and the CSU Northridge PD campus point.
   - Coordinates with 2 decimals or fewer: 547 more.
5. **Other off-road within a mile:** 2.9%. Highest: Thousand Oaks 18.3%, Santa Barbara 12.0%, Irvine 11.1%.

## "GPS right, names wrong"? No evidence for it as a pattern
284 difficult crashes were checked: police GPS off the report's roads but within a mile of them, 84 from the #211 audit sample and 200 at random.

In the **random sample of 200**:
- **2 (1%)** show the GPS at an intersection whose streets resemble both report names but aren't spelled the same (RANDAL AVENUE ↔ Randall Avenue; SEDCO HEIGHTS DR ↔ Sedco Heights Road). That's the only class where the GPS is right and the names are (slightly) wrong.
- **119 (60%)** agree with both: freeway crashes with the GPS on the freeway at a distance from the named cross street, or GPS at about the stated offset.
- **5** have the GPS *at* the named intersection. The **Tester's harness** missed these, because it clips each city's network to the city boundary and the intersection sits in a county pocket just outside (Fontana CHERRY AVE & HUNTER ST: GPS 19 ft away).
- **18** put the GPS at a different intersection. Nothing says the GPS is the right one.
- **49** put the GPS off any intersection: parking lots, driveways, house addresses.
- **7** sit on default points.

So the user's doubt holds. The audit's "near one road / within a mile" groups are mostly freeway crashes, offsets and wrong or off-street GPS, not wrong names.

## #215 question: is "street outside the city's clipped map" a harness artefact? Yes
Of the 71 such audit cases still difficult, **39 have the named street within the city's bounding box plus ~1 km**: county pockets and boundary streets the clipped network leaves out. Most of the rest name a city whose name CCRS uses for a county road nearby (Fresno: Millerton Rd, Academy Ave), plus a few name variants. A corridor study fetches the streets around the corridor, so it doesn't hit this.

**Proposal for run 8 (testing method, PM's call):** use the city's box plus 1 km, not the clipped outline, for both the locator and the GPS check. Label the old figure as harness-only.

1,554,835 crashes with police GPS, each in one class:

| Class | Crashes | Share |
|---|---|---|
| fits the report's streets | 1,398,658 | 90.0% |
| at the named intersection, report states an offset | 78,095 | 5.0% |
| degrees-minutes-seconds (wrong format) | 1,997 | 0.1% |
| shared default / dispatch point | 1,755 | 0.1% |
| 2 decimals or fewer | 547 | 0.0% |
| more than a mile from the named roads | 28,252 | 1.8% |
| other: off the roads, within a mile | 45,531 | 2.9% |

## By year

| Year | GPS crashes | fits the report's streets | at the named intersection, report states an offset | degrees-minutes-seconds (wrong format) | shared default / dispatch point | 2 decimals or fewer | more than a mile from the named roads | other: off the roads, within a mile |
|---|---|---|---|---|---|---|---|---|
| 2021 | 307,009 | 88.6% | 4.8% | 0.2% | 0.2% | 0.1% | 3.2% | 3.0% |
| 2022 | 299,638 | 89.0% | 5.1% | 0.1% | 0.2% | 0.0% | 2.5% | 3.0% |
| 2023 | 313,733 | 90.9% | 5.0% | 0.1% | 0.0% | 0.0% | 1.2% | 2.8% |
| 2024 | 323,580 | 90.7% | 5.1% | 0.1% | 0.0% | 0.0% | 1.1% | 2.9% |
| 2025 | 310,875 | 90.6% | 5.1% | 0.1% | 0.1% | 0.0% | 1.1% | 3.0% |

## Agencies with most GPS at the named intersection while the report states an offset (at least 500 GPS crashes)

| Agency | GPS crashes | Share |
|---|---|---|
| 1948 Monterey Park + 4 more city names (local) | 1,559 | 44.2% |
| 1923 El Segundo (local) | 648 | 39.8% |
| 4806 Vacaville (local) | 2,682 | 39.6% |
| 1969 South Gate + 5 more city names (local) | 4,117 | 39.5% |
| 1925 Glendale + 3 more city names (local) | 3,007 | 38.4% |
| 1956 Redondo Beach (local) | 1,841 | 37.5% |
| 4807 Vallejo (local) | 2,767 | 36.4% |
| 5703 Woodland (local) | 2,168 | 35.3% |
| 1955 Pomona (local) | 5,210 | 35.2% |
| 1962 San Gabriel (local) | 1,004 | 34.8% |

## Agencies with most GPS more than a mile from the named roads (at least 500 GPS crashes)

| Agency | GPS crashes | Share |
|---|---|---|
| 2802 Napa (local) | 1,389 | 34.5% |
| 3000 Mission Viejo + 13 more city names (local) | 985 | 28.1% |
| 3003 Buena Park (local) | 1,619 | 27.7% |
| 4313 San Jose (local) | 2,991 | 27.2% |
| 3602 Chino + 4 more city names (local) | 1,774 | 13.0% |
| 9170 Unincorporated (CHP) | 617 | 12.3% |
| 4006 San Luis Obispo (local) | 1,758 | 8.1% |
| 9480 Unincorporated + 10 more city names (CHP) | 13,299 | 7.9% |
| 9175 Unincorporated (CHP) | 1,261 | 7.8% |
| 9160 Unincorporated (CHP) | 1,339 | 7.2% |

## Agencies with most GPS on shared default points (at least 500 GPS crashes)

| Agency | GPS crashes | Share |
|---|---|---|
| 2401 Atwater (local) | 1,295 | 3.1% |
| 4120 Foster City (local) | 520 | 2.7% |
| 9295 Unincorporated + 5 more city names (CHP) | 2,028 | 1.8% |
| 2404 Livingston (local) | 604 | 1.7% |
| 9220 Unincorporated + 5 more city names (CHP) | 8,846 | 1.6% |
| 4109 Menlo Park + 3 more city names (local) | 1,166 | 1.5% |
| 1601 Corcoran (local) | 731 | 1.5% |
| 9245 Unincorporated (CHP) | 7,616 | 1.0% |
| 9735 Unincorporated + 5 more city names (CHP) | 1,867 | 0.9% |
| 1602 Hanford (local) | 1,690 | 0.9% |

## Agencies with most GPS in degrees-minutes-seconds (at least 500 GPS crashes)

| Agency | GPS crashes | Share |
|---|---|---|
| 4313 San Jose (local) | 2,991 | 63.2% |
| 3000 Mission Viejo + 13 more city names (local) | 985 | 6.8% |
| 340H Elk Grove (local) | 2,723 | 0.3% |
| 1900 Lancaster + 48 more city names (local) | 48,617 | 0.0% |
| 9590 Los Angeles + 16 more city names (CHP) | 36,049 | 0.0% |
| 9530 Unincorporated + 30 more city names (CHP) | 35,672 | 0.0% |
| 9550 Unincorporated + 53 more city names (CHP) | 34,836 | 0.0% |
| 9840 Riverside + 28 more city names (CHP) | 34,400 | 0.0% |
| 9525 Unincorporated + 40 more city names (CHP) | 33,598 | 0.0% |
| 9535 Unincorporated + 40 more city names (CHP) | 32,096 | 0.0% |

## Agencies with most GPS off the roads within a mile (at least 500 GPS crashes)

| Agency | GPS crashes | Share |
|---|---|---|
| 3308 Hemet (local) | 1,304 | 33.1% |
| 4310 Morgan Hill (local) | 730 | 18.8% |
| 5600 Thousand Oaks + 7 more city names (local) | 8,118 | 18.3% |
| 4203 Santa Barbara (local) | 2,924 | 12.0% |
| 3026 Irvine (local) | 2,497 | 11.1% |
| 9456 Unincorporated (CHP) | 1,760 | 8.5% |
| 9170 Unincorporated (CHP) | 617 | 8.4% |
| 3103 Lincoln (local) | 662 | 8.3% |
| 3402 Galt (local) | 614 | 8.3% |
| 3924 Lathrop (local) | 972 | 7.4% |

## Shared default / dispatch points (pooled over agencies; #218 rule)

Rule: {'min_crashes': 10, 'min_street_pairs': 5, 'max_fit_share': 0.5, 'point': 'exact to 5 decimals (~1 m)'}. 50 points, 1,828 crashes.

| Point | Crashes | Agencies | Street pairs | Years | Nearest streets | Miles from city centre |
|---|---|---|---|---|---|---|
| 38.8198, -121.0276 | 333 | 59 | 294 | 2021, 2022 | Pilot View Drive (82 ft); Pilot Peak Road (612 ft) | 6.72 (Auburn) |
| 38.59684, -121.49004 | 256 | 51 | 240 | 2025 | Signature Street (60 ft); North 7th Street (172 ft) | 2.88 (Sacramento) |
| 38.5824, -121.4954 | 225 | 59 | 202 | 2021, 2022 | 8th Street (94 ft); I Street (123 ft) | 2.33 (Sacramento) |
| 34.953, -120.4155 | 103 | 21 | 81 | 2021, 2022 | East Main Street (55 ft); Nicholson Avenue (268 ft) | 1.69 (Santa Maria) |
| 34.23992, -118.52625 | 65 | 2 | 47 | 2021, 2022, 2023, 2024, 2025 | Vincennes Street (374 ft); Bertrand Avenue (387 ft) | 6.07 (Unincorporated Chatsworth) |
| 38.12346, -121.12346 | 60 | 1 | 45 | 2021, 2022 | (no named street within ~500 ft) | 10.85 (Lodi) |
| 34, -118 | 46 | 6 | 43 | 2021, 2022, 2023, 2024, 2025 | Athel Drive (160 ft); East Oak Canyon Drive (176 ft) | 1.8 (Whittier) |
| 33, -117 | 39 | 7 | 38 | 2021, 2022, 2023, 2024 | Oak Canyon Road (388 ft) | 0.75 (Poway) |
| 38.581, -121.4946 | 37 | 17 | 33 | 2021 | 9th Street (104 ft); J Street (133 ft) | 2.23 (Sacramento) |
| 38, -121 | 32 | 3 | 29 | 2021, 2022 | Escalon Bellota Road (24 ft) | 15.24 (Escalon) |
| 33, -118 | 32 | 3 | 31 | 2021, 2022, 2023 | (no named street within ~500 ft) | 30.5 (Avalon) |
| 34, -117 | 30 | 5 | 25 | 2021, 2022, 2023 | (no named street within ~500 ft) | 2.75 (Cherry Valley) |
| 33.8942, -118.2982 | 28 | 15 | 27 | 2021, 2022 | Raymond Avenue (34 ft); Marine Avenue (162 ft) | 0.63 (Gardena) |
| 37.6093, -120.9388 | 26 | 2 | 10 | 2021, 2022, 2024, 2025 | East Hatch Road (7 ft); Mitchell Road (7 ft) | 1.74 (Ceres) |
| 34.135, -117.27642 | 26 | 1 | 21 | 2021, 2022, 2023, 2024, 2025 | East 21st Street (334 ft); North Kenwood Avenue (334 ft) | 1.75 (San Bernardino) |
| 32.77563, -117.07472 | 23 | 3 | 6 | 2021, 2022, 2023, 2024, 2025 | Canyon Crest Drive (173 ft); Scripps Terrace (221 ft) | 3.6 (Lemon Grove) |
| 33.9004, -118.0079 | 22 | 10 | 22 | 2021, 2022 | Manzanares Road (52 ft); Jalon Road (208 ft) | 0.05 (La Mirada) |
| 37.3403, -120.60938 | 20 | 1 | 9 | 2021, 2022, 2023, 2024, 2025 | Golden State Highway (935 ft); Progress Avenue (1226 ft) | 1.11 (Atwater) |
| 37.45296, -122.18172 | 19 | 1 | 16 | 2021, 2023, 2024 | El Camino Real (18 ft); Menlo Avenue (18 ft) | 1.06 (Atherton) |
| 35.7775, -120.605 | 19 | 9 | 18 | 2021, 2022 | Via Escondida (28 ft); Ranchita Vista Way (283 ft) | 9.9 (Paso Robles) |

## Re-check: "GPS right, names wrong"?

284 difficult crashes whose police GPS is off the report's roads but within a mile of them (84 from the #211 audit sample, 200 random). Evidence: the streets meeting at the GPS point and their similarity to the report's names, the distance to each named road, the stated offset, and whether the point is a default point (tests/statewide/gps_recheck.py).

| Class | All cases | Random sample |
|---|---|---|
| freeway | 128 | 87 |
| mid_block | 64 | 49 |
| offset_consistent | 43 | 32 |
| elsewhere | 25 | 15 |
| gps_at_named_intersection | 10 | 5 |
| default_point | 8 | 7 |
| cross_disagrees | 4 | 3 |
| names_misspelled | 2 | 2 |

Scripts: `tests/statewide/gps_profile.py` (`--piles`, `--profile`, `--merge`), `gps_recheck.py`, `gps_report.py`. Results in `reports/testing/gps-profile-2026-10-22/`.
