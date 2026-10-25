# California: how police capture crash GPS (CHP and city police)

Research note, 2026-10-25. Public sources only, no sign-ins. Each claim has its source. **Unconfirmed** marks
anything no public source states, including our own guesses from the data. Asked for after the user decided to keep the
officer's GPS when it fits the report's named roads (docs/03, PR #262).

## Short answer
- **CHP's own manual says GPS is the main location and the postmile is the fallback.** HPM 110.5 ch. 3 (revised April
  2021): the officer "shall enter the GPS latitudinal and longitudinal coordinates that reference the location of the
  crash", in decimal degrees to five places. The milepost fields are filled only "if GPS coordinates cannot be collected
  and all other GPS search resources have been exhausted", and are "not required for freeway on-ramps or off-ramps and
  connector roads". [1]
- **The GPS isn't always taken at the scene.** Same paragraph: GPS is "best obtained at the scene… when access is
  available. If GPS coordinates are not readily available, officers should utilize the Mobile Digital Computer; software
  applications, such as Microsoft Streets and Trips; or Web sites, such as Google Earth, upon return to their local Area
  office". So a CHP coordinate can be a live device fix *or* a point picked on a map later. The record doesn't say which. [1]
- **It is meant to be the crash point, not the patrol car**: the coordinates "reference the location of the crash". For
  run-off-road crashes the location is "the place where the vehicle left the roadway", and the coordinates "may differ
  from the actual Area of Impact". [1]
- **The written distance should be measured.** Non-intersection crashes take distance and direction from "the nearest
  permanent reference point, such as an intersecting street, overcrossing, county line". Distances are to be "measured and
  not estimated", by tape, roll meter, pacing or the patrol car's odometer, in tenths of a mile. [1]
- **City police and sheriffs fill in the same CHP 555 fields** and send them to CHP's system electronically through their
  own vendors' software, or on paper. How each agency's software captures GPS is not public for the agencies we checked.

## 1. CHP

| Question | What the sources say | Source |
|---|---|---|
| Report software | CARS (California Automated Reporting System, early 2000s) until Crash Manager, built in-house. Pilot Nov 2020, "gone live statewide" by Aug 2021. Has "the single-click ability to view GPS coordinates" and "report writing guidance to reduce data entry mistakes". | [2], [1] §1b |
| Where the lat/long comes from | Scene GPS preferred. Otherwise the in-car Mobile Digital Computer (MDC), Streets and Trips or Google Earth back at the Area office. Which device gives the "single-click" coordinate is **unconfirmed** (the in-car MDC or the laptop's GPS is likely). | [1] §19a, [2] |
| When it is taken | At the scene when possible, else when the report is written at the office. Not at dispatch, per the manual. **Unconfirmed** whether Crash Manager pre-fills from the CAD incident location. | [1] §19a |
| Car vs crash | The crash location (where the vehicle left the road, for run-off-road crashes). A one-click fix from the car would give the car's position. That is the parked patrol car's spot, usually next to the scene, so tens of metres off is expected. **Unconfirmed** how often. | [1] §14c–e, §19 |
| Car position elsewhere | CHP cars have AVL (GPS) feeding CAD (VisiNET) and the MDC. Policy GO 60.1 limits viewing it. Nothing links AVL to crash reports. | [3] |
| Reference street, distance, direction | Intersecting street, overcrossing or county line. Measured, not estimated. Directions use the "general route direction, not compass direction" (I-5 is always N/B or S/B). | [1] §14a, §21, §36 note |
| Ramps and connectors | Named from the highway of highest class. Transition roads start "with the highway the vehicle was leaving". Don't use the words "on-ramp", "off-ramp" or "connector" in the location (narrative only). | [1] §14f |
| Postmile (Milepost*) | Fallback only: route, county, postmile from the marker, plus distance and direction (e.g. `150 FEET E OF 50 SAC 5.10`). Not required on ramps or connectors. | [1] §18, [4] §47 |
| `IsLocationReferToNarrative` | No public definition. The data.ca.gov CCRS template lists it as a `Bit` with no description. The 2021 HPM ch. 3 has no "refer to narrative" box for location (it has one for owner info and vehicle defects, and says the true point of impact goes in the narrative). **Unconfirmed** what triggers it. | [5], [1] §14c, §43, §45 |
| Coordinate format | Decimal degrees, five places, e.g. `38.48381, -121.56060`. Minus sign written. | [1] §19 |

## 2. City police and sheriffs
- **Same form, same fields.** Allied agencies collect crash data "conforming to the latest version of the CHP 555" and
  send it electronically to CHP. OTS 405c (TRIP) grants pay for that software and require it to "successfully transmit
  crash reporting data to CHP SWITRS". Allied agencies join CCRS by emailing CCRS-Requests@chp.ca.gov. [6]
- **Vendors.** Crossroads Software is a common California collision system with GIS mapping and SWITRS export. Pleasanton
  says CHP names it in its guide for allied agencies; that is a city document, unconfirmed with CHP. [7], [8] Fresno and
  Downey use LexisNexis with Crossroads to publish reports. [9] Redondo Beach signed an MOU with CHP in July 2025 to send
  CHP 555 data electronically. [10] A 2018–19 CHP submission describes a web service (AARS) for any agency to submit
  crashes electronically. [11] (We read that one only through search excerpts; the PDF now returns 404.)
- **San Francisco (SFPD).** DataSF's crash data comes from SFPD's "Interim Collision System" (2018 on) and Crossroads
  (2013–17). It is "geocoded" afterwards onto the city's street centreline model, and complex intersections are "mapped
  onto a single point". [12] That fits SFPD's ~1% GPS in CCRS (`ca-ccrs.md`): the city places crashes from the street
  names, not from an officer fix. **Unconfirmed** that SFPD's system has no GPS field.
- **San Jose (SJPD).** Went live in 2007 with 3i Infotech TicketWorks on Intermec CN3 handhelds, whose forms include an
  "Accident Report". [13] The current crash software is **unconfirmed**. The city's open crash layer is keyed to an
  intersection (`INTID`, `INTASTREETNAME`/`INTBSTREETNAME`, `DISTANCE`, `DIRECTIONFROMINTERSECTION`,
  `REPORTEDLOCATIONFOUND`) and carries `TCRNUMBER`. [14] It is a possible second truth for San Jose, like DataSF.
- **LAPD, Long Beach.** No public source found for their crash software or how they capture GPS. **Open.** (LAPD's
  open data is in `la-lapd-collisions.md`.)

## 3. Known causes of the errors we see

| Error in CCRS | Public evidence | Likely cause |
|---|---|---|
| Off-road / near-miss points | Berkeley, 2009–11 California data: only 43% of officer GPS points were correct, 54.5% had a discrepancy. "Off the roadway" was the biggest error type (~20%). "Truncated coordinates" were ~7%. [15] | The car's position, or a click on a map |
| Snapped to the intersection while the report gives an offset | The manual allows a map lookup "upon return" to the office. [1] An officer clicking a named intersection on a map will land at the crossing. | Map lookup, not a scene fix. **Unconfirmed** as the cause |
| DMS written as decimal (San Jose PD, CHP areas 9370, 9675, 9252, 9550, 9530) | Kentucky: forms that expect one format while the GPS shows another (degrees-minutes-seconds vs degrees and decimal minutes) get mis-keyed. Most errors were the operator's, not the equipment's. [16] | Device set to DMS or DDM, copied into a decimal field. **Unconfirmed** for California devices |
| Missing longitude minus | Not named in any source found. The manual's example shows the minus. [1] | Hand entry. **Unconfirmed** |
| Coarse points (≤ 2 decimals) | "Truncated coordinates", ~7% in 2009–11. [15] | Hand entry, or a form/field limit |
| Shared default points | No public source. Our biggest piles (`reports/testing/gps-profile-2026-10-22.md`): 38.8198, −121.0276 near Auburn (333 crashes, 59 CHP areas) and 38.5824, −121.4954 in downtown Sacramento (225, 59 areas) appear **only in 2021–22**, Crash Manager's first statewide years [2]. The 2025 pile at 38.59684, −121.49004 is ~170 ft from North 7th Street; CHP HQ is at 601 N 7th St. [17] | A software or server default (a map's start point, an office location) saved when no fix was taken. **Unconfirmed** |

Berkeley also notes errors can enter at each step: the report, entry into the statewide database, the state-highway
reference step, and later geocoding. [18]

## 4. Why CHP stopped filling Milepost* after 2022
No public source says why. What the sources support:
1. Since at least the April 2021 manual, the postmile is a **fallback for when GPS can't be had**, and isn't required on
   ramps or connectors. [1] With GPS on almost every CHP crash, an empty postmile is the expected result.
2. CHP's new Crash Manager went statewide in 2020–21, with fields "displayed as needed based on selections made". [2]
   A guess: once a coordinate is entered, the milepost box isn't shown or required. That would explain 3.7% (2021) →
   2.3% (2022) → ~0 (2023) as the old reports (CARS) and old habits faded. **Unconfirmed.**
3. Caltrans adds the official postmile itself after a report comes in. Since CHP moved to CCRS (2015), those highway
   fields aren't returned to SWITRS, so SafeTREC checks officer GPS on state highways instead. [19] Caltrans, not the
   officer, is the postmile authority (`ca-caltrans-postmiles.md`).

To confirm: ask CHP (ITSupport@chp.ca.gov / CCRS-Requests@chp.ca.gov [6]) or file a Public Records Act request for
the Crash Manager field rules and the meaning of `IsLocationReferToNarrative`. That would be the user's step (it is
outward-facing).

## What it means for CrashIQ's GPS rules
- **Keep the GPS when it fits the named roads (the user's decision, PR #262).** The manual backs it: GPS is CHP's main
  location field, and the written distance is a measured offset from the nearest crossing. The two should agree.
- **A small disagreement is expected, not a red flag.** A fix taken from the patrol car, or the "left the roadway"
  rule, can put the GPS tens of metres from the report's spot. Our 400 ft tolerance covers that.
- **GPS sitting exactly on the reference crossing while the report gives a distance** looks like a later map click on
  the intersection, not a scene fix. Prefer the report's offset there. That is today's rule; this note gives the reason.
- **No postmile ≠ no data.** CHP's milepost is a fallback, so never treat an empty `Milepost*` as a quality signal.
  Derive postmiles from the Caltrans layer (#248).
- **Ramps and connectors:** CHP names them from the highway being left or of highest class and puts "connector" only in
  the narrative. This fits the user's 2026-10-25 decision to hold connectors for review.
- **Pile points in 2021–22 look like software defaults.** Keep treating them as no GPS (#218). A new year's piles (e.g.
  the 2025 N 7th St point) should be found by the same rule, not by a fixed list.
- **Agencies with no officer GPS (SFPD) geocode from street names** in their own systems. Their open data (DataSF, maybe
  San Jose's `crash-locations`) is the better truth for them, not CCRS lat/long.

## Open questions
1. What sets `IsLocationReferToNarrative`? (CHP; PRA request)
2. Does Crash Manager's "single-click" GPS come from the MDC, the laptop, or the CAD incident? Does it hide Milepost once GPS is filled?
3. Which crash software do LAPD, Long Beach, SJPD (today) and LASD use, and do they send coordinates?
4. Are the 2021–22 Auburn and Sacramento piles Crash Manager defaults? (A check: does the pile share drop after 2022?)
5. Is San Jose's open `crash-locations` LATITUDE the intersection or the offset point? Does `TCRNUMBER` join to CCRS?

## Sources
1. CHP, HPM 110.5 Collision Investigation Manual, ch. 3 "Instructions for completing the CHP 555, page 1", revised April
   2021, §§1b, 14, 18, 19, 21: https://www.chp.ca.gov/siteassets/policy/hpm/hpm-110.5/hpm-110.5-ch-3.pdf
2. Techwire / GovTech Insider, "State law enforcement entity refining new crash reporting system", 2021-08-16:
   https://insider.govtech.com/california/news/state-law-enforcement-entity-refining-new-crash-reporting-system
3. CHP, General Order 60.1 "Use of Automated Vehicle Locator System Data", revised July 2020:
   https://www.chp.ca.gov/siteassets/policy/go/go-60.1-use-of-automated-vehicle-locator-system-data.pdf
4. CHP, HPM 110.5 ch. 2 (definitions, §47 Milepost marker), revised April 2021:
   https://www.chp.ca.gov/siteassets/policy/hpm/hpm-110.5/hpm-110.5-ch-2.pdf
5. data.ca.gov CCRS package, "Raw Data Template" (field list): https://data.ca.gov/dataset/ccrs →
   https://publish.data.ca.gov/dataset/80c6a49d-c6b3-40ba-86d8-379c9741b4be/resource/1ec4c13e-b5b6-47df-b794-5107d4eb39ac/download/rawdata_template.docx
6. California OTS, "TRIP grants — 405c funding uses and examples" (Dec 2025):
   https://www.ots.ca.gov/wp-content/uploads/sites/67/2025/12/TRIP-One-Page-Handout.pdf
7. FHWA, Collision Database System (Crossroads Software):
   https://highways.dot.gov/safety/data-analysis-tools/rsdp/rsdp-tools/collision-database-system-crossroads-software
8. City of Pleasanton staff report (Crossroads, SWITRS export): https://weblink.cityofpleasantonca.gov/WebLink/0/doc/308624/Page9.aspx
9. Fresno ID18-1064: https://agendas.fresno.gov/en/legislation/id18-1064-7528 ; Downey:
   https://www.thedowneypatriot.com/articles/downey-police-contracts-with-lexisnexis
10. Redondo Beach council, 2025-07-15, item H.5:
    https://redondo.granicusideas.com/meetings/1255-city-council-on-2025-07-15-6-00-pm-city-council-chamber/agenda_items/687071c6f2b6704420024b57-h-dot-5-25-0914-approve-contracts-under-35-dollars-000-1
11. NASCIO 2020 award submission, CHP "Business Process — SWITRS" (read via search excerpts; now 404):
    https://www.nascio.org/wp-content/uploads/2020/09/CHP-Business-Process-SWITRS.pdf
12. DataSF via data.gov, "Traffic Crashes Resulting in Injury" metadata:
    https://catalog.data.gov/harvest_record/0dbb9f6f-ae19-4504-ac24-26c5257aad29/raw
13. SJPD / 3i Infotech press release, 2007-09-05:
    https://info.sjpd.org/records/press_release_archive/2004-2007/pdfs/Press%20Release%20-%20Citation%20Process,%20Sept%202007%20-%20Go%20Live%20v2.pdf
14. City of San José open data, "Crash Locations" (fields): https://data.sanjoseca.gov/dataset/crash-locations ;
    https://geo.sanjoseca.gov/server/rest/services/OPN/OPN_OpenDataService/MapServer/512
15. Bigham, Strang, Oum (2014), "Evaluation of the Accuracy of GPS Coordinates for Collision Locations in California",
    UC Berkeley ITS/SafeTREC: https://escholarship.org/uc/item/2kh3z760 (abstract:
    https://ideas.repec.org/p/cdl/itsrrp/qt2kh3z760.html). Full text not read (eScholarship blocks scripted download).
16. Green & Agent (2004), Kentucky Transportation Center, GPS accuracy for crash locations:
    https://uknowledge.uky.edu/ktc_researchreports/213 ; https://rosap.ntl.bts.gov/view/dot/21583
17. CHP Headquarters, 601 N. 7th Street, Sacramento: https://www.chp.ca.gov/find-an-office/headquarters/
18. Bigham & Oum (2014), "Error Consideration for Geocoding Police Reported Collision Data in California":
    https://escholarship.org/uc/item/7zv7196b
19. TIMS, SWITRS geocoding: https://tims.berkeley.edu/help/crashdata/switrs-geocoding.php
