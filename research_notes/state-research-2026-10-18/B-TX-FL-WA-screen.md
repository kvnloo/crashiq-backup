# CrashIQ state research — TX, FL, WA in depth + 9-state screen
Researched 2026-10-18. Every claim has its source next to it. **UNVERIFIED** = I could not confirm it from a primary source.

## Texas

**Crash data: who owns it and how you get it**
- Owner: TxDOT is the custodian of Texas crash records. Officers must report crashes with injury, death, or apparent damage of **$1,000+** to any one person's property, within 10 days (Transp. Code §550.062). Retention is **10 full years plus the current year**. Driver self-reports (CR-2) are no longer kept. https://www.txdot.gov/data-maps/crash-reports-records.html
- System: CRIS (Crash Records Information System), built from the officer's report (CR-3). https://www.txdot.gov/data-maps/crash-reports-records/crash-data-analysis-statistics.html
- **CRIS Query** is a public web tool to "query, extract and/or analyze publicly available crash data". You click through a disclaimer; no login was seen. https://cris.dot.state.tx.us/public/Query/app/home
  - The disclaimer says TxDOT makes no warranty, and "Any opinions and conclusions resulting from analysis… must be represented as your own and not those of the State of Texas". It does **not** prohibit commercial use. https://cris.dot.state.tx.us/public/Query/app/query-builder
- **Bulk access (Automated Extract):** one-time self-registration, then CSV extract files covering the last 10 years plus the current year.
  - The **Public extract** has all personal identifying information removed and is "available to the public upon request".
  - The **Standard extract** includes personal information. It covers state-highway-system crashes only and is limited to certain government agencies. https://www.txdot.gov/data-maps/crash-reports-records/crash-data-analysis-statistics.html
  - Files can be requested by process date, come as daily file sets, and arrive as a password-protected zip. https://www.txdot.gov/content/dam/docs/division/trf/crash-records/cris-guide.pdf
  - Registration has user categories, e.g. "Member of a Government Organization" (same guide).
  - The Public extract contains what may be released under Transp. Code §550.065 (same guide).
- **Confidentiality (§550.065):** full crash reports go only to involved or interested parties (insurers, media, etc.) or to government. Everyone else gets a redacted copy. Bulk crash reports are not provided; TxDOT supplies crash IDs for purchase instead ($6 regular, $8 certified). https://www.txdot.gov/data-maps/crash-reports-records.html
- **Licence / commercial use:** I found no explicit open licence. The terms seen are only the CRIS disclaimer (no warranty; conclusions are your own). Whether redistributing Public-extract rows inside a paid product is allowed is **UNVERIFIED**. Ask TxDOT TRF before launch.
- **Coordinates:** the City of Austin's open dataset, which is sourced from CRIS, carries "Derived Latitude/Longitude". https://data.austintexas.gov/Transportation-and-Mobility/Austin-Crash-Report-Data-Crash-Level-Records/y2wy-tgr5
  - The share of statewide CRIS records with coordinates is **UNVERIFIED**.
- **Severity:** CRIS uses a KABCO-style code: 1 incapacitating, 2 non-incapacitating, 3 possible, 4 killed, 5 not injured, 0 unknown (Austin data dictionary above). TxDOT HSIP uses "KA (Fatal and Severe)". https://www.txdot.gov/content/dam/docs/division/trf/highway-safety-engineering/hsip-guidance-program.pdf
- **Field changes over time:** some fields exist only after 03/31/2023 (e.g., Secondary Crash, Responder Struck, Autonomous Unit), others only after 12/31/2017 (CRIS Query notices). https://cris.dot.state.tx.us/public/Query/app/home
  - Separate unit and person tables in the extract are **UNVERIFIED** (the extract spec PDFs were not opened). Narratives appear only on purchasable CR-3s, not in the data.
- **Update lag:** annual reports for the prior 10 years are published by June of the following year. https://www.txdot.gov/data-maps/crash-reports-records/crash-data-analysis-statistics.html
  - The Austin open data runs at least 2 weeks behind and says some records take longer (Austin link above).
- **Known gaps:** crashes under $1,000 that are not investigated are not reported. CR-2 self-reports have been destroyed. Nothing older than the 10-year retention window is available (TxDOT page above).

**Traffic volume and road inventory**
- **STARS II** (MS2 Traffic Count Database System): traffic volumes annualized to AADT. TxDOT averages about 82,000 short-term counts a year plus about 300 permanent count sites. https://txdot.gov/inside-txdot/division/transportation-planning/stars.html ; https://txdot.gov/inside-txdot/division/transportation-planning/maps.html ; https://txdot.gov/manuals/des/tsp/chapter-3-traffic-volume-and-forecasting-/3-2-existing-traffic-volumes.html
- **Roadway Inventory (RHiNo):** published every year as GIS line work plus all attributes on the TxDOT Open Data Portal. https://www.txdot.gov/data-maps/roadway-inventory.html ; https://gis-txdot.opendata.arcgis.com/datasets/TXDOT::txdot-roadway-inventory-2023

**Study formats and methods**
- **TxDOT Traffic & Safety Analysis Procedures Manual (2024), §6.1.3.1** — this is effectively the template CrashIQ would need to follow:
  - Use **5 complete calendar years** of crash data. 3 years is the minimum; 8 years for rural, pedestrian/bike, or commercial-vehicle studies.
  - Minimum items to report: highway, year, road part, location, severity, manner of collision, crash rate vs. statewide average, segment vs. intersection, ped/bike, and contributing factors.
  - Crash-rate formulas are per 100 MVMT (segments) and per MEV (intersections).
  - Projects needing FHWA approval must request CRIS data through TxDOT TRF or Design Division.
  - https://www.txdot.gov/manuals/des/tsp/chapter-6-safety-analysis--methodologies--and-tool/6-1-safety-analysis-methods/6-1-3-existing-conditions-analysis/6-1-3-1-historical-crash-data-analysis.html
- **HSIP (2026 Guidelines)** — run centrally by TxDOT TRF, with districts as the entry point:
  - Projects are ranked by the **Safety Improvement Index (SII)**: annual savings in preventable crash costs divided by construction cost.
  - Each countermeasure maps to a **Work Code** (Appendix B lists reduction factors, service life, and maintenance cost). Preventable crashes are coded with a decoding table (Appendix C) over **3 years** of crash data. Crash costs come from National Safety Council comprehensive figures set in each program call.
  - 2026 adds an Excel submission file with an SII Calculator and a Work Code Combination Calculator.
  - Off-system projects use CRIS plus the SII calculator.
  - https://www.txdot.gov/content/dam/docs/division/trf/highway-safety-engineering/hsip-guidance-program.pdf
- **ICE:** required when an intersection involves a State route or the National Highway System, when a change of control type is possible, or when State/Federal funding is used. It follows a two-stage procedure (TSP Manual Ch. 10). https://txdot.gov/content/txdotoms/us/en/manuals/des/tsp/chapter-10-intersection-analysis/10-2-intersection-control-evaluation--ice----conte/10-2-2-ice-applicability.html ; https://txdot.gov/manuals/des/tsp/chapter-10-intersection-analysis/10-3-intersection-control-evaluation---process-and.html
- **Highway Safety Manual (HSM) / safety performance functions (SPFs):** TxDOT research produced Texas SPFs and calibration factors as spreadsheet tools (TSP Manual App. G §6). https://www.txdot.gov/manuals/des/tsp/chapter-6-safety-analysis--methodologies--and-tool/6-2-an-overview-of-predictive-safety-analysis-tool/6-2-9-local-safety-performance-functions--spf--and.html
- **Vision Zero cities:**
  - Austin runs the Vision Zero Viewer and open crash data. https://visionzero.austin.gov/viewer/
  - Houston adopted a Vision Zero Action Plan in Dec 2020 targeting 2030. https://houstontx.gov/mayor/press/2020/vision-zero-action-plan.html
  - Dallas has a Vision Zero Action Plan running through 2026. https://dallascityhall.com/departments/transportation/Pages/visionzeroplans.aspx

**Competitors and state tools**
- TxDOT already provides free CRIS Query with dashboards and clusters, plus the Texas Traffic Safety Data Portal. https://data.texas.gov/stories/s/Texas-Department-of-Transportation-Traffic-Safety-/nze5-dppu
- AASHTOWare Safety (Numetric) is configured with TxDOT KABCO costs. https://support.numetric.com/en/articles/10698209-txdot-crash-injury-severity-kabco-costs

**Verdict: MEDIUM.** The data is good: public, statewide, record-level, 10+ years, with coordinates and a bulk CSV extract after free registration. The study method is explicit and easy to automate (TSP Manual minimum items, SII/Work Codes).
- Risks:
  - The licence for commercial redistribution is unclear.
  - The bulk extract arrives as password-protected daily zips after registration, not through an open API.
  - On-system HSIP work expects TxDOT's internal reports.
  - Free CRIS Query is a capable substitute for basic counts.

## Florida

**Crash data: who owns it and how you get it**
- Owner: FLHSMV is the legal custodian and publishes the official numbers. FDOT's State Safety Office keeps its own copy, post-processed to verified locations. https://www.fdot.gov/Safety/safetyengineering/crash-data.shtm
- **Confidentiality:** reports that reveal personal information are confidential for **60 days** after filing (FS 316.066(2)(a)). That subsection sunsets Oct 2, 2027 unless re-enacted. https://www.leg.state.fl.us/statutes/index.cfm?App_mode=Display_Statute&URL=0300-0399/0316/Sections/0316.066.html
- **Long vs. short form:** a Long Form is required for death, injury or complaint of pain, hit-and-run or DUI, towaway, or a commercial vehicle. Otherwise officers fill a short form or a driver exchange form (FS 316.066(1)).
  - Short forms lack the narrative and diagram. FDOT treats crashes with **over $500 damage** as reportable. https://fdotwww.blob.core.windows.net/sitefinity/docs/default-source/safety/11a-safetyengineering/crash-data/florida-hsip-guidelines-manual6f3e1a5a378142ca861609b583b4ecf8.pdf?sfvrsn=51bf5868_0
- **Public FLHSMV download (key finding):** a quarterly-updated "aggregated crash data" zip. It is person-level, has no personal identifiers, and covers the **preceding 3 full years plus completed months of the current year** (Q1 2026 posted). Figures normalize after about 12 months. https://www.flhsmv.gov/crash-facts/
  - Its data dictionary lists **Crash Latitude/Longitude**, manner of collision, maximum severity, and vehicle and person keys with person injury severity. Dictionary downloaded and read: https://www.flhsmv.gov/wp-content/uploads/Automated%20Crash%20Facts%20Report%20Dict.xlsx
- **Signal Four Analytics (S4, UF GeoPlan):** now "FDOT's official crash data repository" after merging with CAR. It has FDOT-verified locations, state and local roads, Roadway ID/milepost, and ped/bike crash typing. https://fdotwww.blob.core.windows.net/sitefinity/docs/default-source/safety/11a-safetyengineering/crash-data/signal-4-analytics-announcement---v4.pdf?sfvrsn=420f7485_1
  - **Access:** login only, for public agency employees. FDOT says consultants can be approved through an FDOT project manager. https://signal4lab.geoplan.ufl.edu/signal4analytics ; https://www.fdot.gov/Safety/safetyengineering/crash-data-systems-and-mapping
  - Data arrives nightly from FLHSMV, and agencies take up to 90 days to report. https://www.fdot.gov/Safety/safetyengineering/crash-data-systems-and-mapping
- **CAR (legacy):** restricted access. Fatal and serious-injury crashes get location verification within about a week; other crashes take about 10 months (same page).
- **Public FDOT GIS:** the SSOGis query tool returns at most 5,000 records. The public `sso/ssogis` MapServer has per-year crash layers for **2007–2024**. https://fdotewp1.dot.state.fl.us/ssogis/home.aspx ; https://gis.fdot.gov/arcgis/rest/services/sso/ssogis/MapServer
  - The `Crashes_All` service has 157 fields, including FDOT and officer lat/long, highest injury (INJSEVER), and K/serious/injured counts. My live queries returned intermittent 500 errors, and 2024 returned 0 rows, so its currency is **UNVERIFIED**. https://gis.fdot.gov/arcgis/rest/services/Crashes_All/MapServer/0
- **Licence / use terms:** FDOT safety products carry a 23 USC 407/409 notice: "shall be used only for the purposes deemed appropriate by FDOT" (SSOGis page above). FLHSMV's download has no stated licence. Commercial redistribution is **UNVERIFIED**; Florida's public-records law suggests it is permissive, but no source was found.
- **Severity:** KABCO. FDOT publishes KABCO crash costs in FDM Table 122.6.2, updated for 2026. https://fdotwww.blob.core.windows.net/sitefinity/docs/default-source/traffic/trafficservices/studies/muts/muts-2026/teo_2026_muts_bulletin_25-03.pdf?sfvrsn=3f69bc08_1
- **Report pages:** Event, Vehicle, Person, Narrative, Diagram (Florida Uniform Traffic Crash Form Manual). https://www.flhsmv.gov/pdf/courts/crash/crashmanualcomplete.pdf

**Traffic volume and road inventory**
- **Florida Traffic Online** (2025 data) and an ArcGIS REST AADT layer. https://tdaappsprod.dot.state.fl.us/fto/ ; https://gis.fdot.gov/arcgis/rest/services/FTO/fto_PROD/MapServer/7
- **RCI** (Roadway Characteristics Inventory) feature services. https://gis.fdot.gov/arcgis/rest/services/RCI_Layers/FeatureServer
- **FLARIS** (all-roads network) via SSOGis (link above).

**Study formats and methods**
- **HSIP Guidelines:** FDOT-administered for all public roads, with analysis through the CRASH application. FDOT strongly recommends its own location-verified crash data and **3–5 years** of data; HSM methods are promoted. https://fdotwww.blob.core.windows.net/sitefinity/docs/default-source/safety/11a-safetyengineering/crash-data/florida-hsip-guidelines-manual6f3e1a5a378142ca861609b583b4ecf8.pdf?sfvrsn=51bf5868_0
  - Local projects are delivered through the Local Agency Program (LAP). https://fdotwww.blob.core.windows.net/sitefinity/docs/default-source/fpo/project-management/pmg/pmg-430-local-agency-program.pdf?sfvrsn=d7df6e79_1
- **FDOT Manual on ICE** (Topic 750-010-003, rev. Nov 2021):
  - Stage 1 screening uses the FDOT ICE spreadsheet, CAP-X, and SPICE crash prediction.
  - Stage 2 is a form plus supporting analysis (Synchro, SPICE, and a Safe System SSI score).
  - https://fdotwww.blob.core.windows.net/sitefinity/docs/default-source/traffic/trafficservices/studies/muts/muts-2022/2022-fdot-ice-manual.pdf?sfvrsn=8f36f2f4_4
- **Safety Analysis Guidebook for PD&E** (under the HSM Implementation Policy 000-500-001, May 2016):
  - Calls for HSM predictive methods and Empirical Bayes using SPFs calibrated to Florida.
  - S4 is the crash source (access needs GeoPlan permission).
  - https://fdotwww.blob.core.windows.net/sitefinity/docs/default-source/environment/pubs/pd-amp-e-studies-safety-analysisguidebook_-08222019.pdf?sfvrsn=7960a800_2 ; https://trid.trb.org/view/1765266
- **Local Road Safety Plans (LRSPs) and Vision Zero:**
  - Palm Beach County LRSP. https://rosap.ntl.bts.gov/view/dot/55609
  - Orlando's Vision Zero goal is 2040. https://www.orlando.gov/Initiatives/Vision-Zero
  - MetroPlan Orlando has a regional Vision Zero Central Florida action plan. https://metroplanorlando.gov/wp-content/uploads/VZCF_ActionPlanUpdate_FINAL.pdf

**Competitors and state tools**
- Signal Four Analytics is free to agencies and includes corridor selection, crash summaries, collision diagrams, and network screening. https://www.fdot.gov/Safety/safetyengineering/crash-data-systems-and-mapping
- This is the strongest state-built competitor of the three states.

**Verdict: MEDIUM (data easy, market contested).** The public FLHSMV quarterly download has lat/long and person-level records but only about 3 rolling years. FDOT GIS layers reach back to 2007 with verified locations.
- Risks:
  - FDOT/PD&E work expects S4's verified locations and HSM/SPICE outputs.
  - S4 already delivers corridor summaries and collision diagrams for free.
  - The 23 USC 409 notice and unclear licence add caution.
- Best niche: private-sector traffic impact study (TIS) work for developers' consultants who lack S4 access, and SS4A/LRSP plans.

## Washington

**Crash data: who owns it and how you get it**
- Owner: WSDOT's Crash Data & Reporting Branch. Records are built from Police Traffic Collision Reports (PTCRs), plus fields derived from the officer's narrative and diagram (collision type, object struck, junction relationship). WSP sells individual reports through WRECR.
  - Retention is **15 full years plus the current year**. Data is not final until **July of the following year**. https://wsdot.wa.gov/about/transportation-data/crash-data ; https://wsp.wa.gov/driver/collision-records
- **Crash Data Portal** (public, no login): dashboards and map covering **10 full years plus the current year**. Only records with X/Y coordinates are plotted. https://remoteapps.wsdot.wa.gov/highwaysafety/collision/data/portal/public/
  - A record-level bulk download or API from the portal is **UNVERIFIED**; I saw only summaries and a map.
- **Record-level data comes by request:** email Form 780-032. "There are no restrictions on who can request the data." Turnaround averages 10 days. Outputs are a "history report" (per crash) or a summary, in Excel or PDF.
  - Non-WSDOT consultants, citizens, attorneys, and media go through the Public Disclosure Request Center. https://wsdot.wa.gov/sites/default/files/2026-04/Crash-Data-FAQ-s.pdf ; https://wsdot.wa.gov/sites/default/files/2026-04/Crash-Data-Request-Form_0.pdf ; https://wsdot.wa.gov/about/transportation-data/crash-data
- **Use restriction:** every release carries a **23 USC 148 / 23 USC 407** notice. The data cannot be used in discovery or as evidence in damages actions (FAQ above).
  - WSDOT explains this "Section 409" protection travels with data shared with safety agencies. https://wsdot.wa.gov/sites/default/files/2021-10/WSDOTAssistancetoLocalGovernmentsbyProvidingCrashD.pdf
  - RCW 46.52.080 makes the reports themselves confidential, apart from limited disclosure to interested parties. https://app.leg.wa.gov/rcw?cite=46.52.080
  - Commercial redistribution is **UNVERIFIED**: no licence is stated, and the 409 notice is the main constraint.
- **Coverage:** all public roads, including city streets and county roads. Ped/bike crashes are generally received only when a motor vehicle is involved. https://wsdot.wa.gov/sites/default/files/2026-04/Crash-Data-FAQ-s.pdf ; https://wsdot.wa.gov/sites/default/files/2021-10/WSDOTAssistancetoLocalGovernmentsbyProvidingCrashD.pdf
- **Severity:** the data carries severity; the program focus is fatal and serious injury (City Safety call). Whether WSDOT's coding is exact KABCO is **UNVERIFIED**.
  - Seattle's open dataset uses 3 fatal, 2b serious, 2 injury, 1 property damage, 0 unknown. It runs 2004–present and updates weekly. https://www.seattle.gov/Documents/Departments/SDOT/GIS/Collisions_OD.pdf ; https://data.seattle.gov/dataset/SDOT-Collisions-All-Years/sbqc-3j3m
- The share of statewide records with coordinates is **UNVERIFIED**; the portal says only coordinate-bearing records are mapped.

**Traffic volume and road inventory**
- WSDOT Traffic Counts (AADT, 2025) and Traffic Sections are on the WA Geospatial Open Data Portal. https://geo.wa.gov/datasets/WSDOT::wsdot-traffic-counts-aadt-current/about ; https://geo.wa.gov/datasets/WSDOT%3A%3Awsdot-traffic-sections-aadt-current/about
- These cover state highways only. Local counts come from cities and counties; Seattle publishes its own traffic-volume dashboards. https://www.seattle.gov/transportation/permits-and-services/interactive-maps/traffic-volume-and-crash-data

**Study formats and methods**
- **HSIP split:** 30% WSDOT and 70% local agencies, based on Target Zero Priority One areas (lane departure, intersections). Local money flows through the **City Safety Program** and **County Safety Program**, including high-risk rural roads and about $2M per biennium for Safe Routes to School. Projects follow Target Zero and each agency's **local road safety plan**. https://wsdot.wa.gov/business-wsdot/support-local-programs/funding-programs/highway-safety-improvement-program
  - The 2026 City Safety call closed March 6, 2026. https://wsdot.wa.gov/business-wsdot/support-local-programs/funding-programs/highway-safety-improvement-program/highway-safety-improvement-program-call-projects
  - Applicants order a special City Safety layout from WSDOT: an Excel file plus a PDF map of fatal and serious-injury crashes. https://wsdot.wa.gov/sites/default/files/2026-04/2026-City-Safety-Program.pdf
- **LRSP 7-step template:** analyze summary crash data, analyze individual fatal/serious crashes, select common risk factors, screen the network, prioritize locations, pick countermeasures, list projects. This is a systemic method based on FHWA's Systemic Safety Project Selection Tool. https://wsdot.wa.gov/sites/default/files/2021-10/LP-Local-Road-Safety-Plan.pdf ; https://wsdot.wa.gov/sites/default/files/2023-03/LocalRoadSafetyPlan-Template-Feb2023.pdf
- **ICE / roundabout first:** Project Delivery Memo 25-02 (7/8/2025) rewrote Design Manual §1300.05.
  - "Roundabouts are the preferred intersection control type on state highways."
  - There are two types, Simplified ICE and standard ICE, with separate vehicle safety and active-transportation safety assessments.
  - Analysis uses HSM predictive methods, CMFs, and societal cost.
  - The ICE must be prepared under a licensed PE.
  - https://wsdot.wa.gov/publications/fulltext/ProjectDev/ProjectDeliveryMemos/Memo25-02.pdf ; https://wsdot.wa.gov/publications/manuals/fulltext/m22-01/1300.pdf
- **HSM:** Design Manual Ch. 321 and the WSDOT Safety Analysis Guide cover safety analysis policy. https://wsdot.wa.gov/publications/manuals/fulltext/M22-01/321.pdf ; https://wsdot.wa.gov/publications/fulltext/design/ASDE/Safety-Analysis-Guide.pdf
  - WSDOT-specific SPF calibration details are **UNVERIFIED**; the guide was not read in depth.
- **Vision Zero:** Seattle publishes open crash data and dashboards (links above). Target Zero is the statewide plan, with a 2030 goal per Memo 25-02.

**Competitors and state tools**
- The WSDOT Crash Data Portal is free.
- WSDOT supplies custom City Safety crash packages on request.
- Commercial: **UNVERIFIED**; no WA-specific vendor was found in this time box.

**Verdict: MEDIUM-HARD for automation, EASY for fit.** The study model (LRSP/systemic, City/County Safety, ICE) closely matches CrashIQ's report types. But statewide record-level data needs a manual email or public-disclosure request (about 10 days), with no API seen, and every release carries a 409 notice.
- Realistic path: users upload their own WSDOT history report, plus native ingestion of Seattle-style city open data.

## Screen
Population figures are 2020 Census resident counts, quoted from memory of the Census apportionment table and **not re-fetched**. Verify before use: https://www.census.gov/data/tables/2020/dec/2020-apportionment-data.html

**Pennsylvania (pop. about 13.0M)**
- **PCIT** (PennDOT Crash Information Tool) is public, with featured reports and dashboards. https://crashinfo.penndot.pa.gov/PCIT
- **Record-level public download:** annual crash spreadsheets for **2006–2025**, by statewide, county, district, or planning partner. No login was seen. https://experience.arcgis.com/experience/51809b06e7b140208a4ed6fbad964990
- The 2026 data dictionary lists **DEC_LATITUDE / DEC_LONGITUDE**, MAX_SEVERITY_LEVEL, and "Suspected Serious" (KABCO). https://gis.penndot.pa.gov/gishub/crashZip/Crash_Data_Dictionary_2026.pdf
- Licence and commercial-use terms: **UNVERIFIED** (no licence text on the download page).
- Study rules: PennDOT ICE Policy (Jan 2018). https://docs.penndot.pa.gov/Public/Bureaus/BOO/ICEDocs/ICE_Intro.pdf ; https://docs.penndot.pa.gov/Public/Bureaus/BOO/TSPortal/ICE.html
- **Fit: very high.** Open, bulk, geocoded, and 20 years deep.

**Ohio (pop. about 11.8M)**
- **GCAT** (GIS Crash Analysis Tool) is for "ODOT, MPOs, city/county engineers, law enforcement agencies, and pre-qualified safety study consultants", by access request. It was expected to move to AASHTOWare Safety in late 2025. https://dam.assets.ohio.gov/image/upload/transportation.ohio.gov/safety/highway-safety/Crash-Analysis-Tools/gcat/Get_GCAT_Access.pdf ; https://transportation.ohio.gov/traveling/safety/manuals/safety-analysis-guidelines-cf/0700
- ODPS Crash Retrieval lets the public search individual OH-1 report copies, labelled "not official documents". https://ohtrafficdata.dps.ohio.gov/crashretrieval
- A public record-level bulk download with coordinates is **UNVERIFIED**. The TIMS data page offers downloads, but its dataset list did not render. https://tims.dot.state.oh.us/tims/data
- 23 USC 409 protection notice on GCAT (same PDF).
- Study rules: a strong HSM culture. ODOT Safety Analysis Guidelines and the **ECAT** benefit-cost tool. https://transportation.ohio.gov/wps/portal/gov/odot/traveling/safety/manuals/highway-safety-manual ; https://highways.dot.gov/safety/learn-safety/noteworthy-practices/ohio-economic-crash-analysis-tool-ecat-supports-benefit
- **Fit:** large consultant market, but the best data sits behind a login.

**Virginia (pop. about 8.6M)**
- **Open record-level data** on Virginia Roads / data.virginia.gov: CSV, Excel, and an ArcGIS GeoService. "CrashData Details" has 63 columns and 1,076,099 rows; the metadata was modified 2026-07-29. https://data.virginia.gov/dataset/crash-data ; https://data.virginia.gov/dataset/c1e3821e-bf9f-4458-b32c-c1903380a1fa/resource/abb1056f-660b-4908-98c4-1d4e1371637f
- Source is DMV TREDS. VDOT publishes the "non-privileged" data under a DMV data-sharing agreement (same page).
- **Terms:** a 23 USC 407 notice, and users must comply with the federal Driver's Privacy Protection Act (DPPA), the Va. Government Data Collection Act, and DMV dissemination rules. No commercial-use ban is stated, but this is **not an open licence**, so legal review is needed. https://www.arcgis.com/sharing/rest/content/items/1a96a2f31b4f4d77991471b6cabb38ba?f=json
- Year range and coordinate fields: **UNVERIFIED**. My ArcGIS query of the service failed ("Invalid URL").
- Study rules: **VJuST/iCAP** ICE policy (IIM-TOD-397). https://vdot.virginia.gov/media/vdotvirginiagov/about/vdots-transportation-system/highways/innovative-intersections/iim-tod-397-icap-policy-and-guidance.pdf ; https://vdot.virginia.gov/about/our-system/highways/innovative-intersections/virginia-icap
- **Fit: high.** Open portal with an API, and a mature ICE policy.

**Michigan (pop. about 10.1M)**
- **MTCF** (Michigan Traffic Crash Facts, run by UMTRI): a public Data Query Tool with **2004–2025** data and crash map, list, and table views. New years are added when Michigan State Police close each year. https://www.michigantrafficcrashfacts.org/
- Query tool views include List, Crash Map, and Crash Reports. https://www.michigantrafficcrashfacts.org/data/querytool/
- A bulk CSV export with coordinates and the licence terms are **UNVERIFIED**.
- Study rules: MDOT Local Safety Program (HSIP, HSIP Systemic, HRRR). FY2028 call letter; submittal form 1627. https://www.michigan.gov/mdot/-/media/Project/Websites/MDOT/Business/Local-Government/Local-Agency-Program/Special-Funding-Program/Safety-Program/Application-Process/FY28-HSIP-HRRR-Call-Letter.pdf ; https://mdotjboss.state.mi.us/webforms/GetDocument.htm?fileName=1627.pdf
- **Fit:** good public query access, but the export path is unknown.

**Colorado (pop. about 5.8M)**
- **Statewide Crash Data Listing for 2007–2026** is posted as public downloads, with data dictionaries for 2007–2020 and 2021–2026. 2021–2026 data is subject to revision. https://www.codot.gov/safety/traffic-safety/data-analysis/crash-data
- All listings are "protected under 23 U.S.C. Section 407". More specific data comes by open-records request (Excel) (same page).
- Coordinates: in the DRCOG regional crash data consortium, **16% of records were missing lat/long in 2022**. https://drcog.org/sites/default/files/acc/TPO-GF-25FEB18RTCATTACHE-EN-ACC-25-02-10-V1.pdf
  - Statewide coordinate share: **UNVERIFIED**.
- Study rules: annual HSIP local-agency funding notices; 46 applications from 26 agencies in the 2025 report. https://highways.dot.gov/sites/fhwa.dot.gov/files/2026-09/COLORADO_HSIP%20REPORT_2025_508.pdf
- **Fit: high on data, smaller market.**

**North Carolina (pop. about 10.4M)**
- **TEAAS** (Traffic Engineering Accident Analysis System): downloadable software, free to "state government personnel, municipalities, law enforcement agencies, planning organizations, and research entities". It holds all reportable crashes since 1990, with data through January 2026. https://connect.ncdot.gov/resources/safety/TrafficSafetyResources/Traffic%20Engineering%20Accident%20Analysis%20System%20(TEAAS).aspx
- Private consultant and public bulk access: **UNVERIFIED**; it appears government and research only.
- Crash report images are on DMV CrashWeb, with personal information protected by law. https://connect.ncdot.gov/resources/safety/Crash%20Data%20and%20TEAAS%20System/TEAAS/DMV%20CrashWeb%20Information.pdf
- Public products are county and city rankings and crash profiles. https://ncdot.gov/initiatives-policies/safety/traffic-safety/Pages/City-County-Resources.aspx
- Study rules: HSIP **safety warrants and Spot Safety Index**. https://highways.dot.gov/safety/hsip/hsip-noteworthy-practice-series-hsip-project-identification/safety-warrants-and-spot
- **Fit:** medium market, restricted data.

**Illinois (pop. about 12.8M)**
- **IDOT Safety Portal:** you create an account, must be **vetted by your County Engineer**, then IDOT approves. It gives crash map locations, report images, 10-year retention, and summary reports. Other data is by email request. https://idot.illinois.gov/content/dam/soi/en/web/idot/documents/transportation-system/bulletins-and-circulars/circular-letters/informational/cl-2025-11-crash-data-final.pdf
- History: in 2015 IDOT had stopped, then resumed, fulfilling non-government requests. https://chi.streetsblog.org/2015/11/03/idot-finally-sees-the-light-stops-withholding-crash-data-from-the-public
- No public record-level download was found.
- Study rules: HSIP Benefit-Cost Tool and a local HSIP funding notice (FY28 NOFO). https://idot.illinois.gov/content/dam/soi/en/web/idot/documents/transportation-system/manuals-guides-and-handbooks/safety/hsip-benefit-cost-tool-user-guide.pdf ; https://idot.illinois.gov/content/dam/soi/en/web/idot/documents/transportation-system/bulletins-and-circulars/circular-letters/informational/cl-2026-07-fy28-local-hsip-nofo.pdf
- **Fit: low on data openness.**

**Georgia (pop. about 10.7M)**
- **GEARS** (Georgia Electronic Accident Reporting System) is built and maintained by LexisNexis Risk Solutions for GDOT. https://www.gahighwaysafety.org/traffic-records-data-data-sources/
- **GDOT Crash Data Dashboard** (AASHTOWare Safety/Numetric): public, no account, covers the **past 5 years**, with mapping and filters. Custom data comes by email, usually within 5 business days. https://crashmanual.dot.ga.gov/data ; https://support.numetric.com/en/articles/4606870-gdot-crash-data-dashboard-overview
- A record-level CSV export from the dashboard and its licence: **UNVERIFIED**.
- Study rules: GDOT **ICE Policy** (Stage 1 / Stage 2, ICE Decision Record). https://www.dot.ga.gov/PartnerSmart/DesignManuals/Intersection%20Control%20Evaluation/ICE_Policy_Appendices.pdf
- **Fit:** medium. Strong ICE demand; data access is via dashboard or email.

**Arizona (pop. about 7.2M)**
- Public products are annual Crash Facts PDFs for 2006–2024. Crash data otherwise requires the **Public Record Center**. https://azdot.gov/planning/traffic-safety/arizona-motor-vehicle-crash-facts
- The "AZ Traffic Safety Data" SHSP dashboards cover 2016–2025 KSI. https://experience.arcgis.com/experience/a7711f17055a4e9dab845577a13e737f
- ACIS access and terms: **UNVERIFIED** (no official page found).
- Study rules: ADOT HSIP Manual Appendix A worksheets (Oct 2023). https://azdot.gov/sites/default/files/2023-12/HSIP-Appendix_A-Rev-Oct23.pdf
- **Fit: low on data openness.**

## Ranking
*Recommendation only.* Order for adding after CA, NY, TX, WA, MA. Weighs data openness (record-level, coordinates, no login, commercial use), market size, and similarity to the CA study model.
1. **Pennsylvania:** public 2006–2025 record-level downloads with decimal lat/long and KABCO, no login, large market, ICE policy. Closest to CA CCRS.
2. **Virginia:** open portal with CSV and API (about 1.08M rows). DPPA and 407 conditions need legal review; VJuST/iCAP ICE fits the ICE export.
3. **Colorado:** public statewide listings for 2007–2026, but a smaller market and some coordinate gaps (16% missing in DRCOG 2022).
4. **Michigan:** public MTCF query tool for 2004–2025 with maps; confirm bulk export and terms before committing.
5. **Georgia:** large market and strong ICE policy, but data is a 5-year dashboard plus email requests.
6. **Ohio:** large, HSM-mature market (ECAT), but the core crash data (GCAT/AASHTOWare) is login-gated.
7. **North Carolina:** TEAAS is government and research only; public data is mostly aggregated.
8. **Arizona:** records only via the Public Record Center; public material is PDFs and dashboards.
9. **Illinois:** Safety Portal requires County Engineer vetting, and IDOT has a history of restricting non-government requests.

## Sources
Every source URL appears inline, next to the fact it supports.

Gaps not covered in the time box, all marked UNVERIFIED in the text:
- TxDOT extract file specs (unit/person tables).
- WSDOT bulk export and SPF details.
- VA year range and coordinate fields.
- MI/GA export paths.
- Commercial-use licences in every state.
- Statewide coordinate percentages.
