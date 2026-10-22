# #199 correction: police-GPS check inside cities (2026-10-22)

Found by the Tester in the #211 audit. The GPS check in `tests/statewide/citywide.py` (`City.keys`) looked up only the exact-name streets whenever any existed in the city. GPS on a stretch mapped under a variant of the name ("West Foothill Boulevard" next to "Foothill Boulevard") was therefore called "off the report's roads". Example: Upland, FOOTHILL BLVD & CAMPUS AVE, GPS 6 m from both roads. The fix returns exact **and** same-core streets, the locator's own relaxed lookup. `tests/statewide/coverage_gpsfix.py` re-ran only the GPS step for every #199 crash inside a city map that has police GPS and wasn't placed by it. Outside cities the check (`fatal.road_match`) is unchanged.

Same basis: CCRS mirror 2026-10-19, OSM 2026-10-18, app code 5f54c02 (the locator itself is not involved in this step). Completeness: 2,057,508 crashes before and after.

| Moved | Crashes |
|---|---|
| review → police GPS | 9,975 |
| can't place → police GPS | 6,516 |
| CrashIQ exact → police GPS (bin unchanged) | 154 |
| FARS → police GPS (bin unchanged) | 6 |
| can't place → police GPS (DMS) | 6 |
| CrashIQ exact → police GPS (DMS, bin unchanged) | 2 |
| **total re-classified** | **16,659** (16,497 out of bin 2) |

| Statewide | Before | After |
|---|---|---|
| On the map % | 85.3 | 86.1 |
| Difficult % | 14.7 | 13.9 |
| Police GPS % | 71.1 | 71.9 |
| CrashIQ placed % | 14.2 | 14.2 |
| Fatal on the map % | 94.5 | 95.2 |
| KSI on the map % | 85.5 | 86.1 |

| District | On the map before | After |
|---|---|---|
| District 1 | 94.4 | 94.5 |
| District 2 | 88.4 | 88.4 |
| District 3 | 92.1 | 92.2 |
| District 4 | 89.6 | 89.7 |
| District 5 | 88.6 | 89.0 |
| District 6 | 86.6 | 87.6 |
| District 7 | 80.1 | 81.2 |
| District 8 | 85.2 | 86.4 |
| District 9 | 93.9 | 93.9 |
| District 10 | 91.2 | 91.7 |
| District 11 | 83.3 | 83.5 |
| District 12 | 79.8 | 82.2 |
| unknown | 23.7 | 23.7 |

| Road type | Before | After |
|---|---|---|
| city street | 75.0 | 76.3 |
| freeway | 94.7 | 95.2 |
| county road (outside cities) | 96.6 | 96.6 |
| state highway (off freeway) | 87.1 | 87.3 |

Biggest city changes (by crashes moved):

| City | Crashes | Before | After |
|---|---|---|---|
| Los Angeles | 142,519 | 69.5 | 71.1 |
| Santa Ana | 23,097 | 79.9 | 86.5 |
| Rialto | 7,308 | 60.0 | 79.8 |
| Anaheim | 23,870 | 72.6 | 78.5 |
| West Covina | 6,548 | 74.0 | 85.3 |
| Fresno | 25,229 | 83.5 | 86.1 |
| Alhambra | 4,552 | 75.9 | 87.3 |
| Stockton | 22,944 | 87.7 | 89.7 |
| Pomona | 12,742 | 81.5 | 85.1 |
| San Bernardino | 12,841 | 80.6 | 84.0 |
