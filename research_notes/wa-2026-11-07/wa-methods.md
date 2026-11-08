# Washington: safety-analysis manuals, rates, crash costs, screening (2026-11-07)

Written by Hermes for the user's added scope (2026-11-07). Every number below was read from the PDF named with it;
PDFs are in `~/.hermes/cache/scratch/states/wa/manuals/` (not committed), downloaded 2026-11-07. "PDF p." is the page
in the PDF file; "printed p." is the number on the page. Anything not found says **not found**.

**Headline:** Washington does not work like California. WSDOT **does not use crash rates** for decisions (so there is
no TASAS-style table of average rates by facility type), screens with **HSM safety performance functions + Empirical
Bayes** (expected and excess fatal + serious crashes), uses **HSM calibration factor 1.00**, prices crashes with
**WSDOT societal costs where K and A cost the same ($4,308,200)**, and requires a **§148/§407 footer on every page,
table or graph** of safety analysis.

## 1. Safety Analysis Guide for Design Projects (WSDOT, August 2024)
URL: https://wsdot.wa.gov/publications/fulltext/design/ASDE/Safety-Analysis-Guide.pdf (printed p. = PDF p. − 5)

| Topic | What it says | Where |
|---|---|---|
| Crash rates | "staff is required to remove columns reporting crash rates as WSDOT no longer uses crash rates for decision-making … crash rates can incorrectly assume that there is always a linear relationship between traffic volume and crashes, and short segments can overinflate crash rates" | PDF p.24, printed p.19 (§6.6, IHSDM) |
| Hot spots / heat maps | "WSDOT does not perform hot spot analysis … WSDOT does not use heat maps for decision making" (regression to the mean; no comparison with similar facilities) | PDF p.25, printed p.20 (§6.9) |
| Screening | I2 program screens the state highway system "approximately every two years to identify segments and intersections where the expected number of fatal and serious injury crashes are greater than what would be anticipated at a similar site (… predicted average crash frequency)": Collision Analysis Locations/Corridors (CAL/CAC) and Intersection Analysis Locations (IAL) | PDF p.11, printed p.6; PDF p.28, printed p.23 |
| Study period | "Use five full calendar years (January 1st to December 31st) of historic crash data"; "minimum 2 years of data where major modifications at the site have occurred"; one year only → use the HSM predicted frequency | PDF p.18–19, printed p.13–14 (§6.4); design-analysis table PDF p.29 |
| Observed frequency | "the annual average across five years measured in full calendar years"; with HSM, expected replaces observed | PDF p.12, printed p.7 |
| SPF calibration | "WSDOT uses a calibration factor of 1.00, which is the default calibration factor in the HSM predictive methods" (HSM 1st ed. was built largely on Washington data) | PDF p.20, printed p.15 |
| Tools | HSM extended spreadsheets (Ch. 10, 11, 12) and IHSDM; ISATe no longer recommended; "Use of any other tools for project analysis is not allowed" | PDF p.23, printed p.18 |
| CMFs | WSDOT CMF short list (internal SharePoint); FHWA CMF Clearinghouse only as a starting point, approval needed if not on the short list; don't multiply CMFs on the same target crashes | PDF p.21–22, printed p.16–17 |
| Societal cost | Values "set as a matter of policy by the HSEC … modified from NHTSA and FHWA values"; "the most current values are available from the TSSA Highway Safety SharePoint site" (internal: **values not in this guide**) | PDF p.24, printed p.19 (§6.7) |
| Severity scale | KABCO: K fatal, A suspected serious, B suspected minor, C possible, PDO | PDF p.5 (acronyms) |
| Disclaimer | Standard §148/§407 text "should be included on any page, table, or graph representing safety data or analysis results … this disclaimer must be in the footer" | PDF p.14, printed p.9 (§6.3.1) |
| Consultant data | "the single row flat file format … can be requested through the Crash Data and Reporting Branch at WSDOT" (includes Target Zero indicators) | PDF p.26, printed p.21 |

## 2. 2024 Washington State Safety Implementation Plan (HSIP Implementation Plan, "Getting to Zero")
URL: https://wsdot.wa.gov/about/data/Multimodal-mobility-dashboard/doc/TargetZero-ImplementationPlan-HSIP2024.pdf
(printed p. = PDF p. − 7)

- **Crash costs (WSDOT-specific, FHWA *Crash Costs for Highway Safety Analysis* 2018 method)**, per crash
  (Exhibit 6 note 3, PDF p.18, printed p.11; repeated PDF p.90, printed p.83):
  | K | A | B | C | O |
  |---|---|---|---|---|
  | $4,308,200 | $4,308,200 | $304,200 | $180,600 | $19,300 |
  Dollar year: **not stated** next to the table; the exhibit is "2023 Societal Crash Cost" on 2023 crashes
  (WSDOT Engineering Crash Data Mart, 2023 year-end snapshot, June 2024).
- 2023 totals (Exhibit 6, PDF p.18): 4,505 fatal + serious injuries, 3,816 fatal + serious crashes, 113,113 crashes,
  $23,151,024,900 societal cost.
- **Network screening method** (PDF p.50, printed p.43): sliding window and peak searching to set reference
  populations; rank by **expected average crash frequency with Empirical Bayes**; cut-off **0.5 expected (CAL/CAC) or
  0.3 excess (IAL) crashes per year**; CAL/CAC lists in odd years, IAL in even years; managed-access highways in
  cities over 30,000 left out (the cities manage them). WSDOT is moving to a new SPF tool and may merge the lists.
- Crash-prevention (systemic) categories are ranked on **excess** fatal + serious crash frequency, e.g. unsignalized
  intersections with annual excess ≥ 0.5 (PDF p.53, printed p.46).

## 3. Design Manual M 22-01.23 (September 2024)
- **Ch. 321 Safety Analysis**: https://wsdot.wa.gov/publications/manuals/fulltext/m22-01/321.pdf. Safe System policy
  (E 1085.01), Target Zero goal of zero deaths and serious injuries by 2030; every project evaluates the need for a
  safety analysis; scope and scale come from the Safety Analysis Guide (Page 321-1 to 321-2). No rates or costs.
- **Ch. 1300 Intersection Control**: https://wsdot.wa.gov/publications/manuals/fulltext/m22-01/1300.pdf. ICE step
  "Operational and Safety Performance Analysis" points to the Safety Analysis Guide; B/C for safety = "Societal cost
  savings … of reduced crash frequency", "See the Safety Analysis Guide for WSDOT Societal Costs" (Page 1300-16).
- **Project Delivery Memo 25-02** (7/8/2025, Roundabout First and ICE):
  https://wsdot.wa.gov/publications/fulltext/ProjectDev/ProjectDeliveryMemos/Memo25-02.pdf. "Roundabouts are the
  preferred intersection control type on state highways" (PDF p.2); ICE splits a **vehicle safety analysis** and an
  **active transportation safety assessment**; vehicle safety "typically involve[s] reviewing 5 consecutive years of
  historical data", enhanced by HSM predictive methods, CMFs and societal cost (PDF p.5).

## 4. Local agencies: City Safety Program 2026 and Local Road Safety Plans
- **2026 City Safety Program application** (docx, Oct 2025):
  https://wsdot.wa.gov/sites/default/files/2025-10/LP-City-Safety-Program-2026-Application.docx. Projects must be in
  the city's **Local Road Safety Plan** (attach it); a **spot** project "must address one or more fatal and/or serious
  crashes from 2020-2024" listed by **crash report number**; upgrading signs-only control requires evaluating a
  roundabout. Funding: $30 M HSIP, 100% federal for phases authorized before 4/30/2029 (webinar PDF p.4).
- **City Safety crash-data request** (DOT Form 780-032, rev. 04/2026, "2026 City Safety Program layout"):
  https://wsdot.wa.gov/sites/default/files/2026-04/2026-City-Safety-Program.pdf. Date range 1/1/2020–12/31/2024,
  all crashes except limited-access highways, "Where available, GPS coordinates will be provided", Excel + PDF map of
  fatal and serious crashes. This is the file a CrashIQ user in a WA city would upload.
- **Eligible cities 2020–2024** (KSI per city per year): https://wsdot.wa.gov/sites/default/files/2025-11/LP-HSIP-Washington-Eligible-Cities-2020-2024.pdf
  (e.g. Bellevue 16 / 20 / 27 / 21 / 32).
- **LRSP**: WSDOT's information sheet (https://wsdot.wa.gov/sites/default/files/2021-10/LP-Local-Road-Safety-Plan.pdf)
  and the FHWA-based template (https://wsdot.wa.gov/sites/default/files/2023-03/LocalRoadSafetyPlan-Template-Feb2023.pdf):
  the 7 steps (analyze data → individual fatal/serious crashes → risk factors → network for risk factors →
  prioritized locations → countermeasures → prioritized projects), webinar PDF p.8. Systemic, risk-factor based.
- **Countermeasures webinar** (Dec 2025): https://wsdot.wa.gov/sites/default/files/2025-12/LP-Safety-Countermeasures-Webinar_0.pdf
  uses the FHWA CMF Clearinghouse and a B/C worksheet (PDF p.45–52); example CMFs (high-visibility crosswalk 0.60,
  median refuge 0.69, curb extension 0.70, stop bars 0.85, pedestrian lighting 0.58; PDF p.55–56). The worksheet's
  crash costs: **not found** (the worksheet itself is not posted).

## 5. Planning and traffic impact studies
- **Safety Guidance for Corridor Planning Studies** (June 2015/2016):
  https://wsdot.wa.gov/sites/default/files/2021-10/SafetyGuidance_CorridorPlanningStudies_June2016.pdf: "WSDOT avoids
  the use of crash rates in safety documents and efforts to quantify safety performance" (printed p.13).
- **Multimodal Transportation Impact Analysis Guidelines (2nd draft)**:
  https://wsdot.wa.gov/sites/default/files/2021-04/TrafficOps-WSDOTMultimodalTranspImpactAnalysisGuidelines.pdf:
  IHSDM is the primary safety model.

## 6. Statewide rates
- **Average crash rates by facility type: not found.** WSDOT publishes none and says it doesn't use rates (§1, §5).
- Statewide fatality and serious-injury rates **per 100 million VMT** exist only as federal performance measures
  (TPM Safety Folio, 2027 targets, https://wsdot.wa.gov/sites/default/files/2026-09/TPM-Safety-Folio-2027-targets.pdf),
  one statewide number per year, not by facility type.
- Critical-rate method: **not found** (not used; screening is SPF + EB).

## 7. Differences from California (what a WA pack must change)
1. **No rate table.** CA compares a location's rate (per MVM / MEV) with TASAS base rates by rate group; WA uses no
   rates. A WA pack should hide rate-vs-average findings or label them "not a WSDOT method", and offer **HSM
   predicted / expected / excess (EB)** instead, with **calibration 1.00**.
2. **Crash costs.** CA LRSM 2026 prices KA together by location type ($2,379,000 signalized / $3,784,000
   non-signalized / $3,276,000 roadway), B $213,000, C $121,000, O $20,000 (2026 $). WA prices K = A = $4,308,200,
   B $304,200, C $180,600, O $19,300 (year not stated; 2023 crashes), with no location-type split.
3. **Severity focus.** Both are KABCO; WA programs (I2, City Safety, Target Zero) count **fatal + serious (KSI)**;
   City Safety spot projects must name the KSI crashes by report number.
4. **Study period.** WA: 5 full calendar years, minimum 2 after a major change. CA HSIP: 3–5 years.
5. **Screening.** WA: sliding window + peak searching, EB expected, 0.5 / 0.3 excess cut-offs; no hot-spot or heat-map
   ranking. CA tools rank by counts, rates and crash cost.
6. **Local plans.** WA City Safety requires an LRSP (systemic 7-step); CA HSIP uses LRSM B/C per project.
7. **ICE.** WA Memo 25-02: roundabout first on state highways, separate vehicle and active-transportation safety
   assessments.
8. **Legal footer.** WA requires the §148/§407 text in the footer of every page, table or graph of safety analysis
   (SAG §6.3.1). CrashIQ's WA exports (PDF, Excel) need it.
9. **CMFs.** WA: WSDOT short list first (internal), Clearinghouse with approval. CA: LRSM Appendix B CRFs.

## Not checked
- WSDOT's internal SharePoint societal-cost values (may be newer than the 2024 plan's) and the CMF short list.
- The County Safety Program (CRAB / county roads) rules; WSDOT's new SPF tool; SPF tables in HSM (AASHTO copyright).
