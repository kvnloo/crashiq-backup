# California Crash/Safety Analysis Practice and Requirements (as of Oct 2026)

Scope: what California rules and agency practice actually require for crash analysis, written for a CrashIQ gap analysis. CrashIQ's planned modes are corridor profile, TIS/TIA safety section, LRSP, HSIP B/C, ISOAP/ICE with SPICE, and ATP. Sources were fetched in October 2026. Wherever a source showed its own date, that date is noted. Outdated or conflicting items are flagged **[FLAG]**.

---

## 1. Caltrans Local Roadway Safety Manual (LRSM), HSIP Cycle 13 rules, B/C method, HSIP Analyzer

### Takeaway
Local HSIP is selected purely by benefit-cost ratio (BCR). The BCR uses 3–5 years of *observed* police-reported crashes inside each countermeasure's influence area, split into 5 severity levels. It applies fixed Caltrans CRFs from a closed list of 86 countermeasures and fixed crash costs by location type, and must be computed in Caltrans' PDF "HSIP Analyzer." Cycle 13 (2026) requires a BCR of at least 5.0 to apply. Recent funding cutoffs have been 7.0–18.0. An LRSP or equivalent, updated within 5 years, is an eligibility gate.

### Cited Findings
**Versions and documents**
- LRSM Version 1.7 is dated April 2024 (4/18/2024). Version 1.0 dates from 4/20/2012 — [LRSM v1.7 PDF](https://dot.ca.gov/-/media/dot-media/programs/local-assistance/documents/hsip/2024/lrsm2024-v2.pdf)
- **[FLAG]** A newer **LRSM Version 1.8 dated 5/11/2026** is the current edition for Cycle 13. The call-for-projects page links it as `lrsm2026final.pdf`, and its pages are reproduced inside the July 2026 HSIP Analyzer Manual. The Cycle 13 Q&A confirms the LRSM "has been updated" from the Cycle 12 version. Treat any v1.7 (2024) figures as superseded — [Cycle 13 call page](https://dot.ca.gov/programs/local-assistance/fed-and-state-programs/highway-safety-improvement-program/apply-now); [HSIP Analyzer Manual (BCR) July 2026](https://dot.ca.gov/-/media/dot-media/programs/local-assistance/documents/hsip/2026/hsipanalyzermanual2026bcrfinalapp.pdf); [Cycle 13 webinar Q&A, Q18](https://dot.ca.gov/-/media/dot-media/programs/local-assistance/documents/hsip/2026/cycle13-webinar-qa-20260721.pdf)
- The LRSM is organized around these steps: identifying safety issues (Ch. 2: state/local crash databases, TIMS, police reports, observations, public notifications, roadway data, exposure data, field reviews/RSAs), safety data analysis (Ch. 3: quantitative and qualitative), countermeasure selection (Ch. 4), and B/C calculation and project comparison (Ch. 5) — [LRSM v1.7](https://dot.ca.gov/-/media/dot-media/programs/local-assistance/documents/hsip/2024/lrsm2024-v2.pdf)

**LRSM analysis procedures**
- "The two main quantitative analysis methods for roadway crashes are crash frequency and crash rate." The LRSM suggests ways to run these, such as summarizing by type, severity and location, and building "Top 10 (or 20)" lists of intersections and segments — [LRSM v1.7 §3.1](https://dot.ca.gov/-/media/dot-media/programs/local-assistance/documents/hsip/2024/lrsm2024-v2.pdf)
- Crash-rate formulas in the LRSM (taken from FHWA manuals):
  - Segment: R = (C × 100,000,000) / (V × 365 × N × L), in crashes per 100 million VMT.
  - Intersection: R = (1,000,000 × C) / (365 × N × V), in crashes per million entering vehicles (MEV).
  - Where AADT is missing, segment length or population can serve as exposure — [LRSM v1.7 §2.7, §3.1](https://dot.ca.gov/-/media/dot-media/programs/local-assistance/documents/hsip/2024/lrsm2024-v2.pdf)
- "The lack of reliable statewide traffic volumes for all roadway types precludes Caltrans from using the crash rate methodology in their statewide project scoring and ranking processes for the HSIP." — [LRSM v1.7 §3.1](https://dot.ca.gov/-/media/dot-media/programs/local-assistance/documents/hsip/2024/lrsm2024-v2.pdf)
- Caltrans "has avoided using methodology requiring agencies to mathematically adjust their crash data (e.g., Empirical Bayes) and instead has opted to use 3 to 5 years of 'observed crashes' in estimating 'expected crashes.'" The LRSM still discusses regression to the mean as a caution — [LRSM v1.7](https://dot.ca.gov/-/media/dot-media/programs/local-assistance/documents/hsip/2024/lrsm2024-v2.pdf)
- Recommended action: "Obtain at least 5 years of network-wide crash data". Also complete both a crash frequency and a crash rate analysis, looking for patterns by crash type, severity, mode, pavement condition, roadway characteristics, time of day and intersection control — [LRSM v1.7](https://dot.ca.gov/-/media/dot-media/programs/local-assistance/documents/hsip/2024/lrsm2024-v2.pdf)
- Qualitative analysis covers CA-MUTCD and design-standard compliance (sight distance, curve radius, skew, lane/shoulder width, clear recovery zone) plus field assessments of the locations flagged by the quantitative analysis — [LRSM v1.7 §3.2](https://dot.ca.gov/-/media/dot-media/programs/local-assistance/documents/hsip/2024/lrsm2024-v2.pdf)
- The LRSM uses the term "High Crash Concentration Locations (HCCLs)" and frames the work as both reactive and proactive (systemic) — [LRSM v1.7](https://dot.ca.gov/-/media/dot-media/programs/local-assistance/documents/hsip/2024/lrsm2024-v2.pdf)
- Agencies that use vendor software (e.g., Crossroads) are encouraged to share geocoding updates back to CHP's SWITRS managers — [LRSM v1.7 §2.1](https://dot.ca.gov/-/media/dot-media/programs/local-assistance/documents/hsip/2024/lrsm2024-v2.pdf)

**Countermeasure list and CRFs (Cycle 13 / LRSM v1.8)**
- BCR projects must use the **86 countermeasures with established CRFs**:
  - By location type: Signalized Intersection (SI) 22, Non-Signalized (NS) 25, Roadway (R) 39.
  - By crash type the CRF applies to: All 63, Ped & Bike 18, Night 3, Emergency Vehicle 1, Animal 1 — [Cycle 13 webinar slides 7/21/2026](https://dot.ca.gov/-/media/dot-media/programs/local-assistance/documents/hsip/2026/cycle13-webinar-slides-20260721.pdf)
- Each countermeasure lists Crash Types Addressed, CRF, Expected Life (10 or 20 years), Funding Eligibility (90% in Cycle 13) and "Systemic Approach Opportunity" (Very High to Low). Suffixes mark the target crash type: NT = night, PB = ped/bike, EV = emergency vehicle, AL = animal, RA = roundabout — [HSIP Analyzer Manual July 2026 / LRSM v1.8 App. B](https://dot.ca.gov/-/media/dot-media/programs/local-assistance/documents/hsip/2026/hsipanalyzermanual2026bcrfinalapp.pdf)
- Example CRFs from LRSM v1.8 (CRF / expected life), same source:
  - SI01NT intersection lighting: 40% night / 20 yr
  - SI02 signal hardware: 15% / 10
  - SI03 signal timing: 15% / 10
  - SI05 left-turn lane plus phase: 55% / 20
  - SI06 protected left phase: 30% / 20
  - SI07 mast arm: 30% / 20
  - SI09 advance flashing beacons: 30% / 10
  - SI11 raised median: 25% / 20
  - SI12PB ped median fencing: 35% P&B / 20
  - SI13 directional median openings: 50% / 20
  - SI14 right-turn lane: 15% / 20
  - SI15 reduced left-turn conflict intersection: 50% / 20
  - SI16RA signal to roundabout: 79% fatal/injury, 35% non-injury / 20
  - R21 HFST: 55% / 10
  - R22 fluorescent signs: 15%
  - R23 curve chevrons: 40%
  - R24 curve warning signs: 25%
  - R26 dynamic speed signs: 30%
  - R27 delineators: 15%
  - R28 edge/centerlines: 25%
  - R29 no-passing line: 45%
  - R30 centerline rumble strips: 20%
  - R31 edgeline rumble strips: 15%
  - R32 speed safety cameras: 20% (all R-series above are 10 yr)
  - R33PB bike lanes: 35% / 20
  - R34PB separated bike lanes: 45% / 20
  - R35PB sidewalk/pathway: 80% / 20
  - R36PB enhanced crossing: 35% / 20
  - R37PB raised crossing: 35% / 20
  - R38PB RRFB: 35% / 20
  - R39AL animal fencing: 80% / 20
- For roundabouts, the CRF "is dependent on the ADT, project location (Rural/Urban) and the roundabout type (1 lane or 2 lanes)," calculated with a Caltrans procedure. A roundabout must be the only countermeasure at its location — [HSIP Analyzer Manual July 2026](https://dot.ca.gov/-/media/dot-media/programs/local-assistance/documents/hsip/2026/hsipanalyzermanual2026bcrfinalapp.pdf)
- Special rules:
  - R15–R18 (shoulder widening, curve flattening, crest flattening) are allowed only as the last step of an "incremental approach," after low-cost countermeasures were tried.
  - New signals (NS03) need a warrant sheet meeting CA MUTCD Warrant 4, 5 or 7.
  - SI07 and SI02 cannot be combined.
  - Sources: [Cycle 13 slides](https://dot.ca.gov/-/media/dot-media/programs/local-assistance/documents/hsip/2026/cycle13-webinar-slides-20260721.pdf); [Q&A Q27, Q36](https://dot.ca.gov/-/media/dot-media/programs/local-assistance/documents/hsip/2026/cycle13-webinar-qa-20260721.pdf)
- Up to 3 countermeasures per category (SI, NS, R), so up to 9 per project — [Q&A Q29](https://dot.ca.gov/-/media/dot-media/programs/local-assistance/documents/hsip/2026/cycle13-webinar-qa-20260721.pdf)
- Caltrans keeps bike lanes and road diets in its list even though USDOT "recently removed" them from its Proven Safety Countermeasures ("go with the appendix") — [Q&A Q31](https://dot.ca.gov/-/media/dot-media/programs/local-assistance/documents/hsip/2026/cycle13-webinar-qa-20260721.pdf)

**B/C method (LRSM v1.8 Appendix D)**
- Combined CRF = 1 − (1−CRF1)(1−CRF2)(1−CRF3).
- Annual benefit = Σ over severities (CRFcombined × Ns × CCs) / Y, where Y is the crash data period in years.
- Life benefit = annual benefit × service life.
- BCR = life benefit / total project cost.
- Fatal and severe injury costs have been combined (KA) since Cycle 7 "to reduce the possibility of selecting an improvement project on the basis of randomness."
- Source: [HSIP Analyzer Manual July 2026, LRSM v1.8 App. D](https://dot.ca.gov/-/media/dot-media/programs/local-assistance/documents/hsip/2026/hsipanalyzermanual2026bcrfinalapp.pdf)
- **Crash costs (2026 dollars, based on HSM Table 7-1):**
  - KA: Signalized Intersection $2,379,000; Non-Signalized Intersection $3,784,000; Roadway $3,276,000.
  - B (other visible injury): $213,000.
  - C (complaint of pain): $121,000.
  - O (PDO): $20,000.
  - Source: [same](https://dot.ca.gov/-/media/dot-media/programs/local-assistance/documents/hsip/2026/hsipanalyzermanual2026bcrfinalapp.pdf)
- The worked examples project crashes as (observed ÷ years) × 20-year life. When countermeasures are stacked, each later CRF is applied to the crashes remaining after the earlier one. Example: SI05 at 55%, then SI18PB at 25% on the remaining P&B crashes — [same](https://dot.ca.gov/-/media/dot-media/programs/local-assistance/documents/hsip/2026/hsipanalyzermanual2026bcrfinalapp.pdf)

**HSIP Analyzer crash-data rules (July 2026 manual)**
- Crash period must be **between 3 and 5 years**. It can be split into one or two periods, for example to skip COVID — [HSIP Analyzer Manual](https://dot.ca.gov/-/media/dot-media/programs/local-assistance/documents/hsip/2026/hsipanalyzermanual2026bcrfinalapp.pdf)
- Caltrans treats **2020–2022 as the COVID years** that may be excluded. Provisional 2025 data is allowed — [Q&A Q38–Q40](https://dot.ca.gov/-/media/dot-media/programs/local-assistance/documents/hsip/2026/cycle13-webinar-qa-20260721.pdf)
- Up to 5 crash tables: All, Night, Ped & Bike, Emergency Vehicle, Animal. Each table takes 5 severities: Fatal, Severe Injury, Other Visible Injury, Complaint of Pain, PDO. If a database lacks injury sub-severities, all injuries go in as Other Visible Injury.
- Each crash counts once, regardless of how many vehicles or victims, and is classed by its most severe outcome.
- Sub-dataset counts cannot exceed the All dataset.
- Source: [HSIP Analyzer Manual](https://dot.ca.gov/-/media/dot-media/programs/local-assistance/documents/hsip/2026/hsipanalyzermanual2026bcrfinalapp.pdf)
- **Influence areas:**
  - New signals: all crashes within 250 ft.
  - Intersection improvements: within 250 ft in the affected directions, but only to mid-block if the next intersection is less than 500 ft away.
  - Longitudinal improvements: within the improvement limits.
  - Signs and striping: within the driver-reaction limits.
  - Extensions need documented justification.
  - Source: [same](https://dot.ca.gov/-/media/dot-media/programs/local-assistance/documents/hsip/2026/hsipanalyzermanual2026bcrfinalapp.pdf)
- "Do not include collisions unreported by law enforcement." Crashes missing from TIMS summaries may be added by hand with documentation. Crashes used in a prior call may be reused if documented — [same](https://dot.ca.gov/-/media/dot-media/programs/local-assistance/documents/hsip/2026/hsipanalyzermanual2026bcrfinalapp.pdf)
- Crash data "can be from any crash data source, but please attach relevant reports" — [Q&A Q30](https://dot.ca.gov/-/media/dot-media/programs/local-assistance/documents/hsip/2026/cycle13-webinar-qa-20260721.pdf)
- BCR applications require **Collision Diagram(s)** and **Collision List(s)**:
  - Reviewers look for "a pattern of collisions… susceptible to being reduced by the countermeasure."
  - The list must match the diagram, often "a direct output from SWITRS, Crossroads, TIMS," with excluded crashes crossed out, and must show total crashes (not victims).
  - Source: [Cycle 13 Application Instructions](https://dot.ca.gov/-/media/dot-media/programs/local-assistance/documents/hsip/2026/applicationinstructions2026.pdf)
- Other required attachments: LRSP Certification on the Caltrans template, an Engineer's Checklist signed by the engineer in responsible charge, maps, photos and the HSIP Analyzer. A Caltrans support letter is needed if the project touches the State Highway System — [Cycle 13 slides](https://dot.ca.gov/-/media/dot-media/programs/local-assistance/documents/hsip/2026/cycle13-webinar-slides-20260721.pdf)
- The HSIP Analyzer is a fillable PDF that needs Adobe Reader. It covers cost estimate, countermeasure selection, crash data and BCR — [Cycle 13 call page](https://dot.ca.gov/programs/local-assistance/fed-and-state-programs/highway-safety-improvement-program/apply-now)
- TIMS formerly hosted a B/C calculator, which "is no longer available on TIMS" — [TIMS help](https://tims.berkeley.edu/help/BC_Tool.php)

**Cycle 13 call parameters**
- Timeline: announced July 1, 2026; due **Nov 2, 2026**; HQ review Nov 2026–Feb 2027; awards Mar–Apr 2027.
- Funding: $370M total — $306M BCR and $64M set-asides. Minimum BCR **5.0**. Maximum $10M per agency. 90% reimbursement (10% local match).
- Source: [Cycle 13 slides](https://dot.ca.gov/-/media/dot-media/programs/local-assistance/documents/hsip/2026/cycle13-webinar-slides-20260721.pdf); [Kelly Mar deck via CalTAP](https://caltap.org/assets/upload/hsip%20cycle%2013%20-%20kelly%20mar%20caltrans%20(0226-0721)-0.pdf)
- BCR applications are ranked highest to lowest, and "BCR cutoff is unknown at the time of application submittal." For systemic projects, fewer locations give a higher BCR, so agencies may submit alternative versions (1a/1b/1c) — [Cycle 13 slides](https://dot.ca.gov/-/media/dot-media/programs/local-assistance/documents/hsip/2026/cycle13-webinar-slides-20260721.pdf); [Q&A Q22](https://dot.ca.gov/-/media/dot-media/programs/local-assistance/documents/hsip/2026/cycle13-webinar-qa-20260721.pdf)
- Five set-asides (no BCR): Guardrail Upgrades $22.5M, Ped Crossing Enhancements $23.4M, Lane Departure $7.2M, Bike Safety $7.2M, Tribes $3.6M. Tie-breaker: agencies with more **F+SI crashes in the last 3 years**, using SWITRS counts that Caltrans pulls itself — [Cycle 13 slides](https://dot.ca.gov/-/media/dot-media/programs/local-assistance/documents/hsip/2026/cycle13-webinar-slides-20260721.pdf); [Application Instructions](https://dot.ca.gov/-/media/dot-media/programs/local-assistance/documents/hsip/2026/applicationinstructions2026.pdf)
- History of Cycles 8–12 (applications / projects selected / $M / BCR cutoff / average BCR selected):

  | Cycle | Released | Apps | Selected | $M | BCR cutoff | Avg BCR |
  |---|---|---|---|---|---|---|
  | 8 | 11/2016 | 247 | 225 | 216.9 | 3.5 | 10.3 |
  | 9 | 12/2018 | 351 | 220 | 180.8 | 7.5 | 17.7 |
  | 10 | 3/2021 | 429 | 268 | 238.3 | 12.0 | 24.0 |
  | 11 | 3/2023 | 434 | 286 | 231.6 | 18.0 | 35.5 |
  | 12 | 2/21/2025 | 330 | 288 | 299.6 | 7.0 | 28.3 |

  Total: $1.167B for 1,287 projects — [Cycle 13 slides](https://dot.ca.gov/-/media/dot-media/programs/local-assistance/documents/hsip/2026/cycle13-webinar-slides-20260721.pdf)
- California splits HSIP 50/50 between state and local. Local HSIP is about $120M/year, with state funds via the SB 137 exchange — [Cycle 13 slides](https://dot.ca.gov/-/media/dot-media/programs/local-assistance/documents/hsip/2026/cycle13-webinar-slides-20260721.pdf)
- Delivery-based ineligibility: **[FLAG — conflicting sources]** The Kelly Mar deck says "two or more" active projects not in construction after 5 years. The webinar slides say "one." The Q&A (Q34) says the Application Instructions govern: "at least one existing HSIP project that has not been in construction phase within five years of project selection (as of 11/30/2026)" — [Application Instructions](https://dot.ca.gov/-/media/dot-media/programs/local-assistance/documents/hsip/2026/applicationinstructions2026.pdf)
- The HRRR Special Rule was not triggered for FFY 26/27. The VRU special rule applies but does not affect selection — [Q&A Q16–17](https://dot.ca.gov/-/media/dot-media/programs/local-assistance/documents/hsip/2026/cycle13-webinar-qa-20260721.pdf)
- FHWA (FARS-based) breakdown of CA fatalities by focus area: 37% roadway departure only, 18% ped/bike only, 15% intersection only, 16% multiple focus areas, 13% none — [Cycle 13 slides (FHWA section)](https://dot.ca.gov/-/media/dot-media/programs/local-assistance/documents/hsip/2026/cycle13-webinar-slides-20260721.pdf)

### Inferences
- An HSIP mode in CrashIQ must output exactly what the Analyzer takes in:
  - per-location, per-countermeasure crash counts by the 5 severities, split into All / Night / P&B / EV / Animal subsets;
  - counted per crash, not per victim;
  - clipped to 250 ft influence areas, with the 500 ft mid-block rule;
  - over a user-selected 3–5 year window, with a toggle to exclude 2020–2022.
- It must also produce the required collision diagram and a collision list that can be crossed out. CrashIQ cannot submit the PDF Analyzer for the user, but it can pre-compute every input and a shadow BCR.
- The 86-countermeasure table (CRF, life, crash-type scope) plus the KA costs by location type make a deterministic engine possible. AI should only suggest countermeasures that fit the observed crash patterns, since reviewers check for "susceptible" crash patterns.
- Because the BCR uses observed crashes without Empirical Bayes, CrashIQ's HSIP mode should *not* substitute HSM predictive or EB values. Those belong in a separate "expected crashes" view, e.g. for corridor profile or ISOAP.
- Shadow BCRs could be benchmarked against the recent cutoffs (7.0 to 18.0) to tell users whether a project is competitive, not just eligible at 5.0.

### Gaps
- I did not extract the full v1.8 NS-series table or every CRF line. Pull Tables 1–3 directly from `lrsm2026final.pdf` when building the countermeasure database.
- The Caltrans roundabout CRF procedure (dependent on ADT, rural/urban and lane count) was not located.
- The LRSM v1.8 change log against v1.7 was not reviewed.
- Whether the Analyzer discounts benefits: the formula shown has no discount rate, but I did not confirm that the Analyzer applies none internally.

---

## 2. Caltrans ICE → ISOAP and the SPICE tool

### Takeaway
Caltrans' 2013 ICE policy (TOPD 13-02) has been replaced on the State Highway System by **ISOAP** (Intersection Safety and Operational Assessment Process). The ISOAP guide is dated Sept 2024, with rollout training in Dec 2024. ISOAP has two stages and applies the Safe System approach:
- **Stage 1** screening uses CAP-X, FHWA **SPICE** (HSM-based predicted crash frequency and severity by control type) and FHWA's Safe System for Intersections (SSI) score.
- **Stage 2** uses detailed HSM analysis converted to dollars with Caltrans crash costs.

### Cited Findings
- "In 2013, Traffic Operations Policy Directive (TOPD) 13-02 established ICE as a requirement for determining traffic control at intersections." ISOAP updates that process — [ISOAP Information Process Guide (9/10/2024)](https://dot.ca.gov/-/media/dot-media/programs/traffic-operations/documents/isoap/20240910-isoap-process-info-guide--a11y.pdf)
- ISOAP is "a data-driven, performance-based framework incorporating the Safe System Approach to screen intersection strategies and identify optimal solutions for new or improved intersections that considers all users." The program page lists the ISOAP Memo, Guide, Stage 1 Long Form, Dec 2024 rollout training and a June 2025 two-day workshop — [Caltrans ISOAP page](https://dot.ca.gov/programs/traffic-operations/isoap)
- **Applies to** new intersections or major modifications on the State Highway System, including:
  - new public or private road connections, or driveways with ADT of 1,000 or more;
  - changing the traffic-control type;
  - installing a pedestrian hybrid beacon;
  - adding legs or through/turn lanes.
- **Does not apply** to restriping without widening, minor signal modifications, timing or phasing changes, movement restrictions, warning devices such as RRFBs or advance flashers, or low-volume driveways. Restriping still needs safety and operational analysis.
- Encroachment-permit and locally funded projects must complete ISOAP before submitting the permit.
- Source: [ISOAP Guide](https://dot.ca.gov/-/media/dot-media/programs/traffic-operations/documents/isoap/20240910-isoap-process-info-guide--a11y.pdf)
- Typical tools (Table 1):
  - Stage 1 (Pre-PID/PID): CAP-X, SPICE, Safe System Intersection methodology.
  - Stage 2 (PA&ED): Synchro/SimTraffic, Vistro/VISSIM, SIDRA, Rodel, HCS, HSM.
  - Source: [ISOAP Guide](https://dot.ca.gov/-/media/dot-media/programs/traffic-operations/documents/isoap/20240910-isoap-process-info-guide--a11y.pdf)
- Stage 1, Step 1.6, initial safety assessment: "The SPICE tool, Caltrans Traffic Accident Surveillance and Analysis System [TASAS] rate groups, crash modification factors, or other methods may be used." SPICE is described as an FHWA Excel tool "based on the HSM methodologies." SSI scores conflict points, kinetic energy and movement complexity. In other words, **SPICE is one permitted option, not mandated** — [ISOAP Guide](https://dot.ca.gov/-/media/dot-media/programs/traffic-operations/documents/isoap/20240910-isoap-process-info-guide--a11y.pdf)
- Stage 2: "A quantitative safety analysis is performed to show predicted crash frequency and severity for each strategy. The HSM is to be used where applicable. By utilizing Caltrans' crash costs… determine a benefit-cost ratio." The guide notes Stage 2 and Stage 1 SPICE results may differ — [ISOAP Guide](https://dot.ca.gov/-/media/dot-media/programs/traffic-operations/documents/isoap/20240910-isoap-process-info-guide--a11y.pdf)
- Some cases need no alternative-control analysis, e.g. a single stop at a T or two-way stop, unless ped/bike volume or traffic calming merits it. Single-lane roundabouts are favored when total ADT is under 25,000 and signal warrants are projected within 10 years, or where broadside crashes are high — [ISOAP Guide](https://dot.ca.gov/-/media/dot-media/programs/traffic-operations/documents/isoap/20240910-isoap-process-info-guide--a11y.pdf)
- About SPICE:
  - FHWA-SA-18-026 is "a macro-based, Microsoft Excel spreadsheet, to assess the safety performance of a variety of intersection geometry and control scenarios in terms of predicted crash frequency and severity."
  - It has a Calibration tab: SPF calibration factors default to 1.0, users can enter local factors and override CMFs.
  - It can load project inputs from a CAP-X file.
  - Source: [FHWA SPICE User Manual](https://cmfclearinghouse.fhwa.dot.gov/collateral/FHWA-SA-18-026%20SPICE%20Tool%20User%20Guide%20(Final).pdf)
- SPICE is intended for planning-level (ICE Stage 1) safety analysis — [FHWA ICE Primer](https://rosap.ntl.bts.gov/view/dot/49615/dot_49615_DS1.pdf)

### Inferences
- An ISOAP/SPICE mode should be framed as Stage 1 support. That means:
  - existing-condition crash history at the intersection (observed KABCO by type), compared to SPICE-style predicted values per alternative;
  - a conflict-point / SSI-style narrative;
  - optionally, a comparison to TASAS intersection rate groups.
- Running HSM SPFs needs AADT inputs, and calibration factors default to 1.0 unless the user supplies local ones.
- SPICE itself is Excel. CrashIQ would either reimplement the HSM Ch. 10–12 intersection SPFs or export inputs for SPICE. Either way, the CA-specific value-add is the observed crash history from CCRS, which SPICE does not provide.
- ISOAP applies only on the State Highway System. Local agencies use the FHWA ICE concept to varying degrees (local ICE policies were not researched).

### Gaps
- I could not access the ISOAP Memo (date/signatory) or the Stage 1/Stage 2 forms; forms are "contact your District ISOAP Coordinator."
- I did not confirm whether TOPD 13-02 is formally rescinded.
- The Caltrans crash cost values used in ISOAP Stage 2 were not located; they may differ from HSIP costs.
- I did not verify whether the SPICE version has been updated past the 2018 manual.

---

## 3. Caltrans Safe System / DP-36, state highway safety data (TASAS/TSAR), statewide average rates

### Takeaway
DP-36 (effective Feb 15, 2022) commits Caltrans to the Safe System approach and zero fatal and serious injuries by 2050. For the State Highway System, Caltrans publishes annual crash data. It includes **base (average) crash rates for 31 intersection rate groups**, plus highway and ramp tables, with crash costs. These sit on data.ca.gov and are the official comparison benchmark for SHS facilities. No equivalent statewide benchmark exists for local roads.

### Cited Findings
- DP-36 "Road Safety Policy," effective **February 15, 2022**, owned by the Division of Safety Programs:
  - vision to "eliminate fatalities and serious injuries on California's roadways by 2050";
  - commits to a safety-first mindset, prioritizing elimination of fatal and serious injury crashes, and "eliminating race-, age-, ability- and mode-based disparities";
  - "All Divisions shall align their programs, plans, policies, procedures, and practices with the Safe System approach."
  - Source: [DP-36 PDF](https://dot.ca.gov/-/media/dot-media/programs/safety-programs/documents/policy/dp_36-a11y.pdf); [Caltrans news release 2022-009](https://dot.ca.gov/news-releases/news-release-2022-009)
- Caltrans' annual "Crash Data on California State Highways" report covers combined crash rate, fatal plus injury rate, fatality rate, MVM travel, 3-year rates, a 5-year freeway trend and a **"Basic Average Crash Rate Table for Highway, Intersection and Ramp."** It also includes ped/bike by county, and charts by severity, time, crash type, primary crash factor, weather and lighting. Since 2020 it uses 5 severity levels: Fatal, Suspected Serious, Suspected Minor, Possible, PDO. The 2024 edition is posted — [Caltrans Annual Crash Data page](https://dot.ca.gov/programs/research-innovation-system-information/annual-collision-data)
- The 2024 SHS dataset on data.ca.gov includes "Basic Average Crash Rate Table for Intersections," which "lists average crash base rates, highway type description, and crash costs for each of the **31 rate groups** for intersection," last updated Aug 4, 2026 — [CA Open Data – 2024 Crash Data on SHS](https://lab.data.ca.gov/dataset/2024-crash-data-on-state-highway-system/07f78e23-2381-4e59-a0e7-92f0c64022fe); [dataset](https://data.ca.gov/@caltrans/2024-crash-data-on-state-highway-system)
- Caltrans says the broad highway/intersection/ramp rates in its main tables "are generally not refined enough for comparative purposes. The base or average rates included in subsequent tables should be used instead." — [2021 Crash Data on CA State Highway book](https://dot.ca.gov/-/media/dot-media/programs/research-innovation-system-information/documents/annual-collision-data/2021crashdataoncshwybook1a11y.pdf)
- SHS crash records beyond the published summaries require a CPRA request — [Caltrans Annual Crash Data page](https://dot.ca.gov/programs/research-innovation-system-information/annual-collision-data)
- The ISOAP guide still names "Caltrans Traffic Accident Surveillance and Analysis System [TASAS] rate groups" as a valid Stage 1 comparison — [ISOAP Guide](https://dot.ca.gov/-/media/dot-media/programs/traffic-operations/documents/isoap/20240910-isoap-process-info-guide--a11y.pdf)
- SafeTREC geocodes SHS crashes with the Caltrans **Transportation System Network (TSN)** postmile database — [TIMS geocoding help](https://tims.berkeley.edu/help/crashdata/switrs-geocoding.php)
- Caltrans' SHSP Crash Data Dashboard (registration required) filters 10 years of fatal and serious injury crashes by SHSP Challenge Area, severity, location, cause and demographics — [Caltrans Road Safety Data Resources](https://dot.ca.gov/programs/safety-programs/shsp/road-safety-data)

### Inferences
- For corridors on the State Highway System, CrashIQ can compute observed rates (per MVM, or per MEV for intersections) and compare them to the matching SHS base rate from the data.ca.gov tables. This is the accepted California comparison, and it echoes Caltrans' old "TSAR actual vs. average" practice.
- Local roads have no official statewide average-rate table. Comparisons there have to be peer-group or jurisdiction-internal, e.g. San Diego's mean + 1 SD method (Section 5), and should be labeled that way.
- AADT for SHS segments is available from the Caltrans Traffic Census; local AADT usually has to come from the user.

### Gaps
- "TSAR" (Table B/C reports) is internal to Caltrans. I found no current public TSAR access, nor a statement on whether TASAS has been fully replaced (TSN appears to be the current system name). Treat "TASAS/TSAR" as legacy terminology. **[FLAG]**
- The actual base-rate values and the rate-group definitions table were not downloaded.
- I did not check the current SHSP edition (the 2020–2024 SHSP is cited; a 2025+ update may exist).

---

## 4. Crash data sources: SWITRS → CCRS on data.ca.gov, TIMS, data quality

### Takeaway
CHP's public iSWITRS was shut off on **Jan 8, 2025**. Raw statewide crash data is now the **CCRS dataset on data.ca.gov**: per-year Crashes, Parties and InjuredWitnessPassengers CSVs for 2016–2026, updated daily. TIMS (UC Berkeley SafeTREC) is still the de facto practitioner tool and the one Caltrans names for HSIP. It adds SafeTREC geocoding (about 97% of records) and labels recent years "provisional." Known quality issues include incomplete geocoding, missing state-highway postmile attributes in CCRS-era records, lag before data is final, police under-reporting, and PDO exclusion in TIMS.

### Cited Findings
- "Starting 1/8/2025, ISWTRS is no longer available for public access and is replaced by California Crash Reporting System (CCRS)," linking to data.ca.gov — [CHP iSWITRS page](https://chp.ca.gov/iswtrs); confirmed by [Caltrans Road Safety Data Resources](https://dot.ca.gov/programs/safety-programs/shsp/road-safety-data)
- CCRS dataset on data.ca.gov, as of October 2026:
  - Author: California Highway Patrol. Public domain. Frequency "Daily." Last updated Oct 7–8, 2026.
  - Per-year CSVs for **2016 through 2026**: Crashes_YYYY, Parties_YYYY, InjuredWitnessPassengers_YYYY. Crashes_2025 is 179 MB; Crashes_2024 is 188 MB; Crashes_2026 (partial year) is 126 MB.
  - **[FLAG]** The page shows "Created September 30, 2026," which suggests the dataset was recently republished or re-created. Resource IDs may change, so CrashIQ should not hard-code them.
  - Source: [data.ca.gov CCRS](https://data.ca.gov/dataset/ccrs)
- CCRS is described as "a database that collects, and processes data gathered from a crash scene," available to CHP, allied agencies, researchers and the public — [OTS Data Sources](https://www.ots.ca.gov/data-sources/)
- The CHP Crash Investigation Manual (HPM 110.5) standardizes statewide crash reporting. SWITRS dates from 1972 — [CHP HPM 110.5](https://chp.ca.gov/siteassets/policy/hpm/hpm-110.5/hpm-110.5-crash-investigation-manual.pdf)
- TIMS news:
  - "2024 Final and 2025–2026 Provisional SWITRS Update" (Sep 28, 2026).
  - "2026 Q1 SWITRS Added & 2024–2025 SWITRS Updated" (Jun 22, 2026).
  - "2020–2024 Traffic Safety Dashboard" (Sep 21, 2026).
  - Source: [TIMS home](https://tims.berkeley.edu/)
- **[FLAG — internal inconsistency]** The TIMS SWITRS help page still says CHP "hasn't released the 2024 SWITRS Annual Report… so we say provisional for 2024 and later datasets," which conflicts with the Sep 2026 "2024 Final" news item. The help page is likely stale. Either way, data is "final" only once CHP publishes the annual report — [TIMS SWITRS overview](https://tims.berkeley.edu/help/crashdata/switrs.php)
- Schema: SWITRS is hierarchical — CRASH (one row per crash) → PARTY → VICTIM. Injury severity sits in VICTIM. Uninjured parties are absent from VICTIM — [TIMS SWITRS overview](https://tims.berkeley.edu/help/crashdata/switrs.php)
- Geocoding:
  - "Roughly 97% of SWITRS crashes are geocoded using SafeTREC's workflow." `POINT_X/POINT_Y` hold the SafeTREC geocode; `LATITUDE/LONGITUDE` hold the officer GPS.
  - TIMS maps show only SafeTREC-geocoded crashes.
  - Source: [TIMS SWITRS overview](https://tims.berkeley.edu/help/crashdata/switrs.php)
- Geocoding method:
  - Local roads are matched to intersections with an Esri StreetMap Premium locator on PRIMARY ROAD, SECONDARY ROAD, COUNTY and CITY, then officer distance/direction offsets are applied.
  - State highways use linear referencing to Caltrans TSN postmiles.
  - "Since 2015, the California Highway Patrol has used the California Collision Reporting System (CCRS) to submit crashes electronically. Because the new system does not return highway attributes to SWITRS, SafeTREC evaluates the accuracy of officer-supplied GPS coordinates and supplements them with our linear-referencing method."
  - Source: [TIMS SWITRS geocoding](https://tims.berkeley.edu/help/crashdata/switrs-geocoding.php)
- LRSM: "SafeTREC is not able to incorporate all SWITRS crashes into TIMS due to poor crash location descriptions… TIMS includes the majority of California fatal and injury crashes but does not include Property Damage Only collisions." — [LRSM v1.7 §2.2](https://dot.ca.gov/-/media/dot-media/programs/local-assistance/documents/hsip/2024/lrsm2024-v2.pdf)
- TIMS tool list includes Query & Map, GIS Map, **Crash Diagram**, Heat Map, **Safety PM Target Setting**, **ATP Maps & Summary**, Safe Routes to School Map, and SWITRS Summary — [TIMS help nav](https://tims.berkeley.edu/help/crashdata/switrs-geocoding.php)
- CATSIP county ped/bike data uses "SWITRS 2020–2024; provisional 2025 data as of June 08, 2026" — [CATSIP](https://catsip.berkeley.edu/resources/crash-data/pedestrian-and-bicycle-crash-data-county)
- Under-reporting: SF found severe injuries treated at Zuckerberg SF General that were never reported to police. When linked, police-coded severity often changed: 65% of police "severe" injuries remained severe after hospital review (2022 update) — [SFCTA 2022 HIN update](https://www.sfcta.org/sites/default/files/2022-11/SFCTA_Board_SFDPHHighInjuryNetwork_2022-11-15.pdf); [SF 2024 HIN methodology](https://media.api.sf.gov/documents/2024_Vision_Zero_Network_Update_Methodology_For_Steering_Review_20260804_V.4_ca_for_HC.pdf)
- Other state sources: the OTS Crash Rankings (by count, VMT or population), CDPH EpiCenter (hospital/ED injury data) and the Caltrans Traffic Census (SHS AADT) — [TIMS SWITRS overview](https://tims.berkeley.edu/help/crashdata/switrs.php); [Caltrans Road Safety Data Resources](https://dot.ca.gov/programs/safety-programs/shsp/road-safety-data)

### Inferences
- Pulling CCRS directly gives CrashIQ data newer than TIMS, including the partial current year. But CrashIQ must do its own geocoding QA. CCRS rows carry officer GPS and road names; TIMS adds the cleaned SafeTREC geocode and state-highway postmile matching.
- When a user draws a corridor, CrashIQ should count crashes with missing or implausible coordinates and match by road name where it can. It should report a "located vs. unlocated" share, because ungeocoded crashes are a known (~3%+) gap.
- Reports should flag every year after the last CHP annual report as **provisional**. HSIP allows provisional years, but counts can change.
- CCRS's severity coding and table names (InjuredWitnessPassengers, not VICTIM) differ from legacy SWITRS/TIMS. CrashIQ needs a mapping layer to KABCO and to the HSIP Analyzer's 5 severities.
- Whether raw CCRS includes PDO crashes, which TIMS does not, matters for HSIP: PDO is worth $20k per crash in the BCR. This needs verifying against the data dictionary.

### Gaps
- I did not retrieve the CCRS data dictionary/field list, so I could not confirm field names, severity codes, PDO inclusion or coordinate completeness.
- I found no published statistic on CCRS reporting lag by agency, or on non-CHP agency completeness (e.g., LAPD/SFPD submission timing).
- Why the dataset shows a Sept 2026 "Created" date is unexplained.

---

## 5. SS4A Action Plans, Vision Zero, High-Injury Networks, LRSP requirements

### Takeaway
To be eligible for local HSIP, an agency needs an LRSP **or equivalent**: an SSAR, a Vision Zero Action Plan, or (per Caltrans) an SS4A Action Plan, updated or validated every 5 years. Caltrans no longer funds LRSPs; it points agencies to SS4A. SS4A requires a "safety analysis" covering all roadways regardless of owner, and a geospatial high-injury network. California HIN methods vary:
- SF: linked police + hospital + death records, KSI per mile on quarter-mile sliding sections.
- LA: KSI with mode weighting plus contextual/equity factors, with mode-specific HINs.
- San Diego: annual injury/fatal "High Crash Location" lists, with rate = mean + 1 SD.

### Cited Findings
**LRSP / HSIP eligibility**
- "In order to apply for the HSIP funds, an agency must have completed their LRSP or an equivalent of the LRSP, such as Systemic Safety Analysis Report (SSAR) or Vision Zero Action Plan… must be updated and validated at least every five years… self-certify." Board approval is "strongly recommended" but not required — [Caltrans LRSP page](https://dot.ca.gov/programs/local-assistance/fed-and-state-programs/highway-safety-improvement-program/local-roadway-safety-plans); [Cycle 13 Application Instructions](https://dot.ca.gov/-/media/dot-media/programs/local-assistance/documents/hsip/2026/applicationinstructions2026.pdf)
- "All LRSP funding has been awarded… Caltrans does not accept new LRSP applications." "By completing the [SS4A] Action Plan, the agency is considered meeting the LRSP requirement." — [Caltrans LRSP page](https://dot.ca.gov/programs/local-assistance/fed-and-state-programs/highway-safety-improvement-program/local-roadway-safety-plans)
- History: SSARP was established in 2016 and evolved into LRSP in late 2019 to cover enforcement, education and EMS, not just engineering — [LRSM v1.7](https://dot.ca.gov/-/media/dot-media/programs/local-assistance/documents/hsip/2024/lrsm2024-v2.pdf)
- For Cycle 13, an LRSP older than 5 years may be updated, validated or "worked concurrently with application" — [Cycle 13 slides](https://dot.ca.gov/-/media/dot-media/programs/local-assistance/documents/hsip/2026/cycle13-webinar-slides-20260721.pdf)

**SS4A**
- Action Plan components: (1) leadership commitment and goal setting, (2) planning structure, (3) **safety analysis**, (4) engagement and collaboration, (5) policy and process changes, (6) strategy and project selections, (7) progress and transparency — [USDOT SS4A Action Plans](https://www.transportation.gov/grants/ss4a/comprehensive-safety-action-plans)
- Safety analysis means a "baseline level of crashes involving fatalities and serious injuries," covering locations, severity, contributing factors and crash types by road user. It includes systemic analysis (high-risk road features, built environment, demographics) and covers "all roadways within the jurisdiction, without regard for ownership." From it, "a geospatial identification of higher-risk locations is developed (a high-injury network or equivalent)." — [USDOT SS4A Action Plans](https://www.transportation.gov/grants/ss4a/comprehensive-safety-action-plans)
- An Action Plan used for an FY26 Implementation Grant must be "finalized or updated between 2021 and May 26, 2026." — [USDOT SS4A Action Plans](https://www.transportation.gov/grants/ss4a/comprehensive-safety-action-plans)
- **[FLAG]** Caltrans' LRSP page says SS4A "is open for applications. The deadline… May 26, 2027." This is probably a later NOFO round. Program funding was "$5 billion… over 5 years, 2022–2026" per FHWA, so post-2026 SS4A funding depends on reauthorization. Verify before relying on it — [Caltrans LRSP page](https://dot.ca.gov/programs/local-assistance/fed-and-state-programs/highway-safety-improvement-program/local-roadway-safety-plans); [Cycle 13 slides (FHWA)](https://dot.ca.gov/-/media/dot-media/programs/local-assistance/documents/hsip/2026/cycle13-webinar-slides-20260721.pdf)
- SS4A is administered directly by FHWA, not by Caltrans — [Q&A Q8](https://dot.ca.gov/-/media/dot-media/programs/local-assistance/documents/hsip/2026/cycle13-webinar-qa-20260721.pdf)

**San Francisco HIN (2024 update)**
- Built by SFDPH with SFMTA. SF was "the first city in the country to use mapped hospital data along with police injury data." The 2024 update adds record linkage of SFPD TransBASE crash reports, ZSFG trauma patients and CDPH death certificates (VRBIS).
- Method: scores overlapping quarter-mile sections, uses an injury-per-mile threshold, and sets start and end points at **10 KSI per mile**.
- Result: the network is **13.3% of street miles and captures 74% of severe and fatal injuries**. Pedestrians and cyclists are 47% of KSI on the HIN. 70% of the miles were retained from the 2022 HIN.
- Source: [SF 2024 HIN methodology](https://media.api.sf.gov/documents/2024_Vision_Zero_Network_Update_Methodology_For_Steering_Review_20260804_V.4_ca_for_HC.pdf); [Vision Zero SF Maps & Data](https://www.visionzerosf.org/maps-data/)

**Los Angeles (Vision Zero Safety Study, Jan 2024)**
- KSI collisions rose from 1,472 (2017) to 1,658 (2021), about +13%. Pedestrians were involved in 38% of KSI.
- The new HIN is **549 miles (7.5% of streets) and captures 61.8% of KSI**. There are separate bicycle, pedestrian, motorcycle and vehicle HINs.
- The method adds contextual factors and equity: the top 20% of census tracts by the Health Atlas index. A systemic analysis identifies 16 risk factors and 24 collision profiles, and a high-scoring subset of corridors and intersections is ranked.
- The prior 2016/2018 HIN used collision data only: 65% of KSI on 6% of streets (over 450 miles).
- Source: [LADOT Vision Zero Safety Study 2024](https://ladot.lacity.gov/sites/default/files/documents/la-vision-zero-safety-study-2024.pdf)
- SCAG maintains a regional HIN, updated in 2022 with a new method — [SCAG HIN hub](https://transportation-safety-scag.hub.arcgis.com/pages/high-injury-network)

**San Diego (annual High Crash Location analysis)**
- The 2024 memo (dated Mar 24, 2025) "uses injury and fatal crashes, excluding property-damage-only crashes." It produces lists for Crash Rate, Crash Pattern, Crash Frequency – Intersection, and Crash Frequency – Signalized Left Turn.
- High crash rate means at least 1 SD above the mean (mean 0.51, SD 0.31 per million entering vehicles). It is computed only for the 38 intersections with 5 or more crashes.
- Each location is tagged with a Climate Equity "access to opportunity" label. Engineers must reply with findings, proposed improvements and cost estimates by Sept 30.
- Source: [City of San Diego 2024 High Crash Locations memo](https://www.sandiego.gov/sites/default/files/2025-03/2024-high-crash-locations.pdf); [SD Vision Zero safety initiatives](https://www.sandiego.gov/vision-zero/safety-initiatives)

### Inferences
- An LRSP/SS4A mode needs network-wide outputs, not just corridor outputs:
  - a jurisdiction-wide KSI baseline and trends;
  - a breakdown by mode, crash type and primary collision factor;
  - systemic risk-factor and collision-profile tables;
  - a HIN generated by configurable sliding-window KSI per mile with mode weighting.
- That is more than "draw a corridor." It suggests a "jurisdiction boundary" input.
- No single California HIN standard exists. CrashIQ should offer documented presets (SF-style KSI/mile threshold, LA-style weighted plus contextual, mean + 1 SD crash-rate screening) and state the method in the report.
- Police-only data misses hospital-identified severe injuries, as SF shows. CrashIQ should disclose that CCRS-based KSI is a lower bound.
- San Diego shows how an annual city screening works: injury/fatal only, a single calendar year, rate screening with a minimum-crash threshold, and equity tags. That is a likely recurring-use case for a corridor/network tool.

### Gaps
- I did not research the official LRSP content checklist (Caltrans/NACE template). The Caltrans page links the NACE template, but it was not reviewed.
- San Diego's HIN (separate from the HCL lists) and its Vision Zero Action Plan methods were not extracted.
- I did not verify SS4A FY2027 NOFO details.

---

## 6. Typical CA traffic impact study / VMT-era transportation study safety section; ATP safety

### Takeaway
Since SB 743 (statewide July 1, 2020), CEQA transportation impact analysis in California runs on VMT, not LOS. Caltrans' 2020 TISG says safety review of the State Highway System continues and promised a "simplified safety analysis approach" focused on multimodal conflicts and access management. Safety sections are therefore now non-CEQA local or Caltrans review items, not CEQA significance tests. ATP (2027, Cycle 8) scores safety on ped/bike collision history plus hazards and countermeasures.

### Cited Findings
- "VMT analysis replaces level of service… Caltrans' primary review focus for a land use project's impacts is now VMT." It cites OPR's Dec 2018 Technical Advisory. VMT became the standard CEQA metric on July 1, 2020 — [Caltrans VMT-Focused TISG (May 20, 2020)](https://dot.ca.gov/-/media/dot-media/programs/transportation-planning/documents/sb-743/2020-05-20-approved-vmt-focused-tisg-a11y.pdf)
- "Determining how the State Highway System may otherwise be affected by a land use project may still be necessary at times, particularly as it relates to the safety of the traveling public. Additional future guidance… will include a simplified safety analysis approach that reduces risks to all road users and focuses on multi-modal conflict analysis as well as access management issues. With this guidance the Department will transition away from requesting LOS." — [Caltrans TISG](https://dot.ca.gov/-/media/dot-media/programs/transportation-planning/documents/sb-743/2020-05-20-approved-vmt-focused-tisg-a11y.pdf)
- ISOAP applies to land-development connections to state highways, e.g. new driveways with ADT of 1,000 or more and encroachment permits. This is a concrete safety-analysis trigger for development projects on the SHS — [ISOAP Guide](https://dot.ca.gov/-/media/dot-media/programs/traffic-operations/documents/isoap/20240910-isoap-process-info-guide--a11y.pdf)
- 2027 ATP (Cycle 8) Guidelines, criterion C "Safety": "The score considers the identified safety hazards for active transportation users as well as the history of pedestrian and bicycle collisions and the selected countermeasures. The applicants must demonstrate that the project location is a priority, and the project will remedy the identified safety hazards." — [CTC 2027 ATP Guidelines](https://catc.ca.gov/-/media/ctc-media/documents/programs/atp/cycle8/2027-atp-guidelines-a11y.pdf)
- Separate scoring rubrics exist for large, medium and non-infrastructure ATP applications — [Caltrans ATP Cycle 8 page](https://dot.ca.gov/programs/local-assistance/fed-and-state-programs/active-transportation-program/cycle8)
- A secondary source reports a draft Cycle 8 fund estimate of about $619.3M. Unverified against CTC primary documents — [CitizenPortal summary](https://citizenportal.ai/articles/7627865/california/executive/agencies-under-office-of-the-governor/transportation-commission/transportation-commission-reviews-cycle-8-atp-scoring-rubrics-confirms-6193m-draft-fund-estimate-and-key-deadlines)
- TIMS offers an "ATP Maps & Summary" tool for ATP crash data — [TIMS help nav](https://tims.berkeley.edu/help/crashdata/switrs-geocoding.php)

### Inferences
- A TIS/TIA safety-section mode should not claim to be CEQA significance analysis. A typical VMT-era safety section is a local-guideline or Caltrans-review item. It would include study-area crash history (3–5 years, by severity, type and mode), rates compared to averages where AADT exists, crash-pattern review at the project access and adjacent intersections, multimodal conflicts, access management, sight distance, and an ISOAP trigger check for SHS connections.
- For ATP, CrashIQ should produce ped/bike-only crash history inside the project limits, with severity and maps, plus a hazard/countermeasure narrative tied to the observed crash types. The rubric's point allocation (not extracted) determines how much depth is needed.

### Gaps
- Whether Caltrans has published the promised simplified safety-analysis guidance (a later "safety review" guide for LD-IGR) was not confirmed in this session. **[FLAG]** The 2020 TISG language is now 6 years old.
- I reviewed no city or county TIS guidelines (e.g., LA DOT TAG, San Jose, SANDAG). The "typical safety section" description above is an inference, not sourced practice.
- The ATP Cycle 8 safety point weights and specific crash-data rules (years, sources, buffers) were not extracted from the rubric PDFs.
