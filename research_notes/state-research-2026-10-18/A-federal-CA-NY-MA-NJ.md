# CrashIQ state research — A: Federal layers, California, NY, MA, NJ
Compiled 2026-10-18. Every fact has its source next to it. UNVERIFIED = I couldn't confirm it.

## Federal layers

### NHTSA FARS (Fatality Analysis Reporting System)
- **Contents:** census of fatal crashes only (≥1 death within 30 days), with crash, vehicle and person files. **Access:** FARS Crash API returns XML, CSV/XLSX, JSV or JSON with no login; "FARS data starting from 2010 onwards" is in the API, and the FARS Query Tool (cdan.dot.gov/query) is there for non-developers — https://crashviewer.nhtsa.dot.gov/CrashAPI
- **Years/lag:** the 2024 annual file was first released 04/01/2026, about a 15-month lag — https://www.nhtsa.gov/file-downloads/download?p=nhtsa%2Fdownloads%2FFARS%2F2024%2FFARS2024%20Release%20Notes.txt . The 2023 file came out 04/08/2025 — https://static.nhtsa.gov/nhtsa/downloads/FARS/2023/FARS2023%20Release%20Notes.txt
- **Licence:** US federal government work, so no copyright under 17 USC 105 (general rule; I found no FARS-specific licence page). No login.
- **Geolocation:** FARS records carry LATITUDE/LONGITUD (Analytical User's Manual 1975-2024, https://crashstats.nhtsa.dot.gov/Api/Public/ViewPublication/813794). I didn't re-check field-level completeness, so the coverage % is UNVERIFIED.
- **CAN:** a fatal-crash overlay for any US corridor, and a national fallback for K counts when a state's data is gated. **CANNOT:** A/B/C/O crashes, so no KSI and no total crash profile. Small-corridor fatal counts are too sparse for screening.

### NHTSA CRSS (Crash Report Sampling System)
- A nationally representative probability sample of police-reported crashes of all severities, with only basic police-report data — https://highways.dot.gov/safety/data-analysis-tools/rsdp/rsdp-tools/crash-report-sampling-system-crss ; https://nhtsa.gov/national-center-statistics-and-analysis-ncsa/crash-report-sampling-system-crss
- **CANNOT** be used at corridor or intersection level: it's a weighted sample for national estimates, and public files have no location below PSU/region (my reading of the sample design; I didn't check CRSS location fields line by line). **CAN:** national distributions of crash types as a benchmark.

### FHWA HPMS (Highway Performance Monitoring System)
- State-reported sections covering the "HPMS-defined Federal-Aid System". Shapefiles are published by state — https://www.fhwa.dot.gov/policyinformation/hpms/shapefiles.cfm
- "HPMS Spatial All Sections – 2024" is a GeoJSON on data.gov, dataset last updated Sept 21, 2026 — http://catalog.data.gov/dataset/hpms-spatial-all-sections-2024 . It's also served on BTS NTAD (https://geodata.bts.gov/datasets/5e6a977c2d7c4ec1bdc82e684d3384f2 ; README https://rosap.ntl.bts.gov/view/dot/72253)
- **CAN:** AADT on arterials and collectors, so crash rates (per MVMT) work on federal-aid roads. **CANNOT:** reliable AADT on local roads or minor streets (local functional class isn't part of the federal-aid system, per the same FHWA page). Intersection-level minor-road volumes are almost never in it, so plan for user-entered or modeled AADT.

### MIRE / MIRE FDE (23 CFR 924)
- 23 CFR 924.11(b): "States shall have access to a complete collection of the MIRE fundamental data elements on all public roads by September 30, 2026." **Deadline CONFIRMED** in the current eCFR — https://ecfr.gov/current/title-23/chapter-I/subchapter-J/part-924/section-924.11 . I found no rule extending or rescinding it. FHWA's 2025-26 rescission notices I saw cover other parts (633, Bridges on Federal Dams, Forest Highways) — https://govinfo.gov/content/pkg/FR-2025-12-03/html/2025-21780.htm
- Opportunity: the deadline passed 18 days ago. States should now hold FDE road inventories (including AADT on all public roads, possibly modeled), but public release varies by state (UNVERIFIED per state). Caltrans MIRE FDE page: https://dot.ca.gov/programs/local-assistance/fed-and-state-programs/highway-safety-improvement-program/mire-fde

### MMUCC
- The current edition is the 6th, DOT HS 813 525, January 2024 (revised Feb 2025). It's a **voluntary** guideline — https://www.nhtsa.gov/traffic-records/model-minimum-uniform-crash-criteria ; https://www.nhtsa.gov/laws-regulations/guidance-documents
- State adoption level: UNVERIFIED. NHTSA's MMUCC mapping/alignment results by state weren't found in time. Expect field codes to differ by state, so CrashIQ needs a per-state mapping onto an MMUCC-like internal schema.
- **KABCO:** police injury severity scale (K fatal, A suspected serious, B suspected minor, C possible, O no apparent injury). It's in MMUCC's person injury-status element (same MMUCC source). KSI = K+A.

### Methods and tools
- **CMF Clearinghouse:** the full database downloads as XML, XLSX and CSV with a data dictionary, "intended for users who would like to use automated routines to regularly ingest data… into analytical tools"; last updated Nov 10, 2025 — https://cmfclearinghouse.fhwa.dot.gov/cmf_data.php . Caltrans LRSM v1.8 says the Clearinghouse holds "more than 2,900 CMFs" (CA section link). Licence: FHWA site, federal work. I found no explicit reuse terms page, so terms are UNVERIFIED, but bulk download for tools is the stated intent. Cite the CMF ID and star rating.
- **HSM:** 1st edition 2010, with a freeways/ramps supplement in 2014 — https://highwaysafetymanual.org/Pages/About.aspx
- **HSM 2nd edition (HSM2), status as of Oct 2026: not confirmed published.** AASHTO's HSM site still says it is "going through AASHTO committee reviews and is expected… in 2025" (stale). FHWA (FHWA-HRT-26-015) says it is "likely" AASHTO will publish HSM2 in 2026 — https://rosap.ntl.bts.gov/view/dot/88871 . McTrans says "expected to be completed soon" — https://mctrans.ce.ufl.edu/highway-safety-software-hss/order-hsm . Caltrans has May 2026 research notes on HSM2 implementation and Part C calibration — https://dot.ca.gov/-/media/dot-media/programs/research-innovation-system-information/documents/final-reports/task4440-rns-05-26-a11y.pdf . **UNVERIFIED whether it is on sale today.** Copyrighted AASHTO content, so CrashIQ shouldn't reproduce SPF tables without a licence.
- **IHSDM:** FHWA has **discontinued IHSDM software development** but keeps free tech support for the HSM1 transition period — https://rosap.ntl.bts.gov/view/dot/88871
- **SPICE:** FHWA's Excel tool for comparing safety performance of intersection control types in ICE (user guide FHWA-SA-18-026) — https://cmfclearinghouse.fhwa.dot.gov/collateral/FHWA-SA-18-026%20SPICE%20Tool%20User%20Guide%20(Final).pdf ; listed on FHWA ICE page https://highways.dot.gov/safety/intersection-safety/ice
- **AASHTOWare Safety (powered by Numetric):** state-DOT licences priced by group. Group 3 (CA, FL, TX, NY) pays $350k/yr for Segment, $350k for Intersection and $200k for Trend Analytics. Group 1 pays $100k/$100k/$50k. NY is in Group 3, while MA and NJ fall in Groups 1 or 2 (lists truncated) — https://aashtoware.org/products/safety/safety-ordering . Users include UT DPS, ITD (https://numetric.com/resources/replacing-public-crash-fact-sheets) and TxDOT (https://numetric.com/creating-district-safety-plans-in-crash-query).
- **Systemic:** FHWA Systemic Safety Project Selection Tool (FHWA-SA-13-019) — https://highways.dot.gov/safety/data-analysis-tools/systemic/systemic-safety-project-selection-tool . usRAP (risk-based star ratings): no official page fetched, so UNVERIFIED.

### Programs in every state
- **HSIP:** 23 USC 148 and 23 CFR 924. The rule covers program structure, planning, implementation, evaluation and reporting — https://highways.fhwa.dot.gov/safety/hsip/spm/safety-performance-management-measures-final-rules-overview . The SHSP must include implementation actions (23 CFR 924.11(c), eCFR link above).
- **VRU Safety Assessment** (23 USC 148(l), IIJA): all states finished their initial assessments in 2023. If VRU deaths are ≥15% of total, the special rule requires ≥15% of HSIP on VRU safety — https://highways.dot.gov/sites/fhwa.dot.gov/files/2024-07/HSIP%20VRU%20Fact%20Sheet_508.pdf ; https://highways.fhwa.dot.gov/safety/hsip/hsip-special-rules
- **LRSP:** FHWA Proven Safety Countermeasure. FHWA runs an LRSP DIY website — https://highways.dot.gov/safety/proven-safety-countermeasures/local-road-safety-plans ; https://highways.dot.gov/sites/fhwa.dot.gov/files/docs/multimedia/lrsp/index.html
- **SS4A Action Plan:** 7 components — leadership commitment/goal; planning structure; **safety analysis**; engagement; policy/process changes; strategy/project selection; progress/transparency. The safety analysis must establish a baseline of fatal and serious-injury crashes and look at location, severity, contributing factors and crash types, "to the extent practical… all roadways… without regard for ownership." It produces "a geospatial identification of higher-risk locations… (a high-injury network or equivalent)" — https://www.transportation.gov/grants/ss4a/comprehensive-safety-action-plans . **This is an exact fit for CrashIQ's export.**
- **ICE:** FHWA defines it as a "data-driven, performance-based framework" for screening intersection alternatives — https://highways.dot.gov/sites/fhwa.dot.gov/files/2022-06/fhwasa18076.pdf
  - State policies I confirmed: VDOT IIM-TOD-397 (https://vdot.virginia.gov/media/vdotvirginiagov/about/vdots-transportation-system/highways/innovative-intersections/iim-tod-397-icap-policy-and-guidance.pdf), WSDOT Memo 25-02 "Roundabout First" (https://wsdot.wa.gov/publications/fulltext/ProjectDev/ProjectDeliveryMemos/Memo25-02.pdf), PennDOT ICE (https://docs.penndot.pa.gov/Public/Bureaus/BOO/ICEDocs/ICE_Intro.pdf) and Caltrans ISOAP (CA section).
  - NY and MA are below. A full national count is UNVERIFIED (no FHWA state list found).
- **23 USC 407:** "reports, surveys, schedules, lists, or data compiled or collected for the purpose of identifying, evaluating, or planning the safety enhancement of potential accident sites… pursuant to sections 130, 144, and 148… shall not be subject to discovery or admitted into evidence in a Federal or State court proceeding…" — https://law.cornell.edu/uscode/text/23/407
  - **Vendor implications (my analysis, not legal advice):**
    - (1) Agencies may be reluctant to share HSIP-compiled lists (top-crash lists, HINs) and may attach §407 notices.
    - (2) CrashIQ reports built for HSIP or safety planning should carry a §407 disclaimer.
    - (3) Protection applies to data compiled *for* §148 purposes. Raw police reports obtained elsewhere may not be covered, so don't promise clients privilege.
    - (4) Expect agency DUAs (data use agreements) to prohibit litigation use and resale.
- **DPPA (18 USC 2721)** limits release and use of personal information from state motor vehicle records, which matters where crash data comes from a DMV (e.g., NY) — https://www.law.cornell.edu/uscode/text/18/2721

### Commercial / aggregator landscape
- **LexisNexis BuyCrash:** sells individual police report PDFs for participating agencies (e.g., Atlanta, Detroit). It's report retrieval, not analytics — https://risk.lexisnexis.com/products/lexisnexis-buycrash ; coverage list http://policereports.lexisnexis.com/ui/coverage
- **AASHTOWare Safety / Numetric:** state-licensed analytics, network screening and dashboards (above).
- **Citian CRASH:** AI/NLP crash analytics sold to agencies; SCAG uses it for partner cities, counties and consultants — https://citian.co/crash ; https://scag.ca.gov/sites/default/files/2025-02/tt_jan2025_part1_combined.pdf . **Closest competitor to CrashIQ's AI angle.**
- **Resale:** state terms vary. CA CCRS is public domain (below). Many state DOTs restrict crash data to safety purposes under 23 USC 407 / DPPA (e.g., CDOT states its crash database is maintained "as required by 23 U.S.C. Section 148 and 23 U.S.C. Section 405" — https://www.codot.gov/safety/traffic-safety/data-analysis/crash-data). **No general rule: check each state.** Safe model: CrashIQ processes data each user is entitled to, or uses open-licensed sources; no bulk resale.

## California baseline
- **CCRS on data.ca.gov** (CHP): public access, "Rights: No restrictions on public use", **License: Other (Public Domain)**, frequency daily. Yearly CSVs: Crashes / Parties / InjuredWitnessPassengers for **2016–2026** (Crashes_2026 updated 10/17/2026); CKAN datastore API available on data.ca.gov resources — https://data.ca.gov/dataset/ccrs ; https://data.ca.gov/@california-highway-patrol/ccrs/r/b8ce0ca4-b4e9-490d-b4d1-1f4ec48cbefb . Best-in-class for CrashIQ (commercial use permitted by public-domain designation).
- **TIMS (UC Berkeley SafeTREC)**: SWITRS-based mapping/query with SafeTREC geocoding; Sign-in/Create Account required for tools; 2025+ data flagged provisional until CHP releases the annual report — https://tims.berkeley.edu/help/crashdata/switrs.php ; https://tims.berkeley.edu/login.php . Free competitor/benchmark.
- **AADT**: Caltrans Traffic Census = "State Highway System only" — https://dot.ca.gov/programs/traffic-operations/census ; ArcGIS layer https://caltrans-gis.dot.ca.gov/arcgis/rest/services/chhighway/traffic_aadt/featureserver/0 . No statewide local-road AADT product found (UNVERIFIED that none exists; MIRE FDE program may produce one — https://dot.ca.gov/programs/local-assistance/fed-and-state-programs/highway-safety-improvement-program/mire-fde).
- **TASAS/TSN**: Caltrans internal state-highway crash/inventory system, being replaced (TSN Replacement BCP FY25-26) — https://bcp.dof.ca.gov/2526/FY2526_ORG2660_BCP7874.pdf ; https://dot.ca.gov/programs/research-innovation-system-information/office-of-highway-system-information-performance . Not public self-serve (access via request; UNVERIFIED process).
- **Local HSIP**: Cycle 13 call; **LRSM Version 1.8 (May 2026)** (crash costs in App. D updated; App. D = BCR method) — https://dot.ca.gov/-/media/dot-media/programs/local-assistance/documents/hsip/2026/lrsm2026final.pdf . LRSM text: Caltrans "established a small subset of **82 countermeasures** and a single CRF for each" that must be used (the brief's '86' NOT confirmed — numbering may include sub-items). **HSIP Analyzer** (PDF form: cost, crash input, BCR) required for all Cycle 13 applications — https://dot.ca.gov/programs/local-assistance/fed-and-state-programs/highway-safety-improvement-program/apply-now
- **LRSP requirement**: "to apply for the local HSIP funds, an agency must have completed their Local Roadway Safety Plan (LRSP) or an equivalent" + LRSP Certification template — same apply-now page.
- **ISOAP** (Intersection Safety and Operational Assessment Process; Safe System–based; replaced ICE, guide dated 2024-09-10) — https://dot.ca.gov/programs/traffic-operations/isoap ; https://dot.ca.gov/-/media/dot-media/programs/traffic-operations/documents/isoap/20240910-isoap-process-info-guide--a11y.pdf
- **ATP**: Cycle 8 (2027 ATP) ~$574M, FY27/28–30/31; CTC adopted guidelines Mar 19, 2026 — https://dot.ca.gov/programs/local-assistance/fed-and-state-programs/active-transportation-program/cycle8 ; https://mtc.ca.gov/funding/investment-strategies-commitments/climate-protection/active-transportation-program

## New York
**Crash data**
- **Owner:** NYS DMV holds crash records (AIS). NYSDOT runs **CLEAR** (Crash Location & Engineering Analysis Repository): DMV location coders and DOT batch processing geolocate crashes into a "Computed Location" table — https://www.dot.ny.gov/divisions/operating/osss/highway-repository/RedBook.pdf (Red Book, Apr 2026).
- **CLEAR access is agency-gated.** Consultants need the government client to email dot.sm.clear@dot.ny.gov with contract name and start/end dates — https://clear.dot.ny.gov/clear/apps . FHWA case study: https://highways.dot.gov/safety/learn-safety/noteworthy-practices/new-york-department-transportation-data-integration-clear . CLEAR Safety produces crash lists for investigations and replaces the TE-213 form, "including both reportable and non-reportable" crashes — https://www.dot.ny.gov/divisions/operating/osss/highway-repository/YellowBook.pdf (Yellow Book, Apr 2026).
- **ITSMR TSSR** (Traffic Safety Statistical Repository): public statistical query tool — https://www.itsmr.org/traffic-safety-statistical-repository (page timed out; details UNVERIFIED).

**data.ny.gov "Motor Vehicle Crashes" (DMV, Socrata API)**
- Tables: Case (e8ky-4vqe), Individual (ir4y-sesj), Vehicle (xe9x-a24f), plus Violations. Posted "Annually", "Most recent year's available data + 3 additional prior years" — https://data.ny.gov/Transportation/Motor-Vehicle-Crashes-Case-Information-Four-Year-W/e8ky-4vqe ; metadata via https://data.ny.gov/api/views/e8ky-4vqe.json
- Queried 2026-10-18: years **2021–2024** (2024 = 380,819 cases); rows last updated 2026-01-21. That's a ~13-month lag, and only a rolling 4-year window.
- **No lat/long.** Location fields are only county, municipality and `dot_reference_marker_location` (column list from the API metadata). **Not usable for a user-drawn corridor on local roads.**
- **Severity is not KABCO** at crash level: Fatal / Injury / Property Damage / Property Damage & Injury. Person level: Killed / Severe / Moderate / Minor / Injured with Unkn Severity / Uninjured (API query, 2024).
- The Case table shows no case ID column, so joining Case to Individual/Vehicle looks impossible from the public data (inference from the metadata; UNVERIFIED).
- `police_report` = N on 34,236 of 380,819 cases in 2024 (≈9%), i.e. motorist-only reports (API query).
- **Licence:** OPEN-NY Terms of Use. Content is "freely download[able]"; there are no attribution, share-alike or pre-approval requirements. Use it "in private sector projects" "however you wish"; the only condition is lawful use — https://data.ny.gov/download/77gx-ii52/application/pdf . **Commercial use OK.**

**Reporting threshold**
- VTL §605: a report is required if someone is injured or killed, or property damage to any one person exceeds **$1,000** — https://dmv.ny.gov/records/file-a-motorist-crash-accident-report . Non-reportable (police-only, below threshold) crashes appear in CLEAR (Yellow Book above).

**NYC Open Data "Motor Vehicle Collisions – Crashes" (NYPD, h9gi-nx95)**
- Covers every police-reported NYC collision (MV-104AN). Data are preliminary — https://data.cityofnewyork.us/Public-Safety/Motor-Vehicle-Collisions-Crashes/h9gi-nx95
- Queried 2026-10-18: 2012-07-01 to **2026-06-11**, 2,269,187 rows. **The dataset currently says it is "temporarily not updating"**; rows last updated 2026-06-15.
- Has lat/long plus on/cross street. 248,397 rows (≈10.9%) have null or 0 latitude (API count).
- Severity is only injured/killed counts by mode (no KABCO, no serious injury). Up to 5 contributing factors and vehicle types per crash.
- Companion tables: Person (f55k-p6yu) and Vehicles (bm4k-52h4). Metadata via `/api/views/<id>.json`.
- No narratives in any public NY dataset (column lists).
- **Licence:** NYC Local Law 11 of 2012 requires datasets "without registration requirement, license requirement, or usage restrictions" — https://cityofnewyork.github.io/opendatatsm/publicpolicies.html ; Terms of Use https://data.cityofnewyork.us/stories/s/Terms-of-Use/k9k7-3cje/

**AADT / inventory**
- NYSDOT Traffic Data Viewer (station AADT) — https://www.dot.ny.gov/tdv ; count portal https://nysdottrafficdata.drakewell.com/publicmultinodemap.asp . Local-road coverage is partial (UNVERIFIED %).
- Local Highway Inventory 2025: county PDF listings of municipal and county roads — https://www.dot.ny.gov/highway-data-services/lhi-local-roads

**Study formats**
- **HSIP:**
  - A **BCR is required for HSIP projects but need not be ≥1.0** — Red Book §1.2.
  - Average crash costs (Red Book Table 3): K $18,186,968; A $991,313; B $309,976; C $194,893; O $18,794; KA $2,601,585.
  - 3% discount rate; Main Office ranks capital safety projects by BCR_FI.
  - CMFs come from CLEAR Safety defaults or the **FHWA CMF Clearinghouse**, with pseudo-CMFs from SPFs allowed.
  - Methods: EB before-after; SPFs in App. C (Red Book above).
  - NYSDOT uses a hybrid state/local HSIP funding model — https://highways.dot.gov/sites/fhwa.dot.gov/files/2025-03/HSIP_Report_NEW%20YORK_2024_508.pdf (PDF wouldn't parse; snippet only).
- **Network screening:** NYSDOT Main Office screens annually with PSI and Level of Service of Safety (LOSS 1–4) to produce **Priority Investigation Locations (PILs)** and specialty KSI PIL lists. Investigations follow the Yellow Book (Red Book above). PILs are HSIP data, so 23 USC 407 applies.
- **ICE:** I found no "ICE" by that name (UNVERIFIED). HDM Ch. 5 §5.9.1 was revised to **require a roundabout alternative for major intersection projects**, with roundabouts preferred where feasible ("Roundabouts First") — https://dot.ny.gov/divisions/engineering/design/dqab/hdm/hdm-repository/rev50.pdf
- **NYC Vision Zero:** Borough Pedestrian Safety Action Plans (2023 update) set Priority Corridors, Intersections and Areas from ped KSI. Priority intersections = top ped-KSI locations making up 15% of borough ped KSI. Published as open data — https://nyc.gov/html/dot/downloads/pdf/ped-safety-action-plan-update-2023.pdf ; https://catalog.data.gov/dataset/vzv_priority-intersections
- **SS4A / LRSP:** MPO plans exist, e.g. GBNRTC RACE Safety Action Plan — https://gbnrtc.org/safety

**Competitors / state tools:** CLEAR (free to agencies and their consultants); NYC Vision Zero View; ITSMR TSSR. NYS is in AASHTOWare Safety Group 3 (pricing tier only; whether NY licenses it is UNVERIFIED).

**Verdict: MEDIUM-HARD outside NYC; EASY-MEDIUM inside NYC.**
- NYC: open and geocoded, but stalled since June 2026, with no KABCO A-level and ~11% missing coordinates.
- Rest of state: public data has no coordinates and no KABCO. Corridor-grade data sits in CLEAR, which is login-only and per-contract. Users would have to upload CLEAR exports, so CrashIQ needs a "bring your own CLEAR export" importer.

## Massachusetts
**Crash data**
- **Owner:** RMV collects state and local police crash reports. MassDOT Highway Traffic Safety geocodes them and publishes through **IMPACT** — https://mass.gov/info-details/top-crash-locations-and-maps ; portal https://apps.crashdata.dot.mass.gov/cdp/home
- **Public open data:** crash, vehicle and person filtering, downloadable "in a number of formats including spatial" (no shapefile above 2 GB; no geodatabase for open years) — https://apps.impact.dot.state.ma.us/helpcdp/topics/idh-topic110.htm ; https://apps.impact.dot.state.ma.us/helpcdp/topics/idh-topic170.htm
- **Hub:** "2002 Crashes" through "2026 Crashes" are listed on the ArcGIS Hub — https://massdot-impact-crashes-vhb.opendata.arcgis.com/ (Hub search API, queried 2026-10-18).
- **API:** ArcGIS REST FeatureServers `MASSDOT_ODP_OPEN_2021…2026`, each with Crash / Vehicle / Person layers and maxRecordCount 2000 — https://gis.crashdata.dot.mass.gov/arcgis/rest/services/MassDOT ; https://gis.crashdata.dot.mass.gov/arcgis/rest/services/MassDOT/MASSDOT_ODP_OPEN_2026/FeatureServer/0
- **Freshness (queried 2026-10-18):** the 2026 layer has 95,962 crashes, max crash datetime **2026-10-17**. Near-real-time; open years are provisional.
- **GPS:** LAT/LON and X/Y fields. 2026: IS_GEOCODED = Yes for 89,086 / 95,962 (92.8%). 2025: 127,417 / 130,931 (97.3%). MassDOT quotes ~95% geocoding that "is not uniform for all police departments" — top-crash-locations page above.
- **Severity: KABCO** (MAX_INJR_SVRTY_CL values "Fatal injury (K)" … "No Apparent Injury (O)"). Crash records also carry joined road-inventory attributes: **AADT, AADT_YEAR**, F_CLASS, lanes, speed limit, median, sidewalks, jurisdiction (field list from the FeatureServer metadata). **Unusually rich.**
- No narratives in the open data (field list).
- Login tiers: the IMPACT Log In covers advanced modules. RMV Business Partner crash-system access needs a request form — https://mass.gov/doc/crash-user-request-form/download
- **Licence:** I found no explicit open licence on the Hub items (licenseInfo blank). Only the disclaimer applies: MassDOT "makes no representation as to the accuracy… not an official record" — https://apps.crashdata.dot.mass.gov/cdp/dashboard . Commercial reuse terms: UNVERIFIED. Ask MassDOT for written confirmation.
- **Reporting threshold:** operator report required under MGL c.90 §26 for death, injury, or damage over $1,000 to any one vehicle or property — https://mass.gov/doc/motor-vehicle-crash-operator-report/download . Operator-only reports are mixed in with police reports (POLC_AGNCY_TYPE field). Share UNVERIFIED.

**AADT / inventory**
- Traffic Volume and Classification program plus TCDS (MS2) — https://www.mass.gov/traffic-volume-and-classification-in-massachusetts ; https://mhd.ms2soft.com/tcds/tsearch.asp?loc=Mhd&mod= (via https://www.acecma.org/news/massdot-traffic-count-data-collaborative/)
- Road Inventory covers all public roads (594,705 records) — https://gis.massdot.state.ma.us/roadinventory/ . AADT on local roads is sparse or derived (AADT_DERIV field); % coverage UNVERIFIED.

**Study formats**
- **HSIP eligibility:** a cluster is HSIP-eligible if its EPDO crash total is in the **top 5% of the region**. The HSIP Task Force (FHWA, MassDOT, MARPA) sets the guidelines — https://www.mass.gov/info-details/highway-safety-improvement-program
- **Published clusters:** HSIP clusters (3-year), 10-year ped/bike clusters and **Top 200 Intersection/Crash Clusters**, all on the Hub and on an interactive map — https://mass.gov/info-details/top-crash-locations-and-maps ; https://gis.massdot.state.ma.us/topcrashlocations/
- **RSA requirement:** "An RSA (or another engineering or planning report) is required for HSIP funding applications, and if all or part of your project is HSIP-eligible, an RSA is required for 25% design plans." — https://www.mass.gov/info-details/road-safety-audits ; RSA Guidelines Oct 2024 https://www.mass.gov/doc/massdot-road-safety-audit-guidelines/download . **A CrashIQ "RSA pre-read crash packet" export is a direct fit.**
- **B/C:** the MassDOT **Safety Alternatives Analysis Guide** works in three steps — no-build via SPF+EB, then MassDOT's CMF list, then monetize with "average comprehensive crash costs… documented for common facility types". It says "An alternative analysis is required" — https://www.mass.gov/doc/massdot-safety-alternatives-analysis-guide/download
  - The spreadsheet tool is available "by request" (HSIP page above).
  - Crash cost dollar values: UNVERIFIED (not extracted).
  - HSIP evaluation reports B/C and HSIP B/C by countermeasure — https://www.mass.gov/doc/2026-massachusetts-hsip-implementation-plan/download
- **ICE:** MassDOT ICE Procedure, effective **March 31, 2021**.
  - Three stages: Stage 1 screening (ICE form, optional CAP-X); Stage 2 with the ICE Tool plus the **Safety Alternatives Analysis Tool**; Stage 3.
  - Required when a project creates an intersection, adds a leg, adds lanes, etc.
  - Exempt if all minor approaches have AADT <1,000 or the State Traffic Engineer waives it.
  - Applies to municipally-led projects as well.
  - Source: https://mass.gov/doc/massdot-ice-procedure-requirements/download ; overview https://mass.gov/info-details/massdot-intersection-control-evaluation-ice
- **SS4A / LRSP:** MassDOT "Safety Action Planning Primer for Massachusetts Communities" — https://www.mass.gov/doc/safety-action-planning-primer-for-massachusetts-communities/download

**Competitors / state tools:** IMPACT (free, with dashboards and query/visualization at https://apps.impact.dot.state.ma.us/cdv); the RPAs' own analyses; MassDOT's spreadsheet tools.

**Verdict: EASY.**
- Statewide, near-real-time, KABCO, ~93–97% geocoded, with an ArcGIS REST API and AADT/inventory attributes on each crash.
- Formats are explicit (RSA, ICE, Safety Alternatives Analysis, top-5% EPDO clusters).
- Main risk: no explicit open licence, so get written confirmation on commercial reuse.

## New Jersey (lighter)
**Crash data**
- **Legacy raw tables, 2001–2018:** Crash, Driver, Vehicle, Occupant and Pedestrian tables as zipped comma-delimited TXT. They link on Year + County Code + Municipality Code + Department Case Number. **For 2019 onward, NJDOT points to its Crash Data Dashboard** — https://dot.nj.gov/transportation/refdata/accident/rawdata01-current.shtm
- **Current public portal:** NJDOT Crash Data Portal on **AASHTOWare Safety (Numetric)**, "to help the public visualize and share crash reporting information" — https://njdot.aashtowaresafety.net/njdot-crash-data-portal (via https://support.numetric.com/en/articles/13017463-njdot-crash-dashboard-overview).
- NJ DHTS has a separate Numetric crash analysis tool — https://support.numetric.com/en/articles/3779021-njdhts-crash-analysis-tool-data-documentation
- Record-level bulk download, lat/long % and licence for 2019+: **UNVERIFIED** (JS app, not tested).
- **Safety Voyager:** a "secure cloud-based crash mapping portal" combining crashes, AADT and ball-bank data, built by GPI/FHWA/NJDOT and agency-gated — https://gpinet.com/projects/safety-voyager-crash-mapping-portal ; https://highways.dot.gov/safety/learn-safety/noteworthy-practices/njdot-launches-data-driven-interactive-tool-safety-voyager . Used in SS4A plans (e.g., Union County, 2018–2022 KSI) — https://ucnj.org/safe-streets/wp-content/uploads/sites/49/2025/12/Union-SS4A_Community-Meeting-PPT-2.pdf
- **Threshold:** a reportable crash means injury or death, or property damage to any one person **over $500** (N.J.S.A. 39:4-131) — https://nj.gov/transportation/refdata/accident/pdf/NJTR-1Field_Manual.pdf . That's a lower threshold than NY/MA, so more PDO crashes are captured.
- NJTR-1 Crash Report Manual 2023 — https://nj.gov/transportation/refdata/accident/pdf/NJTR-1CrashReportManual2023.pdf . Whether it uses KABCO is UNVERIFIED (not checked).
- The open-source R package `njtr1` downloads the legacy NJDOT files — https://gavinrozzi.github.io/njtr1

**AADT / inventory**
- AADT by location and route (short-term 48-hour and continuous counts) on data.nj.gov — https://data.nj.gov/Transportation/Annual-Average-Daily-Traffic-by-Location-and-Route/dfun-zupj ; program page https://dot.nj.gov/transportation/refdata/roadway/traffic.shtm
- 2023 SLD Roadway Network covers about 12,528 miles of State, county and some other roads — https://data.nj.gov/Transportation/NJDOT-Roadway-Network/8i2w-vt9k

**Study formats**
- **Local Safety Program (LSP) and HRRRP:** projects are selected by the 3 MPOs (NJTPA, DVRPC, SJTPO) with NJDOT — https://dot.nj.gov/transportation/about/safety/lshrrrp.shtm
- **NJTPA:** sponsors "must complete Highway Safety Manual (HSM) and benefit/cost analyses as part of the application process", and roundabouts must be considered for new or upgraded intersections — https://njtpa.org/safety-improvement-program
- Projects are screened against the **NJ HSIP LSP Network Screening** lists. DVRPC built a Regional High Injury Network (2024) as a supplement — https://highways.dot.gov/sites/fhwa.dot.gov/files/2026-09/NEW%20JERSEY_HSIP%20REPORT_2025_REV_508.pdf
- HSIP Manual (2016) uses SMS lists: Intersection, Segment, Pedestrian, Fixed Object — https://dot.nj.gov/transportation/about/safety/pdf/2016hsipmanual.pdf
- NJ ICE policy: **UNVERIFIED** (none found).

**Competitors / state tools:** AASHTOWare Safety / Numetric (state-licensed, public dashboard), Safety Voyager (free to agencies). **Two state-funded tools already exist.**

**Verdict: MEDIUM.**
- Data are rich and the state already uses Numetric. Local LSP applications need HSM + B/C, which fits CrashIQ.
- Open bulk geocoded 2019+ records aren't confirmed, and Safety Voyager is gated.
- Pitch to consultants and MPO subregions as "LSP application packager", not as a data source.

## Sources
Each fact cites its URL inline; the key primary documents are linked in each section. Live API queries (Socrata for data.ny.gov and NYC; ArcGIS REST for MassDOT) run 2026-10-18 produced the counts, date ranges and geocode percentages quoted for NY, NYC and MA. Documents downloaded and text-searched: Caltrans LRSM v1.8 (May 2026), NYSDOT Red Book and Yellow Book (Apr 2026), OPEN-NY Terms of Use.
