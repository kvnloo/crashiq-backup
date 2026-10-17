# Crash / Safety Analysis Software Landscape (as of Oct 2026) — for CrashIQ positioning

Scope: commercial and public tools that traffic engineers, agencies and consultants use for crash/safety analysis, who buys them, public pricing, pain points, and whether anything auto-generates study-ready safety sections or HSIP applications (California focus). Research date: 2026-10-17. Pricing is reported only where a primary or procurement source shows it; otherwise "not public."

---

## 1. Products: what they do (by category)

### Takeaway
The market splits into (a) statewide HSM/network-screening platforms sold to DOTs (Numetric/AASHTOWare Safety), (b) older local crash-records and collision-diagram tools (Crash Magic, Crossroads, TIMS, TES), (c) "big data" exposure/behavior platforms that have added safety modules and, in 2026, LLM agents (INRIX Compass, Replica+Arity Safety Hub, StreetLight, Urban SDK, Iteris ClearGuide), and (d) video/lidar near-miss analytics (Miovision, Derq, Transoft TrafxSAFE, Ouster BlueCity). Citian's CRASH, deployed for SCAG in Southern California, comes closest to CrashIQ's concept: AI cleanup, collision diagrams, countermeasures and grant-ready outputs.

### Cited Findings

**Statewide / HSM platforms**
- Numetric is described as a "configurable, cloud-based traffic safety analytics platform" that transforms, integrates and QA's crash, asset, LRS, citation and roadway data. Its apps are Network Screening (HSM rankings, downloadable report), Safety Analysis (countermeasure mix to maximize B/C), Project Design (concept cost estimates), Crash Query ("query using natural language", downloadable Crash Report), Asset/Citation Query, and Workbooks (custom dashboards plus public portals). — [FHWA RSDP: Numetric](https://highways.dot.gov/safety/data-analysis-tools/rsdp/rsdp-tools/numetric)
- Numetric was started by engineers from Utah DOT. — [Numetric About](https://numetric.com/about-us/)
- AASHTOWare Safety "powered by Numetric" is the co-branded replacement for AASHTOWare Safety Analyst, which was sunset in July 2022. — [Numetric](https://numetric.com/aashtoware-safety-replacing-safety-analyst); [AASHTO Journal](https://aashtojournal.transportation.org/aashtoware-numetric-form-safety-software-alliance)
- FY2027 AASHTOWare Safety modules are Segment Analytics (Crash Query, Safety Analysis, Network Screening, Predictive Analysis), Intersection Analytics (which adds Collision Diagrams), Trend Analytics (public dashboards) and Alternative Design. — [AASHTOWare FY2027 Catalog, pp. 51–57](https://www.aashtoware.org/wp-content/uploads/2026/06/FY-2027-AASHTOWare_Catalog_web.pdf)
- Arizona DOT's 2025 Project Investment Justification says ADOT had been "utilizing free modeling tools, some of which have to be adapted," and that "16 states are already using Numetric." — [AZ ASET PIJ DT25009](https://aset.az.gov/sites/default/files/2025-08/DT25009%20PIJ%20FINAL%20082025.pdf)
- TxDOT has published an innovation summary on its use of Numetric as a crash data analysis tool. — [TxDOT](https://www.txdot.gov/content/dam/docs/division/str/division-innovation-summaries/traffic-safety-numetric-crash-data-analysis-tool.pdf)
- Kittelson's crashKIT is a web tool marketed as needing "no GIS expertise." It runs HSM screening measures: crash frequency, EPDO, crash rate, critical rate, RSI, excess frequency by method of moments, proportion tests, and EB/SPF-based measures for agencies that have SPFs. It also offers example natural-language-style queries. — [crashKIT](https://crashkit.kittelsonsoftware.com/). Kittelson also built a Stanislaus County (CA) screening web map. — [Kittelson](https://www.kittelson.com/work/stanislaus-screening-web-map-application/)
- Esri's ArcGIS "Traffic Crash Analysis" solution analyzes crash data with usRAP and FHWA methods to find concentrations of fatal and serious crashes. — [Esri docs](https://doc.arcgis.com/en/arcgis-solutions/latest/reference/use-traffic-crash-analysis.htm). Esri also publishes open-source segmentation and crash tools. — [GitHub Esri/transportation-safety-tools](https://github.com/Esri/transportation-safety-tools)
- FHWA's SPICE is a free Excel macro tool for HSM-based predictive safety analysis of intersection control alternatives. It is commonly used in ICE. — [FHWA ICE Primer](https://highways.dot.gov/media/11516); [TxDOT manual](https://www.txdot.gov/manuals/des/tsp/chapter-6-safety-analysis--methodologies--and-tool/6-2-an-overview-of-predictive-safety-analysis-tool/6-2-5-safety-performance-for-intersection-control-.html)

**Local crash-records / collision diagram tools**
- Crash Magic (Pd' Programming) began as Intersection Magic in 1987, a collision diagram engine first built for the City of Boulder. It produces collision diagrams, summaries, statistics and pin/heat maps, and can be hosted by Pd' at GovernmentTools.com. — [pdmagic.com](https://www.pdmagic.com/); [Crash Magic Online](https://pdmagic.com/trf2021); [FHWA RSDP](https://highways.dot.gov/safety/data-analysis-tools/rsdp/rsdp-tools/crash-magic)
- Pd's Road Position Magic (RPM) is a geocoding service. It geocodes crashes to the nearest intersection, then "walks" each point along the approach street by distance and direction, and uses collision type and vehicle movement to choose the side of the road. It also standardizes street names, records a location confidence, and charges a flat fee for nightly locating after initial setup. — [pdmagic RPM](https://pdmagic.com/gis/rpm)
- A Caltrans preliminary investigation found Caltrans investigators used Accident Collision Diagram (ACD) and MicroStation for collision diagrams, and that Crash Magic Online was used in multiple states. TES (Canada) was also listed. — [Caltrans PI: Use of Collision Diagramming Systems](https://dot.ca.gov/-/media/dot-media/programs/research-innovation-system-information/documents/preliminary-investigations/use-of-collision-diagramming-systems-pi-a11y.pdf)
- Crossroads Software (Brea, CA) sells a Traffic Collision Database System, a Collision Report Writer, and Online Records Dissemination, mainly to police departments. SFPD adopted its database. — [Crossroads brochure](http://crossroadssoftware.com/support/tcdsbrochure.pdf); [SF Examiner](https://sfexaminer.com/news/sf-is-receiving-vehicle-collision-data-faster-with-new-database/article_b902a9cd-43ea-57eb-a6e3-51d7cae05298.html); [Report Writer](https://web.crossroadssoftware.com/report-writer). Caltrans's HSIP Analyzer manual names "Crossroads" as a typical local crash data source. — [HSIP Analyzer Manual 2024](https://dot.ca.gov/-/media/dot-media/programs/local-assistance/documents/hsip/2024/hsip-analyzer-manual-bcr2024.pdf)
- TES (deployed by CIMA+) is a cloud collision data management and network-screening platform used by Canadian municipalities. — [TES](https://tes.ca/software/collisions); [CIMA+](https://cima.ca/en/what-we-do/transportation/tes)
- LexisNexis Crash Mapper & Dashboards is bundled with its eCrash/BuyCrash police reporting products. — [LexisNexis](https://risk.lexisnexis.com/products/crash-mapper-and-dashboards)

**California public / free tools**
- UC Berkeley SafeTREC's TIMS offers "quick, easy and free access to California crash data." On Sep 28, 2026 it loaded 2024 final and 2025–2026 provisional SWITRS. It also has a 2020–2024 Traffic Safety Dashboard and AV crash dashboards. — [TIMS](https://tims.berkeley.edu/)
- About 97% of SWITRS crashes are geocoded by SafeTREC's workflow. Ungeocodable records get blank POINT_X/POINT_Y. — [TIMS SWITRS help](https://tims.berkeley.edu/help/crashdata/switrs.php); [TIMS geocoding](https://tims.berkeley.edu/help/crashdata/switrs-geocoding.php)
- TIMS has a Crash Diagram tool. It builds a printable 8.5×11 diagram from a SWITRS GIS Map selection, reports mapped vs. unmapped crashes (some go undrawn because of missing movement data or more than two parties), and lets users add, move, rotate or delete crashes by hand. — [TIMS Crash Diagram help](https://tims.berkeley.edu/help/tools/analysis/crash-diagram.php). Users can also report location errors. — [SafeTREC](https://safetrec.berkeley.edu/news/new-tims-feature-users-can-now-provide-feedback-crash-location-errors)
- CHP publishes CCRS crash records on the California Open Data portal (updated Oct 17, 2026). — [CA Open Data CCRS](https://publish.data.ca.gov/dataset/ccrs). Hobbyist and open-source CCRS API scripts exist. — [GitHub nc3man/switrs](https://github.com/nc3man/switrs)
- Caltrans's HSIP Analyzer is a required PDF form for HSIP Cycle 12 BCR applications. It handles cost estimate, countermeasure selection, crash data input and BCR calculation. — [HSIP Analyzer Manual 2024](https://dot.ca.gov/-/media/dot-media/programs/local-assistance/documents/hsip/2024/hsip-analyzer-manual-bcr2024.pdf)

**Big-data / exposure platforms with safety modules (incl. 2026 AI launches)**
- **INRIX Compass** (launched Mar 26, 2026) is a "generative AI agent designed specifically to help transportation agencies improve roadway safety." It runs on LLMs via Amazon Bedrock over INRIX speed, hard-braking and VRU-exposure data plus state and federal guidance, and suggests countermeasures. Miami-Dade County and the City of Las Vegas are quoted users. — [INRIX press release](https://inrix.com/press-releases/inrix-launches-compass-ai-platform-to-help-cities-reduce-systemic-roadway-safety-risk/)
- **Replica + Arity Safety Hub** (launched Jun 2, 2026) combines Arity driving-behavior data (speeding, hard braking, distraction), Replica pedestrian and bike exposure, and agency/federal crash records. It offers High Risk Corridors and a Safety Metrics Dashboard, and is pitched for "planning, reporting, grant applications, and before and after evaluation." — [Replica Safety Hub](https://replicahq.com/safety-hub); [PR Newswire](https://www.prnewswire.com/news-releases/replica-and-arity-launch-safety-hub-through-strategic-partnership-to-help-prevent-roadway-deaths-302787640.html); [Replica crash data sources](https://documentation.replicahq.com/docs/crash-data)
- **StreetLight InSight** markets safety solutions that evaluate driver-behavior change without waiting for crash data. — [StreetLight](https://www.streetlightdata.com/road-safety-solutions). SCAG bought a regional StreetLight subscription that includes "safety analytics," free to local agencies through June 2026. — [SCAG Big Data WP](https://scag.ca.gov/sites/default/files/bulk_uploads/26-418-BDP-0043-Big-Data-WP-SBCTA-Final.pdf)
- **Urban SDK** sells geospatial AI to "300+ communities," mostly police and public works. Its collision index and hotspot model uses 5-year fatal crashes, volumes, speeding, and roadway and neighborhood characteristics. — [Urban SDK features](https://www.urbansdk.com/features)
- **Iteris ClearGuide Safety** offers speeding analytics and related modules. Buyers include Seattle DOT and the Hillsborough MPO. — [Iteris ClearGuide](https://www.iteris.com/oursolutions/traffic-analytics-software/clearguide); [Seattle](https://www.iteris.com/news/seattle-department-of-transportation-selects-iteris-clearguide-saas-solution-for-smart-mobility-safety-and-sustainability-program)
- **Rekor** has a real-time crash prediction risk layer aimed at TMCs. — [Rekor help](https://help.rekor.ai/how-can-i-access-crash-prediction-information)
- **Ecopia AI** supplies AI-extracted planimetric data (crosswalks, sidewalks, etc.) for safety programs. Fehr & Peers is a consultant customer. — [Ecopia case study](https://www.ecopiatech.com/resources/case-study/improving-transportation-safety-accessibility-sustainability-with-high-precision-mapping-data)
- **Blyncsy** (part of Bentley) uses crowd-sourced dashcam imagery plus AI for asset and condition inventory. — [Carahsoft blog](https://www.carahsoft.com/blog/blyncsy-revolutionizing-road-safety-blog-2026)

**AI-native crash analysis**
- **Citian CRASH** claims to use "machine learning and AI, natural language processing" to process, refine and audit crash data. It offers dashboards, query and reporting, collision diagrams, recommended countermeasures with estimated costs, an HSM-tied countermeasure engine ranked by B/C, HSIP network screening dashboards, and "grant-ready outputs." In the Berkshire RPC (MA) case study, it automated the MassDOT IMPACT ingest and QA/QC and produced fact sheets for HSIP/SS4A submissions. — [Citian CRASH](https://www.citian.co/crash)
- **SCAG (Southern California)** is rolling out Citian's CRASH ("Crash Reduction through Analysis of Safety Hazards") to "SCAG and partner agencies, including cities, counties, and consultants working on their behalf." It is described as an AI-driven, geolocated crash data, dashboard, query and export platform. — [SCAG Toolbox Tuesday, Jan 14 2025](https://scag.ca.gov/sites/default/files/2025-02/tt_jan2025_part1_combined.pdf)
- Academic LLM work includes SafeTraffic Copilot (LLM crash prediction with feature attribution), CrashSage (LLM crash analysis framework), RAG countermeasure recommendation from crash narratives, and schema-grounded natural-language spatial queries over safety data. These are research papers, not products. — [PMC SafeTraffic Copilot](https://pmc.ncbi.nlm.nih.gov/articles/PMC12504690); [arXiv CrashSage](https://arxiv.org/html/2505.07853v1); [arXiv 2609.15997](https://arxiv.org/abs/2609.15997); [arXiv 2605.21712](https://arxiv.org/html/2605.21712v1)

**Video / lidar near-miss (surrogate safety)**
- Miovision Safety Studies and Continuous Safety Monitoring provide near-miss analytics 24/7. A Miovision spec describes the study product as "up to 60 conflict types generated from 60 hours of video." — [Miovision Safety Studies](https://miovision.com/safety-studies/); [Miovision spec](https://www.mobycon.nl/wp-content/uploads/2023/09/Miovision-Safety-Product-Specification.pdf)
- Derq INSIGHT is a camera-based real-time safety analytics and ATSPM platform. A next-generation version launched Mar 10, 2026; Montréal is deploying it at 100 intersections (Jun 2026); RTC Southern Nevada selected it in 2024. — [Derq 2026](https://en.derq.com/press-coverage/derq-advances-traffic-safety-intelligence-with-next-generation-of-insight); [Montréal](https://en.derq.com/press-coverage/montreal-deploys-derq-insight-across-100-intersections-in-citywide-ai-powered-safety-and-traffic-data-initiative); [Las Vegas](https://en.derq.com/press-coverage/2024/7/9/derq-to-deploy-state-of-the-art-advanced-intersection-safety-monitoring-in-las-vegas)
- Transoft TrafxSAFE is an on-demand video conflict analysis platform (TrafxSAFE Next launched at TRB 2024). — [Transoft](https://www.transoftsolutions.com/news/trafxsafe-next-launches-at-trb-2024/)
- Ouster BlueCity uses lidar for near-miss and signal actuation and was selected for 30+ more intersections around Atlanta (Apr 2026). — [Ouster](https://investors.ouster.com/news-releases/news-release-details/ouster-bluecity-selected-major-traffic-signal-management-and)

**Custom Vision Zero dashboards**
- Many cities build or commission their own: Austin's open-source Vision Zero Crash Data System, Portland's VZ dashboard, and a JMT-built dashboard for Anne Arundel County. — [GitHub cityofaustin](https://github.com/cityofaustin/atd-vz-data); [Portland](http://portland.gov/transportation/vision-zero/vision-zero-dashboard); [JMT](https://jmt.com/impact/vision-zero-dashboard)

### Inferences
- In 2026, incumbent "AI" safety features fall into two groups. Some are natural-language querying (Numetric Crash Query, crashKIT). Others are LLM agents over proprietary speed and behavior data (INRIX Compass, Replica Safety Hub). None found writes evidence-cited narrative findings from crash records in a study-report format.
- Citian CRASH under the SCAG contract is the most direct California competitor and may already be free to SCAG-region cities and their consultants. CrashIQ should find out its scope and access terms before pricing.

### Gaps
- No evidence of Crash Magic's current California city footprint. A search for California deployments returned nothing relevant.
- Could not get the SCAG CRASH contract value, term, or whether consultants get full export rights.
- No public detail on whether Numetric/AASHTOWare Safety is licensed by Caltrans. California is in AASHTO's pricing Group 3, but no Caltrans procurement record was found.

---

## 2. Who buys, and pricing models (public only)

### Takeaway
Statewide platforms cost hundreds of thousands per year (AASHTOWare Safety in California's tier: $385k/yr for one module plus $25k implementation units). Local and police analytics like Urban SDK run roughly $8.5k–$35k/yr (about $11.6k/yr for Imperial, CA). Most data and video vendors publish no prices. Consultants mostly don't buy these tools; they get access through agency licenses or use free TIMS and Excel.

### Cited Findings
- **AASHTOWare Safety (Numetric) FY2027 annual license fees:**
  - Group 1: $105k (Segment), $105k (Intersection), $51.5k (Trend), $52.5k (Alt Design)
  - Group 2: $195k / $195k / $105k / $105k
  - Group 3 (California, Florida, Texas): $385k / $385k / $210k / $210k
  - Licenses cover unlimited agency users plus local agencies, MPOs and consultants the agency names.
  - First-year implementation units are $25,000 each. California's tier is estimated at 12 units for Segment plus 12 for Intersection.
  - A 90-day test drive costs $0.
  - Source: [AASHTOWare FY2027 Catalog, pp. 56–58](https://www.aashtoware.org/wp-content/uploads/2026/06/FY-2027-AASHTOWare_Catalog_web.pdf)
- FY26 Segment and Intersection Analytics fees rose by up to 6%. — [AASHTOWare FY26 pricing update](https://www.aashtoware.org/story/pricing-update-for-fy26-catalog/)
- A New Hampshire Governor & Council agenda (Apr 15, 2026) authorized NH DOS/DOT to contract with Numetric for up to $810,000. This comes from a third-party mirror of the NH SOS agenda; the original was not retrieved. — [mirror of NH G&C agenda](https://livefreeordie.legal/executive/records/gov-exec-council-meeting-attachment-gov-exec-council-meeting-2026-04-15-governor-and-executive-council-meeting-2026-04-15-httpswwwsosnhgovmeetingapril-15-2026-gc-agenda-f8ba5b0ffb-httpsmediasosnhgovgovcouncil20260415081-gc-agenda-041526pdf)
- **Urban SDK** (mostly police buyers):
  - Imperial, CA: 3-year renewal totaling $34,756 for the Police Department. — [MotionCount summary](https://motioncount.com/items/imperialCA_e5e356ac_2575)
  - Cheyenne, WY: 3-year subscription totaling $105,367.50. — [Citizen Portal](https://citizenportal.ai/articles/6212646/wyoming/laramie-county/cheyenne/police-seek-and-committee-backs-threeyear-urban-sdk-subscription-for-traffic-analytics)
  - Olmsted Falls, OH: 3-year contract "starting at $8,550," with yearly increases. — [Cleveland.com](https://cleveland.com/community/2026/03/olmsted-falls-considering-modern-police-department-gps-speeding-software-service.html)
  - Urban SDK's terms allow annual price increases of the greater of 6% or CPI. — [Urban SDK ToS](https://www.urbansdk.com/legal/terms-of-service)
- **Crash Magic / Road Position Magic:** RPM's page has an "Estimated Road Position Magic cost" table for municipalities from under 25,000 to 1M population, with a flat nightly-locating fee after setup. The dollar figures could not be extracted, so they are not reported here. — [pdmagic RPM](https://pdmagic.com/gis/rpm). Crash Magic license pricing: not public.
- **Crossroads Software:** a Garden Grove, CA staff report approved a five-year Crossroads agreement for **electronic citation** software at $121,000. That is not the collision database, but it shows the vendor's municipal price scale. Collision database pricing: not public. — [Garden Grove staff report](https://agendasuite.org/iip/gardengrove/file/getfile/9125)
- **StreetLight:** sold by subscription, including regional subscriptions (SCAG's covers local agencies at no cost through June 2026). Price not public. — [SCAG](https://scag.ca.gov/sites/default/files/bulk_uploads/26-418-BDP-0043-Big-Data-WP-SBCTA-Final.pdf); [StreetLight 2016 regional subscription PR](https://prweb.com/releases/streetlight_data_to_transform_transportation_infrastructure_planning_with_new_online_tool/prweb13614613.htm)
- **Free tools:** TIMS (free account), the Caltrans HSIP Analyzer (free PDF), FHWA SPICE (free Excel), and Esri's open-source safety tools on GitHub. — [TIMS](https://tims.berkeley.edu/); [HSIP Analyzer](https://dot.ca.gov/-/media/dot-media/programs/local-assistance/documents/hsip/2024/hsip-analyzer-manual-bcr2024.pdf); [FHWA ICE Primer](https://highways.dot.gov/media/11516); [GitHub Esri](https://github.com/Esri/transportation-safety-tools)
- **Not public:** INRIX Compass, Replica Safety Hub, Citian CRASH, Iteris ClearGuide Safety, Miovision Safety Studies, Derq INSIGHT, TrafxSAFE, crashKIT, Numetric direct-to-city licensing. Request-a-demo only on the vendor pages cited above.
- **Buyers by segment:** state DOTs and highway safety offices (Numetric/AASHTOWare; [AZ PIJ](https://aset.az.gov/sites/default/files/2025-08/DT25009%20PIJ%20FINAL%20082025.pdf)); MPOs/COGs (SCAG for Citian CRASH and StreetLight; Berkshire RPC for Citian; Hillsborough MPO for ClearGuide); city police departments (Urban SDK, Crossroads); city DOTs (Seattle ClearGuide, Montréal Derq). Consultants appear as licensed third-party users under agency licenses ([AASHTOWare catalog](https://www.aashtoware.org/wp-content/uploads/2026/06/FY-2027-AASHTOWare_Catalog_web.pdf); [SCAG](https://scag.ca.gov/sites/default/files/2025-02/tt_jan2025_part1_combined.pdf)) and as builders of custom dashboards ([JMT](https://jmt.com/impact/vision-zero-dashboard); [Kittelson](https://www.kittelson.com/work/stanislaus-screening-web-map-application/)).

### Inferences
- No seat-priced, consultant-targeted SaaS for California crash analysis showed up. Consultant-facing products are either agency-licensed (Numetric, Citian through SCAG) or free (TIMS). A per-seat or per-study consultant product would be a distinct pricing position, but CrashIQ would compete with "free TIMS + Excel + staff hours."
- Urban SDK's ~$8.5k–$35k/yr range (derived from the three contracts above) for small and mid cities is a useful reference for what local agencies pay for a data subscription without a formal RFP.

### Gaps
- Crash Magic, Crossroads collision database and TES price points were not found.
- No public evidence of what consulting firms spend on internal crash-analysis tooling.

---

## 3. Consultant / agency pain points (tedious or missing features)

### Takeaway
The documented pain is concentrated in four places: crash data cleanup and geocoding (crashes placed at intersection centroids or ungeocoded), building collision diagrams, re-keying crash counts into application forms (California's HSIP Analyzer is manual entry plus attached diagrams and lists), and refreshing analyses that agencies otherwise pay consultants to redo.

### Cited Findings
- **Data cleanup:** Berkshire RPC's crash data "required manual downloading, organizing, cleaning before any analysis could begin, and refreshing the HIN or the predictive model meant re-engaging outside consultants." Sub-jurisdictions "had no tools of their own to run safety analyses or produce grant-ready outputs." — [Citian case study](https://www.citian.co/crash) (vendor source)
- Ohio DOT publishes step-by-step "Crash Data Cleanup" instructions asking users to report location inaccuracies. — [ODOT Crash Data Cleanup PDF](https://dam.assets.ohio.gov/image/upload/q_auto/v1752240136/transportation.ohio.gov/safety/highway-safety/Crash-Analysis-Tools/cam/HowToCompleteCrashDataCleanup.pdf)
- UT Austin CTR built an Excel VBA parsing tool to improve TxDOT's HSIP report-creation process for intersection and non-intersection crashes. — [CTR poster](https://ctr.utexas.edu/wp-content/uploads/EAC-2022-Poster-Crash_DB_Mgmt.pdf)
- Arizona DOT relied on "free modeling tools, some of which have to be adapted for their purpose," and noted that some of those tools were being discontinued. — [AZ PIJ](https://aset.az.gov/sites/default/files/2025-08/DT25009%20PIJ%20FINAL%20082025.pdf)
- **Geocoding / placement:** Pd' markets RPM against crashes that land "right in the middle of the nearest intersection? On the sidewalk? In the ocean?" — [pdmagic RPM](https://pdmagic.com/gis/rpm). About 3% of SWITRS crashes are not geocoded in TIMS. — [TIMS](https://tims.berkeley.edu/help/crashdata/switrs.php). California police reports record location relative to intersections, which makes geocoding hard. — [PMC: Geocoding police collision report data from California](https://pmc.ncbi.nlm.nih.gov/articles/PMC2806385/)
- **Collision diagrams:** a 1979 TRR paper describes diagrams "prepared manually by a laborious search of accident files." — [TRR 706](https://onlinepubs.trb.org/Onlinepubs/trr/1979/706/706-006.pdf). Indiana funded a collision diagram builder for RoadHAT. — [Purdue JTRP](https://docs.lib.purdue.edu/jtrp/1611). New Hampshire used Safety Analyst's network screening most "because it assembles collision diagrams and crash data in one place." — [FHWA HSIP scan](https://highways.fhwa.dot.gov/safety/hsip/hsip-national-scan-tour/chapter-6-using-advanced-safety-analysis-methods-and-tools). TIMS diagrams leave some crashes undrawn when movement data is missing or more than two parties are involved, and require manual add/move edits. — [TIMS Crash Diagram](https://tims.berkeley.edu/help/tools/analysis/crash-diagram.php)
- **Application assembly (California HSIP):**
  - Applicants enter crash counts by severity into up to five tables (All, Night, Ped & Bike, Emergency Vehicle, Animal) over 3–5 years.
  - They must attach collision diagrams and collision lists organized by location.
  - They must apply countermeasure influence areas (for example, crashes within 250 ft of a new signal).
  - TIMS users "may find it necessary to add in known crashes that were not included in the TIMS summaries," with a signed attestation.
  - Source: [Caltrans HSIP Analyzer Manual 2024, pp. 5–9](https://dot.ca.gov/-/media/dot-media/programs/local-assistance/documents/hsip/2024/hsip-analyzer-manual-bcr2024.pdf)
- **B/C:** Numetric Safety Analysis and Citian's countermeasure engine both compute B/C. — [FHWA RSDP Numetric](https://highways.dot.gov/safety/data-analysis-tools/rsdp/rsdp-tools/numetric); [Citian](https://www.citian.co/crash). For California HSIP, the official BCR must come from the HSIP Analyzer. — [HSIP Analyzer Manual](https://dot.ca.gov/-/media/dot-media/programs/local-assistance/documents/hsip/2024/hsip-analyzer-manual-bcr2024.pdf)

### Inferences
- Several California-specific chores are not automated by any product found: influence-area crash filtering, severity-table counts in HSIP Analyzer categories, and organized diagram and list attachments. Each maps directly to a CrashIQ export.
- "Place crashes lacking coordinates" is a proven paid feature. Pd' sells it as a separate service (RPM), and TIMS leaves about 3% unplaced.

### Gaps
- No practitioner forum threads (e.g., Reddit r/traffic_engineering, ITE Community) were retrieved within this research budget. Pain-point evidence comes from agency documents and vendor case studies, not direct consultant testimony.
- No time-and-motion data was found on hours consultants spend per safety section.

---

## 4. Does any product auto-generate study-ready safety sections or HSIP applications? California-specific tools?

### Takeaway
No product found auto-generates a California HSIP application (HSIP Analyzer inputs plus diagrams and lists), an ISOAP/ICE safety section, an ATP safety narrative, or a traffic-study safety section with evidence-cited AI findings. The closest are Citian CRASH ("grant-ready outputs," fact sheets, HSIP network screening, collision diagrams, B/C-ranked countermeasures, deployed regionally by SCAG), Numetric's downloadable network-screening and crash reports, and INRIX Compass and Replica Safety Hub (LLM or dashboards pitched for grants, but built on behavior data, not CCRS study formats). California-specific tools are TIMS (free), the HSIP Analyzer (form), Crossroads (police records), SCAG's Citian CRASH, and consultant-built county screening apps.

### Cited Findings
- Citian advertises "grant-ready outputs" and fact sheets that "support ... grant submissions, strengthening HSIP and SS4A competitiveness." The HSIP reference is to the federal program and network screening; there is no claim of producing Caltrans HSIP Analyzer files. — [Citian](https://www.citian.co/crash)
- Numetric Network Screening produces a "downloadable and sharable Network Screening Report," and Crash Query a downloadable "Crash Report." — [FHWA RSDP](https://highways.dot.gov/safety/data-analysis-tools/rsdp/rsdp-tools/numetric)
- AASHTOWare sells Numetric "Professional Enablement Services" to "automate reports that currently require consultative engagements." This confirms that agencies currently pay consultants for recurring safety reports. — [AASHTOWare FY2027 Catalog p. 58](https://www.aashtoware.org/wp-content/uploads/2026/06/FY-2027-AASHTOWare_Catalog_web.pdf)
- Replica positions Safety Hub for "grant applications." — [Replica](https://replicahq.com/safety-hub)
- INRIX Compass provides "specific countermeasures based on the underlying data and industry best practices" and supports proposing FHWA Proven Safety Countermeasures. — [INRIX](https://inrix.com/press-releases/inrix-launches-compass-ai-platform-to-help-cities-reduce-systemic-roadway-safety-risk/)
- California HSIP requires the HSIP Analyzer PDF form, and California's equivalent of an LRSP (LRSP, SSAR or Vision Zero Action Plan) is a prerequisite for HSIP funds. — [HSIP Analyzer Manual](https://dot.ca.gov/-/media/dot-media/programs/local-assistance/documents/hsip/2024/hsip-analyzer-manual-bcr2024.pdf); [Caltrans LRSP/SSARP](https://dot.ca.gov/programs/local-assistance/fed-and-state-programs/highway-safety-improvement-program/local-roadway-safety-plans)
- **Name-collision note:** "CrashIQ" is already used by an open-source MCP project (US accident-severity ML with an LLM interface) and by an AI accident-documentation app built on Blink. Neither is a traffic engineering product, but both are a trademark and SEO consideration. — [LobeHub CrashIQ](https://lobehub.com/mcp/sandeeppudi-crashiq-road-accident-severity-intelligence-platform); [Blink CrashIQ](https://blink.new/p/crashiq-ai-platform-qxnij27p)

### Inferences
- **Gap CrashIQ can occupy:** California-native, corridor-scoped, consultant-facing analysis built on CCRS. It would fill missing coordinates, filter by influence area, write AI pattern findings with record-level citations, and export in HSIP Analyzer, ISOAP/ICE, ATP and traffic-study formats. Each incumbent covers at most two of these pieces.
- **Biggest competitive risks:**
  1. SCAG's Citian CRASH, which may be free to SoCal cities and consultants.
  2. TIMS being free, with diagrams.
  3. Numetric adding report automation if Caltrans licenses AASHTOWare Safety.
  4. INRIX and Replica LLM agents moving toward crash-record narratives.

### Gaps
- Could not confirm whether Citian CRASH exports Caltrans HSIP Analyzer-compatible tables or ATP/ICE formats. Its public pages don't say.
- No information found on whether any vendor supports Caltrans ISOAP/ICE safety-step formats specifically.
- Startup scan for 2023–2026 LLM-native crash analysis turned up mostly academic prototypes. Tracxn and Crunchbase-style listings (e.g., "Traffic Aigent," 2025, Toronto, unfunded) could not be verified from a primary source, so they are excluded as findings.
