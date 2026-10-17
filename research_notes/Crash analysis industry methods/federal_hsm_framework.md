# US Federal / HSM-Based Crash Analysis Framework (industry standard, as of Oct 2026)

Scope: the standard US methods for (a) finding existing crash problem locations and patterns and (b) predicting future crashes, plus the federal programs and tools around them. Research date: 2026-10-17. Things that changed in 2025–2026 are flagged **[2025/2026 CHANGE]**. Older material is marked with its date.

---

## 1. HSM Part B: the Roadway Safety Management Process and network screening measures

### Takeaway
HSM Part B sets out a six-step cycle: network screening → diagnosis → countermeasure selection → economic appraisal → project prioritization → safety effectiveness evaluation. Within network screening, the HSM treats measures built on *expected* crash frequency from Empirical Bayes (EB) as best practice, especially excess expected crash frequency. The reason is that raw crash counts and crash rates are biased by regression to the mean (RTM). Crash rates also wrongly assume crashes rise linearly with traffic volume. HSM2 keeps this structure and adds an areawide (macro-level) step and a systemic track that runs alongside the crash-based track.

### Cited Findings
- HSM1 Part B covers "suggested steps to monitor and reduce crash frequency and severity on existing roadway networks." Its chapters are Ch 4 Network Screening, Ch 5 Diagnosis, Ch 6 Select Countermeasures, Ch 7 Economic Appraisal, Ch 8 Prioritize Projects, and Ch 9 Safety Effectiveness Evaluation. Part B also includes methods for evaluating single treatments, groups of treatments, or whole programs, and for calculating a CMF. — [AASHTO HSM Content page](https://www.highwaysafetymanual.org/Pages/hsm_parts.aspx)
- AASHTO says Chapter 4's newer screening measures "shift the safety analysis focus away from traditional crash rates." Its reasoning: "Crash rate analysis assumes there is a linear relationship between traffic volume and the frequency of crashes. A focus on expected crash frequency can account for regression to the mean… Using network screening methods that estimate expected average crash frequency provides a more stable list of locations that might respond to safety improvements than lists prepared with traditional methods." — [AASHTO HSM Content page](https://www.highwaysafetymanual.org/Pages/hsm_parts.aspx)
- The HSM (2010) reports 13 network screening measures. They run from basic ones ("Average Collision Frequency", "Collision Rate") to more robust ones such as "EPDO Average Collision Frequency with EB Adjustment", which estimates the long-term expected number of collisions. — [Journal of Transport Geography, hotzone identification paper](https://sciencedirect.com/science/article/pii/S0966692313002317)
- The HSM's named measures include Crash Frequency, Crash Rate, Relative Severity Index, EPDO, and others. — [Evaluation of performance measures for hotspot identification (J. Transportation Safety & Security)](https://tandfonline.com/doi/full/10.1080/19439962.2015.1048015)
- A peer-reviewed analysis of HSM methods for identifying high-crash locations says "the most reliable methods are based on empirical Bayes (EB) procedure." — [Accid. Anal. Prev., Poisson-Tweedie paper (PubMed)](https://pubmed.ncbi.nlm.nih.gov/32036107)
- FHWA network screening guide (FHWA-SA-17-008) gives a five-step process: (1) establish a focus, (2) identify the site/facility types to screen (reference populations), (3) select performance measures, (4) choose a screening method, (5) screen and evaluate results. It says screening uses "crash, roadway, and traffic volume data." — [FHWA, Screening Your Network to Improve Roadway Safety Performance](https://highways.dot.gov/safety/data-analysis-tools/systemic/screening-your-network-improve-roadway-safety-performance)
- That FHWA guide calls the following the HSM's "advanced" crash-data methods and says they give "more reliable outputs compared to the traditional methods": expected average crash frequency with EB adjustment, excess expected average crash frequency with EB adjustment, and probability of specific crash types exceeding a threshold proportion. It recommends using more than one measure to raise confidence. — [FHWA screening guide](https://highways.dot.gov/safety/data-analysis-tools/systemic/screening-your-network-improve-roadway-safety-performance)
- According to FHWA, the "probability of specific crash types exceeding threshold proportion" measure (HSM p. 4-12) "is not affected by regression-to-the-mean bias." It needs only crash type and location data, so agencies without volume data can use it. — [FHWA screening guide](https://highways.dot.gov/safety/data-analysis-tools/systemic/screening-your-network-improve-roadway-safety-performance)
- Real-world use: a study of small municipalities applied EPDO average crash frequency with EB adjustment and Level of Service of Safety (LOSS), using jurisdiction-specific crash prediction models by intersection type. — [TRR, Roadway Safety Management in Small Municipalities](https://journals.sagepub.com/doi/10.1177/0361198120910147)
- **HSM2 Part B changes [pending publication]:** Part B is restructured into an "Areawide Approach" (new Ch 5), a "Crash-Based Approach" (Ch 6 Network Screening through Ch 11 Effectiveness Evaluation), and a "Systemic Approach" (new Ch 12). Ch 6 Network Screening **adds network-screening-level SPFs** for segments, intersections (including roundabouts), and ped/bike collisions. It **removes** two "less relevant" measures: excess predicted average crash frequency using method of moments, and excess predicted average crash frequency using SPFs. Ch 9 Economic Appraisal updates crash costs. Ch 10 Prioritization has "no significant changes." Ch 11 is rewritten to include how to develop CMFs (from NCHRP 17-63), including crash modification functions. — [AASHTO HSM2 Update webinar for State DOTs, June 18, 2024](https://www.highwaysafetymanual.org/Documents/AASHTO_HSM2_Update_webinar_20240618_Combined.pdf)
- HSM2 new Ch 5 (Areawide): macro-level crash prediction models for Census Block Groups, within MPO boundaries or statewide. Uses include comparing growth scenarios, setting targets, and assessing large developments. — [AASHTO HSM2 webinar 2024](https://www.highwaysafetymanual.org/Documents/AASHTO_HSM2_Update_webinar_20240618_Combined.pdf); also block group/tract/TAZ/city/county per [HDR interview with Dan Cook](https://hdrinc.com/insights/experts-talk-exploring-updates-highway-safety-manual-dan-cook)
- An HSM2 contributor says HSM2 "moves us beyond outdated crash rate analysis… Instead of using crash rates and observed crash frequencies that can sometimes lead us to fix locations that don't actually have a problem, HSM2 focuses on methods that are backed by better data and more accurate predictions." — [HDR, Experts Talk: HSM updates (Dan Cook)](https://hdrinc.com/insights/experts-talk-exploring-updates-highway-safety-manual-dan-cook)
- Federal regulation sets HSIP prioritization criteria: priorities must consider "(i) The potential reduction in fatalities and serious injuries; (ii) The cost effectiveness of the projects and the resources available; and (iii) The priorities in the SHSP." States must also have a process for engineering studies "such as road safety audits." — [23 CFR 924.9(a)(5)–(6), eCFR current as of 2026-09-23](https://www.ecfr.gov/current/title-23/section-924.9)

### Inferences
- The measures fall into three tiers by rigor:
  - Tier 1 (observed data, RTM-biased): crash frequency, crash rate, critical rate, EPDO, RSI.
  - Tier 2 (adds an SPF, not yet EB): excess predicted frequency, LOSS.
  - Tier 3 (best practice): EB expected or excess expected frequency, including EPDO-weighted EB.
  - A tool that offers only Tier 1 measures, which is typical of simple crash-mapping tools, does not match HSM best practice.
- Critical rate is still common in state practice. It is partly volume-normalized and includes a statistical threshold, but it is not EB. The HSM2 webinar did not list it among removed measures, so it probably stays in HSM2 (not confirmed).
- For CrashIQ (a corridor tool): sliding-window and peak-searching segment screening with EB excess expected crashes, and KA- or KAB-weighted variants, is what the commercial/AASHTO tools advertise (see §3). Diagnosis outputs (collision diagrams, crash-type proportions versus a reference population) belong in Part B Ch 5/7.

### Gaps
- I could not fetch the HSM1 Table 4-1 matrix of measures × data needs or the exact list of all 13 measures from a primary source (the HSM is a paid AASHTO publication). From standard HSM knowledge (not re-verified online this session), the 13 are: average crash frequency; crash rate; critical rate; EPDO average crash frequency; relative severity index; excess predicted average crash frequency using method of moments; LOSS; excess predicted average crash frequency using SPFs; probability of specific crash types exceeding threshold proportion; excess proportion of specific crash types; expected average crash frequency with EB adjustment; EPDO average crash frequency with EB adjustment; excess expected average crash frequency with EB adjustment. Check this against the HSM itself before quoting it.
- No primary source confirms the critical rate formula or HSM2's treatment of critical rate.

---

## 2. HSM Part C predictive method (SPFs, CMFs/AFs, calibration, EB) and HSM2 status

### Takeaway
Part C predicts crashes for a site in three steps. First, a base-condition SPF (a function of AADT and length or entering volumes) gives a base prediction. That is multiplied by adjustment factors / CMFs for site conditions that differ from base, and then by a local calibration factor. Finally, the result is combined with the site's observed crashes using EB weighting to get an *expected* crash frequency. HSM2 is still **not confirmed as published as of Oct 2026**. AASHTO, FHWA and TRB all said release was "anticipated 2026"; in 2023–2024 the estimate had been 2025. HSM2 adds many new facility types, ped/bike SPFs, KABC/KAB severity SPFs, directional freeway models, and new chapters on general Part C concepts and on selecting and applying CMFs.

### Cited Findings
- "Part C provides a predictive method for estimating expected average crash frequency at an individual site. The predictive method relies on safety performance functions (SPF)… equations that estimate predicted average crash frequency as a function of traffic volume and roadway characteristics (e.g., number of lanes, median type, intersection control, number of approach legs)." HSM1 Part C chapters: Ch 10 Rural Two-Lane Two-Way, Ch 11 Rural Multilane, Ch 12 Urban & Suburban Arterials. — [AASHTO HSM Content](https://www.highwaysafetymanual.org/Pages/hsm_parts.aspx)
- Freeways (Ch 18) and ramps/interchanges (Ch 19) predictive methods were added in the 2014 Supplement. The HSM was "first published in 2010 with a supplement for freeways published in 2014." — [AASHTO HSM About](https://highwaysafetymanual.org/Pages/About.aspx); [FHWA, Future Plans for IHSDM (2025)](https://highways.dot.gov/media/110891)
- Part D CMFs "quantify the change in average crash frequency as a result of geometric or operational modifications to a site that differs from set base conditions." HSM1 Part D chapters: 13 Roadway Segments, 14 Intersections, 15 Interchanges, 16 Special Facilities, 17 Road Networks. — [AASHTO HSM Content](https://www.highwaysafetymanual.org/Pages/hsm_parts.aspx)
- The EB procedure (Hauer et al. 2002) "is the workhorse of highway safety analysis: it combines a Safety Performance Function with observed crash counts to produce shrinkage estimates of segment-level crash rates." It holds several quantities fixed at calibrated values. (Context: a 2026 arXiv preprint proposes a hierarchical Bayesian generalization for segments missing AADT.) — [arXiv 2605.27889](https://arxiv.org/abs/2605.27889)
- Researchers note that the EB method recommended in the HSM does not capture spatial dependence well, which has led to spatially adaptive EB proposals. These are research, not standard practice. — [TRID record 2643861](https://trid.trb.org/View/2643861)
- Calibration: IHSDM 2021 includes a Calibration Utility "to assist agencies in implementing the calibration procedures described in the appendix to HSM part C." — [FHWA, Future Plans for IHSDM (2025)](https://highways.dot.gov/media/110891)
- **HSM2 status [2025/2026 CHANGE]:**
  - FHWA (2025): "it is likely that [AASHTO] will publish the [HSM2] in 2026." Agencies "might need some time to transition from using HSM1 methods and models to the new or recalibrated HSM2 models (e.g., to calibrate the new HSM2 models and vet the new models for their use)." — [FHWA, Future Plans for IHSDM (2025)](https://highways.dot.gov/media/110891)
  - TRB webinar of March 2, 2026 described HSM2 release as "anticipated in 2026." — [TRB Webinar 1905](https://webinar.mytrb.org/Webinars/Details/1905)
  - AASHTOWare (Oct 7, 2025): HSM2 "is on its way." — [AASHTOWare webinar recap](https://aashtoware.org/story/recent-webinar-recap)
  - The FHWA-managed HSM2 Implementation pooled fund TPF-5(516) started 2025-04-18 with $1,568,000. Caltrans is among about 25 sponsor states. Its record still says "anticipated publication… estimated 2025," which shows the schedule slipped. — [TRB RIP 2169804](https://rip.trb.org/View/2169804)
  - The 2024 AASHTO schedule showed committee review and balloting running through 2025. — [AASHTO HSM2 webinar 2024](https://www.highwaysafetymanual.org/Documents/AASHTO_HSM2_Update_webinar_20240618_Combined.pdf)
  - The AASHTO May 2025 catalog still lists only "Highway Safety Manual, 1st Edition, with 2014 Supplement (HSM-1-M)." — [AASHTO Design/Traffic/Safety catalog May 2025](https://downloads.transportation.org/publications/catalogs/aashto_designsafety_catalog.pdf)
  - The HSM website (fetched Oct 2026) still promotes the "upcoming AASHTO review and ballot process" and has no purchase notice for HSM2. — [highwaysafetymanual.org](https://www.highwaysafetymanual.org/Pages/default.aspx)
- HSM2 was developed through NCHRP 17-71 and 17-71A ("Proposed AASHTO HSM, Second Edition"). The 17-71A objective was "to complete the work begun in NCHRP Project 17-71 to develop and prepare a proposed HSM2 in a format suitable" for AASHTO. — [TRB RIP 1739066](https://rip.trb.org/View/1739066). Companion: NCHRP 2025 report *Quantitative Safety Analyses for Highway Applications* (doi:10.17226/28851) documents modifications to HSM1 materials for HSM2. — [National Academies Press](https://nationalacademies.org/read/28851/chapter/7)
- **HSM2 chapter outline:**
  - Part A: Ch 2 Road Safety Principles (adds a Safe System section), Ch 3 Human Factors, **new Ch 4 Pedestrians & Bicyclists**.
  - Part B: Ch 5–12 (see §1).
  - Part C: **new Ch 13 General Concepts** (SPFs and adjustment factors, crash assignment, the EB method, calibration, developing jurisdiction-specific SPFs, estimating change in crashes), then Ch 14 Rural Two-Lane, Ch 15 Rural Multilane, Ch 16 Urban/Suburban Arterials, Ch 17 Freeways, Ch 18 Ramps.
  - Part D: **new Ch 19 Selecting CMFs and Ch 20 Applying CMFs** (confidence intervals; common misapplications).
  - [AASHTO HSM2 webinar 2024](https://www.highwaysafetymanual.org/Documents/AASHTO_HSM2_Update_webinar_20240618_Combined.pdf)
- **HSM2 Part C model changes:**
  - Rural two-lane and multilane: new total/KABC/KAB SPFs (NCHRP 17-62) replace HSM1 SPFs; new intersection types (NCHRP 17-68); roundabouts (17-70); ped/bike methods (17-84).
  - Urban arterials: total-crash SPFs replaced (17-62); six-plus-lane and one-way arterials (17-58); five new intersection types (17-68); roundabouts (17-70); ped/bike (17-84).
  - Freeways: bidirectional models replaced by **directional** models.
  - Ramps: SPDI and tight diamond interchanges added.
  - SPFs are "calibrated, where appropriate, to a common state."
  - Terminology: HSM2 says "adjustment factors (AFs)" inside Part C. "CMF" is kept only for Clearinghouse/Part D CMFs.
  - [AASHTO HSM2 webinar 2024](https://www.highwaysafetymanual.org/Documents/AASHTO_HSM2_Update_webinar_20240618_Combined.pdf)
- NCHRP research feeding HSM2: 17-50, 17-58, 17-62, 17-63, 17-68, 17-70, 17-72 (CMF update), 17-73 (systemic pedestrian), 17-77 (quantitative systemic analysis guide), 17-78 (reliability of CPMs), 17-81 (macro-level planning chapter), 17-84 (ped/bike SPFs), 17-89/17-89A (part-time shoulders; HOV/HOT). — [AASHTO HSM2 webinar 2024](https://www.highwaysafetymanual.org/Documents/AASHTO_HSM2_Update_webinar_20240618_Combined.pdf)
- FHWA expects HSM2 to make IHSDM's Crash Prediction Module partly or fully obsolete over time, because new ped/bike models and others "differ significantly from the HSM1 form." Some existing models were recalibrated for HSM2 using single-state calibration (NCHRP 17-72, 17-71A). — [FHWA, Future Plans for IHSDM (2025)](https://highways.dot.gov/media/110891)
- Liability framing: a TRB March 2026 webinar covered how practitioners should word safety performance findings so they "withstand professional and legal scrutiny" ahead of HSM2. — [TRB Webinar 1905](https://webinar.mytrb.org/Webinars/Details/1905)

### Inferences
- Core Part C equations, from HSM1 knowledge and **not re-verified online this session**:
  - N_predicted = N_spf,base × (CMF1 × CMF2 × … × CMFn) × C, where C is the local calibration factor.
  - Site-specific EB: N_expected = w × N_predicted + (1 − w) × N_observed, with w = 1 / (1 + k × ΣN_predicted), where k is the SPF overdispersion parameter.
  - Check these against HSM Ch 3/Part C Appendix A before putting them in product documentation.
- HSM2 adds KABC/KAB SPFs and ped/bike SPFs. A tool that predicts only total crashes, or uses only HSM1 models, will look dated once HSM2 is out. California-specific calibration factors and SPFs are needed for credible predictions in CA.
- Transition is likely to take years. FHWA expects agencies to keep using HSM1 while they calibrate HSM2 models, so supporting both editions (or configurable SPF libraries) is a sensible design choice.

### Gaps
- **I could not confirm whether HSM2 was formally published between March and October 2026.** No AASHTO store listing, press release, or ballot result was found. Treat it as "imminent / not confirmed published."
- California's own SPF and calibration-factor status (Caltrans) was outside this researcher's scope and not checked.

---

## 3. FHWA / AASHTO programs and tools (Safe System, NRSS, HSIP, SSPST/Systemic Safety User Guide, PSCs, CMF Clearinghouse, IHSDM, AASHTOWare Safety, MMUCC, KABCO)

### Takeaway
The technical toolchain is still in place. The CMF Clearinghouse is active and was updated 2026-09-25. AASHTOWare Safety has replaced SafetyAnalyst, and is moving toward replacing IHSDM. The Systemic Safety User Guide (2024) replaced the 2013 SSPST. HSIP regulations (23 CFR 924) are unchanged. Federal policy framing shifted a lot in 2025–2026:
- The proposed Safe-System HSIP rule was withdrawn in May 2025.
- Five countermeasures were removed from FHWA's Proven Safety Countermeasures list in July 2026.
- A new National Roadway Safety Strategy in August 2026 dropped "Safer Speeds" and vulnerable-road-user design.

### Cited Findings
**HSIP (statute and regulation)**
- The HSIP is a core federal-aid program "to achieve a significant reduction in fatalities and serious injuries on all public roads." It is legislated under 23 U.S.C. 148, 150 and 130 and regulated by 23 CFR 924 and 490. — [FHWA HSIP Implementation Guide (2016)](https://highways.dot.gov/sites/fhwa.dot.gov/files/2022-06/hsip_ig42216_final.pdf)
- 23 CFR 924.9 (current as of 2026-09-23) requires several things:
  - Collect safety data on all public roads, with roadway data including at least the **MIRE Fundamental Data Elements** (§924.17).
  - Update the SHSP at least every 5 years.
  - Analyze safety data to develop "a comprehensive program of **systemic and spot** safety improvement projects."
  - Conduct engineering studies (e.g., RSAs).
  - Prioritize projects by fatal/serious-injury (FSI) reduction potential, cost-effectiveness, and SHSP priorities.
  - [eCFR 23 CFR 924.9](https://www.ecfr.gov/current/title-23/section-924.9)
- **[2025 CHANGE]** FHWA withdrew its Feb 21, 2024 NPRM, which would have updated HSIP regulations to incorporate the Safe System approach under IIJA. The withdrawal was published 2025-05-30, so 23 CFR 924 remains in its earlier form. — [Federal Register 2025-09726](https://www.federalregister.gov/documents/2025/05/30/2025-09726/highway-safety-improvement-program-withdrawal); NPRM purpose per [reginfo.gov RIN 2125-AG07](https://www.reginfo.gov/public/do/eAgendaViewRule?RIN=2125-AG07&pubId=202410)

**KABCO / MMUCC / serious-injury definition**
- States must use serious injury data that is MMUCC 4th edition compliant ("Suspected Serious Injury (A)"), or converted to KABCO "A" through NHTSA conversion tables [23 CFR 490.207(c)]. The MMUCC 4th edition definition was required by April 15, 2019. — [FHWA HSIP compliance assessment](https://highways.fhwa.dot.gov/safety/hsip/highway-safety-improvement-program-reporting-guidance/compliance-assessment); [FHWA Safety Performance Measures Fact Sheet](https://highways.fhwa.dot.gov/safety/hsip/spm/safety-performance-measures-fact-sheet)
- NHTSA compiled State Serious Injury Conversion Tables from state crash manuals for this reporting. — [FHWA State Serious Injury Conversion Tables](https://highways.fhwa.dot.gov/safety/hsip/spm/state-serious-injury-conversion-tables)
- MMUCC is now in its **6th edition**. It added chapters on Narrative and Diagram, Data Integration, and User-Centered Crash Reporting. — [NHTSA MMUCC page](https://www.nhtsa.gov/traffic-records/model-minimum-uniform-crash-criteria); [MMUCC 6th Ed. PDF (UW TOPS mirror)](https://transportal.cee.wisc.edu/documents/applications/crash-data/MMUCC/MMUCC%20Guideline%20Model%20Minimum%20Uniform%20Crash%20Criteria%206th%20Edition.pdf)
- The CMF Clearinghouse reports CMF severity on the KABCO scale (since late 2017). Before that it used Fatal/Serious/Minor/PDO. — [CMF Clearinghouse newsletter 2017 Q4](https://cmfclearinghouse.fhwa.dot.gov/newsletter/2017Q4.html)

**CMF Clearinghouse**
- FHWA-funded and maintained by UNC Highway Safety Research Center. It is a searchable CMF database with a Data Download API. "CMFs were last added to the clearinghouse on Sep 25, 2026." — [CMF Clearinghouse home](https://cmfclearinghouse.fhwa.dot.gov/)
- Star Quality Rating runs from 1 to 5 based on a 150-point score: 135–150 = 5★, 110–134 = 4★, 75–109 = 3★, 35–74 = 2★, 0–34 = 1★. Before-after/cross-sectional studies are scored on data (55 pts), study design and statistical method (75), and statistical significance (20). Meta-analysis and meta-regression studies have their own factor tables. Thresholds are consistent with an NCHRP 17-7x rating system. — [CMF Clearinghouse Star Quality Rating](https://cmfclearinghouse.fhwa.dot.gov/sqr.php)
- Under the revised criteria, a CMF needs at least 75 points (50%) for 3 stars. — [CMF Clearinghouse newsletter Winter 2020](https://cmfclearinghouse.fhwa.dot.gov/newsletter/2020Q4.html)

**Proven Safety Countermeasures (PSCs)**
- The PSC initiative began in 2008, with updates in 2012, 2017 and 2021, reaching **28 PSCs** grouped by focus area (speed management, roadway departure, intersections, pedestrians/bicyclists, crosscutting). — [FHWA About PSCi](https://highways.dot.gov/safety/proven-safety-countermeasures/about-proven-safety-countermeasures-initiative-psci); [FHWA PSC Booklet](https://highways.dot.gov/sites/fhwa.dot.gov/files/Proven%20Safety%20Countermeasures%20Booklet.pdf)
- **[2026 CHANGE]** In early July 2026 FHWA removed five PSCs from its website: road diets (roadway reconfiguration), bicycle lanes, appropriate speed limits for all road users, speed safety cameras, and variable speed limits. FHWA called it "part of a broader review… to ensure they align with current DOT policies and the administration's priorities." The PSC list "does not directly affect how the government funds projects." — [NPR, July 16, 2026](https://www.npr.org/2026/07/16/nx-s1-5893672/dot-bike-lanes-speed-cameras-safety-measures); [NACTO, July 29, 2026](https://nacto.org/latest/the-evidence-hasnt-changed-proven-safety-tools-continue-to-be-effective-best-practice/)
- Evidence cited before the removal: FHWA's 2021 booklet said speed cameras can cut crashes on urban arterials by up to ~50%, and bike lanes by up to 30% (two-lane roads) or 49% (four-lane). Road diet studies showed 19–47% total-crash reductions. — [NPR](https://www.npr.org/2026/07/16/nx-s1-5893672/dot-bike-lanes-speed-cameras-safety-measures); [NACTO](https://nacto.org/latest/the-evidence-hasnt-changed-proven-safety-tools-continue-to-be-effective-best-practice/). Some FHWA pages fetched in Oct 2026 (search snippets) still say "28 PSCs," so FHWA's own pages are internally inconsistent. — [FHWA PSC filter tool](https://highways.dot.gov/safety/proven-safety-countermeasures/search)

**Safe System Approach / National Roadway Safety Strategy**
- USDOT adopted the Safe System Approach (SSA) as its "guiding paradigm" under the 2022 NRSS. The SSA is built on the principles that humans make mistakes and that human bodies tolerate only limited crash forces. — [USDOT, What Is a Safe System Approach?](https://www.transportation.gov/safe-system-approach); [FHWA Zero Deaths and Safe System](https://highways.dot.gov/safety/zero-deaths)
- **[2026 CHANGE]** USDOT released a revised NRSS on Aug 4–5, 2026, replacing the 2022 version. It cut the five objectives to three: Safer People, Safer Roads, Safer Vehicles. It dropped "Safer Speeds," folded Post-Crash Care into Safer Roads, and removed the focus on road designs that protect vulnerable road users. Actions fell from 29 (2022) and 43 (2023) to 15. The only two regulatory actions are about eliminating requirements. The NRSS still promotes "evidence-based engineering interventions and the application of proven roadway designs and countermeasures." — [Eno Center for Transportation](https://enotrans.org/article/trump-administration-safety-approach-varies-widely-from-past-strategies); [Road Safety News, Aug 2026](https://roadsafetynews.com/us-unveils-new-national-roadway-safety-strategy-built-on-three-pillars-with-one-notably-absent); [AASHTO Journal](https://aashtojournal.transportation.org/usdot-unveils-revised-national-roadway-safety-plan); [NRSS 2026 PDF](https://www.transportation.gov/sites/dot.gov/files/2026-08/USDOT-National-Roadway-Safety-Strategy-2026.pdf)
- HSM2 still adds a Safe System section to Ch 2 (as drafted in 2024). — [AASHTO HSM2 webinar 2024](https://www.highwaysafetymanual.org/Documents/AASHTO_HSM2_Update_webinar_20240618_Combined.pdf)

**Systemic Safety Project Selection Tool → Systemic Safety User Guide**
- SSPST: FHWA-SA-13-019, July 2013 (older). — [FHWA SSPST](https://highways.dot.gov/safety/data-analysis-tools/systemic/systemic-safety-project-selection-tool)
- The 2024 Systemic Safety User Guide is "a substantial update" to the SSPST. Its chapters cover: identifying focus crash types, facility types and risk factors; screening and prioritizing candidate locations by risk; selecting countermeasures for systemic deployment; prioritizing projects; and evaluation. — [FHWA Systemic Safety User Guide page](https://highways.dot.gov/safety/data-analysis-tools/systemic/systemic-safety-user-guide); [PDF](https://highways.dot.gov/sites/fhwa.dot.gov/files/2024-07/SystemicSafetyUserGuide.pdf); [ROSA P](https://rosap.ntl.bts.gov/view/dot/91884)
- Example application: Boston MPO's 2026 Vision Zero plan follows the User Guide's typical six steps, starting with focus crash types (highest-frequency severe crash types) and then facility types. — [CTPS Vision Zero App. D](https://ctps.org/data/html/plans/Vision-Zero/2026/Vision%20Zero%20App%20D%20High-Risk%20(Systemic)%20Network%20Methodology.html)

**IHSDM**
- **[2025 status]** FHWA has **discontinued IHSDM software development**. IHSDM 2021 (v17.0.0, Sept 2021) is the final release. FHWA still provides free technical support, training through NHI, and the website. The CPM implements HSM1 Ch 10, 11, 12, 18 and 19, plus NCHRP 17-58, 17-70 and 17-68 models. It does **not** implement ped/bike (17-84), crash-type/severity models (17-62), part-time shoulders (17-89), or HOV/HOT (17-89A). — [FHWA, Future Plans for IHSDM (2025), doi:10.21949/s1dp-1c49](https://highways.dot.gov/media/110891)

**AASHTOWare Safety (formerly SafetyAnalyst)**
- SafetyAnalyst was sunset in **July 2022**, and AASHTOWare Safety (powered by Numetric) completed third-party validation of its network screening ahead of that. — [Numetric](https://www.numetric.com/aashtoware-safety-network-screening-third-party-validation/)
- AASHTOWare Safety Segment / Intersection Analytics offer "Segment and Sliding Window" (and intersection/ramp) screening "with various Historical, Predictive, and Expected performance measures following HSM best-practices," plus custom or existing SPFs for predictive analysis. — [AASHTOWare Safety Segment](https://aashtoware.org/products/safety/aashtoware-safety-segment); [Intersection Analytics](https://aashtoware.org/products/safety/aashtoware-safety-intersection-analytics)
- AASHTOWare Safety Alternative Design runs HSM Part C calculations, "replacing the IHSDM." — [AASHTOWare Safety Alternative Design](https://aashtoware.org/products/safety/safety-alternative-design)
- State example: New Mexico DOT uses AASHTOWare Safety for crash query, network screening, safety analysis and SHSP dashboards, with crash data from 2013–2023. — [NMDOT presentation](https://api.realfile.rtsclients.com/PublicFiles/f260a66b364d453e91ff9b3fedd494dc/d1e65d16-ef67-46c8-858a-ebb2b36aa5f0/How%20NMDOT%20Is%20Using%20AASHTOWare%20Safety%20To%20Implement%20the%20Roadway%20Safety%20Management_A%20Engle%20L%20Miller.pdf). WisDOT describes it as supporting crash queries, dashboards, network screening, and alternatives analysis with B/C. — [WisDOT Traffic Tech Talk 2025](https://wisconsindot.gov/dtsdManuals/traffic-ops/programs/ttt/ttt072325.pdf)

### Inferences
- What practitioners call "industry standard" is the HSM methods, the CMF Clearinghouse, the PSCs and the systemic approach. Federal policy messaging changed in 2025–2026, but HSIP regulations, the HSM and the Clearinghouse did not. CrashIQ should stay tied to the HSM methods and the Clearinghouse, which are evidence-based, rather than to the current FHWA PSC web list. California practice (Caltrans, local SS4A/HSIP) still largely follows Safe System framing.
- AASHTOWare Safety is the de facto benchmark for "HSM-compliant" screening software: sliding window, EB expected measures, custom SPFs, and B/C. Feature parity on those items is the bar CrashIQ will be judged against.

### Gaps
- Primary FHWA PSC page text after the July 2026 removals could not be fetched (the curl fetch was blocked and the headless browser was unavailable). The removal is confirmed by NPR and NACTO, not by an FHWA notice.
- Whether FHWA SSA web pages were edited or removed in 2025–2026 was not confirmed. Search results show them still live.

---

## 4. Systemic vs. hot-spot (reactive / crash-based) analysis

### Takeaway
US practice and regulation call for *both*. Hot-spot (crash-based) screening finds sites with high observed or expected crash concentrations. The systemic approach finds sites with *risk factors* linked to severe crash types, even where few or no crashes have happened yet. This matters for KA crashes, which are scattered and rare, as on rural roads and with pedestrian crashes. HSM2 makes the systemic approach a formal parallel track in Part B, including guidance on splitting funds between the two.

### Cited Findings
- 23 CFR 924.9(a)(4)(i): an HSIP must deliver "a comprehensive program of systemic and spot safety improvement projects." — [eCFR](https://www.ecfr.gov/current/title-23/section-924.9)
- Systemic safety planning is "evaluating an entire system using a defined set of criteria to identify candidate locations for safety investments to reduce the occurrence of and the potential for severe crashes." It is "a complementary analytical technique" to traditional site analysis. — [FHWA SSPST Introduction (2013)](https://highways.dot.gov/safety/data-analysis-tools/systemic/systemic-safety-project-selection-tool/introduction)
- The systemic approach involves installing low- to moderate-cost countermeasures at locations with risk factors for severe crashes. FHWA calls it a fundamental part of a comprehensive safety approach. — [FHWA Systemic Approach to Safety](https://highways.dot.gov/safety/data-analysis-tools/systemic)
- FHWA: "Employing traditional network screening with systemic safety analysis can be an agency's first step toward a comprehensive safety management program." — [FHWA screening guide](https://highways.dot.gov/safety/data-analysis-tools/systemic/screening-your-network-improve-roadway-safety-performance)
- HSM2 new Ch 12 (Systemic Approach) covers: general steps, benefits, considerations, **"allocating funds between systemic and crash-based projects,"** data used, and sample problems. — [AASHTO HSM2 webinar 2024](https://www.highwaysafetymanual.org/Documents/AASHTO_HSM2_Update_webinar_20240618_Combined.pdf)
- HSM2 "introduces a systemic approach to safety management as a parallel method to the traditional crash-based approach and outlines the five steps for its application… shifts from addressing individual high-crash locations to… targeting risk factors that contribute to serious crashes." It "introduces improved ways to find locations that may have previously been overlooked by traditional 'hot spot' methods." — [HDR (Dan Cook, HSM2 contributor)](https://hdrinc.com/insights/experts-talk-exploring-updates-highway-safety-manual-dan-cook)
- NCHRP 17-73 (Systemic Pedestrian Safety Analyses) and 17-77 (Guide for Quantitative Approaches to Systemic Safety Analysis) supported this content. — [AASHTO HSM2 webinar 2024](https://www.highwaysafetymanual.org/Documents/AASHTO_HSM2_Update_webinar_20240618_Combined.pdf); [HSM Research Resources](https://www.highwaysafetymanual.org/Pages/ResearchResources.aspx)

### Inferences
- When each is recommended, synthesized from the sources above:
  - Use **hot-spot/crash-based** methods where crashes cluster at identifiable sites with enough history for EB-stable estimates, typically urban intersections and higher-volume segments.
  - Use **systemic** methods where severe crashes are spread thinly across many similar sites, such as rural roadway departure, unsignalized intersections, and pedestrian crossings on multilane arterials. Also use them when the goal is proactive, Safe-System-style risk reduction.
- A corridor tool that only ranks hot spots covers half of what the regulation and HSM2 describe. A risk-factor scoring layer (for example, a High-Injury Network plus facility-type risk factors) would close the systemic gap.

### Gaps
- I did not get the 2024 User Guide's full text (the PDF download returned an HTML stub), so its exact step count and recommended risk-factor list are not quoted. CTPS describes "six steps"; HDR describes HSM2's systemic approach as "five steps." The step count depends on the source.

---

## 5. Typical minimum data requirements (crash years, AADT, roadway inventory)

### Takeaway
HSM-grade analysis needs three linked datasets: geolocated crash records with severity (KABCO), type and date; traffic volumes (segment AADT or intersection entering volumes); and a roadway inventory that at minimum matches the MIRE Fundamental Data Elements required by 23 CFR 924. Simpler measures (crash frequency, EPDO, proportion tests) need only crash data. Rate, SPF and EB methods need volumes and site attributes.

### Cited Findings
- HSIP regulation requires roadway data on all public roads to include at least the MIRE Fundamental Data Elements (23 CFR 924.17). — [eCFR 23 CFR 924.9(a)(1)](https://www.ecfr.gov/current/title-23/section-924.9); [eCFR Part 924](https://www.ecfr.gov/current/title-23/part-924)
- Network screening uses "crash, roadway, and traffic volume data." The proportion-based measure needs only "crash type and location data." The HSM groups sites into reference populations (e.g., by number of legs, control type, TEV bands). — [FHWA screening guide](https://highways.dot.gov/safety/data-analysis-tools/systemic/screening-your-network-improve-roadway-safety-performance)
- HSM1 Table 4-1 summarizes data needs for each screening measure. — [MAG Network Screening Tech Memo 4 (Arizona)](https://azmag.gov/Portals/0/Documents-Ext/Transportation/Technical-Memo-4-for-Network-Screening.pdf); [PSU TESC presentation](https://www.tesc.psu.edu/assets/Session%20PDFS/2A-Roeker.pdf)
- SPFs predict crashes "as a function of traffic volume and roadway characteristics (e.g., number of lanes, median type, intersection control, number of approach legs)." Part C therefore needs AADT plus geometry and control attributes. — [AASHTO HSM Content](https://www.highwaysafetymanual.org/Pages/hsm_parts.aspx)
- HSM2 calibration and jurisdiction-specific SPF development (Ch 13) means agencies need local crash, volume and inventory samples to calibrate. FHWA expects a transition period for exactly this. — [AASHTO HSM2 webinar 2024](https://www.highwaysafetymanual.org/Documents/AASHTO_HSM2_Update_webinar_20240618_Combined.pdf); [FHWA IHSDM plans 2025](https://highways.dot.gov/media/110891)
- HSIP serious-injury data must meet the MMUCC "Suspected Serious Injury (A)" definition. — [FHWA SPM Fact Sheet](https://highways.fhwa.dot.gov/safety/hsip/spm/safety-performance-measures-fact-sheet)

### Inferences
- For CrashIQ in California: crash data from SWITRS/TIMS, plus AADT from Caltrans (state highways) and local counts, plus inventory attributes for number of lanes, median, control and legs. These would be the minimum to support EB screening and Part C prediction. Without AADT, the tool is limited to frequency, EPDO and proportion measures.

### Gaps
- **Number of crash years:** No primary source fetched this session states the HSM's recommended analysis period. Common practice is 3–5 years, with HSM Part C applying EB over a multi-year period. That figure is not verified here and should be sourced (e.g., HSM Ch 4/Part C text or a state DOT safety manual such as the TxDOT or Oregon APM Ch 4) before it is quoted in the report.
- Minimum calibration sample sizes for HSM calibration factors (HSM1 Part C Appendix A guidance) were not verified this session.
