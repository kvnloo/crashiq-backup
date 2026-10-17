# Crash Diagnosis → Contributing Factors → Countermeasures: US Industry Methods (for CrashIQ automation)

Source note: HSM Part B text below was read from the pre-publication HSM 1st Edition draft chapters ("Current as of April 6, 2009") hosted on the UNH GRANIT FTP mirror. The published HSM (AASHTO, 2010) may differ in wording and exhibit numbers. Treat exhibit numbers as approximate and check them against the licensed HSM before citing in product text. Caltrans LRSM figures come from Version 1.7 (April 2024). A Version 1.8 is referenced in the 2026 HSIP Analyzer manual, so CRF values may have changed since.

## Q1. HSM Part B Ch. 5 (Diagnosis) and Ch. 6 (Select Countermeasures): crash summaries, collision/condition diagrams, pattern → contributing-factor tables

### Takeaway
The HSM defines diagnosis as a 3-step process: (1) safety data review, (2) supporting documentation, and (3) field conditions. Step 1 uses descriptive crash statistics plus collision diagrams, condition diagrams and crash mapping. Ch. 6 then maps each crash pattern to a checklist of "possible contributing factors" by facility type, and from there to countermeasures with CMFs (HSM Part D). The HSM says repeatedly that linking factors to countermeasures "requires engineering judgment and local knowledge". So the parts that can be automated are the summaries, the over-representation flags and the checklist lookup. The final call stays with the engineer.

### Cited Findings
**Ch. 5 process and data elements**
- Diagnosis is the second step of the Part B roadway safety management process. Its intended outcome is "the identification of the causes of the collisions and potential safety concerns or crash patterns that can be evaluated further" in Ch. 6. — [HSM Ch.5 draft](https://ftp.granit.unh.edu/submissions/NHDOTOUT/craig/HSM/Chapter%205_Diagnosis.pdf)
- The three steps are: Step 1 Safety Data Review (crash types, severities and environmental conditions summarized as descriptive statistics, plus crash locations); Step 2 Assess Supporting Documentation; Step 3 Assess Field Conditions. "Some steps may not apply to all projects." — [HSM Ch.5 draft](https://ftp.granit.unh.edu/submissions/NHDOTOUT/craig/HSM/Chapter%205_Diagnosis.pdf)
- The data review "may identify patterns related to time of day, direction of travel prior to crashes, weather conditions, or driver behaviors." The HSM suggests compiling **3 to 5 years** of data "to improve the reliability of the diagnosis." — [HSM Ch.5 draft](https://ftp.granit.unh.edu/submissions/NHDOTOUT/craig/HSM/Chapter%205_Diagnosis.pdf)
- Descriptive statistics fields listed by the HSM (a direct spec for cross-tab dimensions):
  - Crash identifiers: date, day of week, time of day
  - Crash type: rear-end, sideswipe, angle, turning, head-on, run-off-road, fixed object, animal, out of control, work zone
  - Severity: KABCO
  - Sequence of events: direction of travel and location of parties (NB/SB/EB/WB, approach, milepost)
  - Contributing circumstances: parties involved (vehicle only, ped+vehicle, bike+vehicle); road condition (dry, wet, snow, ice); lighting (dawn, daylight, dusk, dark without lights, dark with lights); weather; impairments (alcohol, drugs, fatigue)
  - Source: [HSM Ch.5 draft](https://ftp.granit.unh.edu/submissions/NHDOTOUT/craig/HSM/Chapter%205_Diagnosis.pdf)
- The HSM calls bar charts, pie charts and tabular summaries "useful," with the purpose "to make patterns visible." The example tabular summary lists each crash with date, day, time, severity, type, road condition, light condition, direction and BAC. — [HSM Ch.5 draft](https://ftp.granit.unh.edu/submissions/NHDOTOUT/craig/HSM/Chapter%205_Diagnosis.pdf)
- If patterns are not obvious from the descriptive statistics, the Ch. 4 measure "Probability of Specific Crash Types Exceeding Threshold Proportion" can be used as a diagnostic tool. "Sites with similar characteristics are suggested to be analyzed together because crash patterns will naturally differ depending on the geometry, traffic control devices, adjacent land uses, and traffic volumes." — [HSM Ch.5 draft](https://ftp.granit.unh.edu/submissions/NHDOTOUT/craig/HSM/Chapter%205_Diagnosis.pdf)

**Collision and condition diagrams, crash mapping**
- A collision diagram is a "two-dimensional plan view representation of the crashes that have occurred at a site within a given time period."
  - Crashes are drawn as arrows showing crash type and direction of travel, annotated with severity, date, time of day, pavement condition and light condition, plus a legend.
  - It need not be drawn to scale. The HSM recommends a standard symbol set, adapted from the ITE *Manual of Transportation Engineering Studies*.
  - Source: [HSM Ch.5 draft](https://ftp.granit.unh.edu/submissions/NHDOTOUT/craig/HSM/Chapter%205_Diagnosis.pdf)
- HSM caveat for automation: visual trends in a collision diagram "may not reflect a quantitative or statistically reliable assessment of site trends; however, they do provide an indication of whether or not patterns exist." For multiple sites, "it can be more efficient to develop the collision diagrams with software." — [HSM Ch.5 draft](https://ftp.granit.unh.edu/submissions/NHDOTOUT/craig/HSM/Chapter%205_Diagnosis.pdf)
- A condition diagram is a plan view of site characteristics:
  - Lane configuration and traffic control
  - Ped, bike and transit facilities
  - Medians, landscaping, shoulder or curb type
  - Utilities and poles
  - Adjacent land uses and driveways
  - Pavement defects (potholes, ponding, ruts)
  - It is meant to be "related to the collision diagram's findings… the two diagrams could be overlaid," and is usually drawn by hand during the field visit.
  - Source: [HSM Ch.5 draft](https://ftp.granit.unh.edu/submissions/NHDOTOUT/craig/HSM/Chapter%205_Diagnosis.pdf)
- Crash mapping via GIS can query "crash clusters; that is, crashes within a specific distance of each other, or within a specific distance of a particular land use."
  - Location coding is a stated pitfall: "if all crashes within 200 feet of an intersection are entered into the database at the intersection centerline, the crash map may misrepresent actual crash locations."
  - Source: [HSM Ch.5 draft](https://ftp.granit.unh.edu/submissions/NHDOTOUT/craig/HSM/Chapter%205_Diagnosis.pdf)
- Supporting documentation listed:
  - Volumes for all modes, as-built plans, design criteria, field inventory, photo/video logs
  - Maintenance logs, recent studies, land use/access mapping, adverse weather history
  - Public comments, planned improvements, anecdotal information
  - Example: a step-change in left-turn crashes three years earlier was explained by a widening project that increased speeds and the number of opposing lanes.
  - Source: [HSM Ch.5 draft](https://ftp.granit.unh.edu/submissions/NHDOTOUT/craig/HSM/Chapter%205_Diagnosis.pdf)
- Field assessment covers:
  - Roadway/roadside: signing, striping, posted speeds, lighting, pavement, sight distance, shoulders, geometry
  - Traffic conditions: queue storage, speeds, signal clearance time
  - Traveler behavior, roadway consistency, land uses, weather
  - "Evidence of problems": broken glass, skid marks, damaged signs or guardrail
  - "Prompt lists" are recommended (HSM Appendix D). A field assessment is distinguished from a formal Road Safety Audit (RSA).
  - Source: [HSM Ch.5 draft](https://ftp.granit.unh.edu/submissions/NHDOTOUT/craig/HSM/Chapter%205_Diagnosis.pdf)
- "Identify Concerns" means comparing data, documentation and field findings. Example: a high crash frequency on one approach plus a sight-distance constraint seen in the field "may be related and warrant further consideration."
  - If no pattern is found, "there are multiple minor factors contributing… Most countermeasures are effective in addressing a single contributing factor, and therefore it may require multiple countermeasures."
  - Source: [HSM Ch.5 draft](https://ftp.granit.unh.edu/submissions/NHDOTOUT/craig/HSM/Chapter%205_Diagnosis.pdf)

**Ch. 6: contributing factors and countermeasures**
- Purpose of the contributing-factor lists: "identification of a broad range of possible contributing factors in order to minimize the probability that a major contributing factor will be overlooked." Engineering judgment then picks the greatest contributors, using Ch. 5 diagnosis as "the primary basis." — [HSM Ch.6 draft](https://ftp.granit.unh.edu/submissions/NHDOTOUT/craig/HSM/Chapter%206_SelectingCountermeasures.pdf)
- The Haddon Matrix frames factors as human, vehicle and roadway, crossed with before, during and after the crash.
  - Example for rear-end crashes, roadway factors "before": wet pavement, polished aggregate, steep downgrade, poor signal coordination, limited stopping sight distance, lack of warning signs.
  - Source: [HSM Ch.6 draft](https://ftp.granit.unh.edu/submissions/NHDOTOUT/craig/HSM/Chapter%206_SelectingCountermeasures.pdf)
- HSM caution: "consistency with design guidelines does not correlate directly to a safe roadway system." — [HSM Ch.6 draft](https://ftp.granit.unh.edu/submissions/NHDOTOUT/craig/HSM/Chapter%206_SelectingCountermeasures.pdf)
- The pattern → possible-contributing-factor tables are directly usable as a seed pattern library. They are Exhibits 6-3 to 6-8: roadway segments, signalized intersections, unsignalized intersections, highway-rail crossings, pedestrians and bicyclists. Verbatim highlights from the draft:
  - **Segments, Fixed object:** obstruction in or near roadway; inadequate lighting; inadequate pavement markings; inadequate signs, delineators, guardrail; slippery pavement; roadside design (inadequate clear distance); inadequate roadway geometry; excessive speed.
  - **Segments, Nighttime:** poor nighttime visibility or lighting; poor sign visibility; inadequate channelization or delineation; excessive speed; inadequate sight distance.
  - **Segments, Wet pavement:** pavement design (drainage, permeability); inadequate pavement markings; inadequate maintenance; excessive speed.
  - **Segments, Run-off-road:** inadequate lane width; slippery pavement; inadequate median width; inadequate maintenance; inadequate shoulders; poor delineation; poor visibility; excessive speed.
  - **Other segment rows:** vehicle rollover; opposite-direction sideswipe/head-on; bridges.
  - **Signalized, Right-angle:** poor visibility of signals; inadequate signal timing; excessive speed; slippery pavement; inadequate sight distance; drivers running red light.
  - **Signalized, Rear-end/sideswipe:** inappropriate approach speeds; poor visibility of signals; unexpected lane changes on approach; narrow lanes; unexpected stops on approach; slippery pavement; excessive speed.
  - **Signalized, Left- or right-turn:** misjudge speed of oncoming traffic; ped/bike conflicts; inadequate signal timing; inadequate sight distance; conflict with right-turn-on-red vehicles.
  - **Unsignalized, Angle:** restricted sight distance; high traffic volume; high approach speed; unexpected crossing traffic; drivers running stop sign; slippery pavement.
  - **Unsignalized, Collisions at driveways:** left-turning vehicles; improperly located driveway; right-turning vehicles; large through or driveway volume; restricted sight distance; excessive speed.
  - **Pedestrian:** limited sight distance; inadequate barrier between pedestrian and vehicle facilities; inadequate signals/signs; inadequate signal phasing; inadequate markings; inadequate lighting; driver has inadequate warning of mid-block crossings; lack of crossing opportunity; excessive speed; pedestrians on roadway; long distance to nearest crosswalk; sidewalk too close to travel way; school crossing area.
  - **Bicyclist:** limited sight distance; inadequate signs; inadequate markings; inadequate lighting; excessive speed; bicycles on roadway; bicycle path too close to roadway; narrow lanes for bicyclists.
  - Source: [HSM Ch.6 draft](https://ftp.granit.unh.edu/submissions/NHDOTOUT/craig/HSM/Chapter%206_SelectingCountermeasures.pdf)
- The HSM says these lists "are not and can never be a comprehensive list," and points to the NCHRP Report 500 series for detail. — [HSM Ch.6 draft](https://ftp.granit.unh.edu/submissions/NHDOTOUT/craig/HSM/Chapter%206_SelectingCountermeasures.pdf)
- Countermeasure selection has three steps: (1) identify contributing factors; (2) identify countermeasures that address them; (3) run a cost-benefit analysis (Ch. 7).
  - "Comparing contributing factors to potential countermeasures requires engineering judgment and local knowledge… what is physically, financially, and politically feasible."
  - Worked chain: rear-end crashes → limited sight distance → why (curvature, low landscaping, illumination) → treatments (regrade or realign, modify landscaping).
  - Source: [HSM Ch.6 draft](https://ftp.granit.unh.edu/submissions/NHDOTOUT/craig/HSM/Chapter%206_SelectingCountermeasures.pdf)
- HSM Part D supplies CMFs (called "AMFs" in the draft). Draft examples:
  - Urban TWSC → modern roundabout: AMF 0.61 for all types and severities.
  - Rural TWSC → signal: AMF 1.58 for rear-end and 0.40 for left-turn. This shows one countermeasure can increase some crash types while reducing others.
  - Where no AMF exists, Part D gives trend information, which is "not sufficient for a cost-benefit" analysis.
  - Source: [HSM Ch.6 draft](https://ftp.granit.unh.edu/submissions/NHDOTOUT/craig/HSM/Chapter%206_SelectingCountermeasures.pdf)
- If no clear factor emerges: check upstream and downstream conditions and inconsistencies with the community's typical driving environment, consider systematic improvements, or monitor the site. — [HSM Ch.6 draft](https://ftp.granit.unh.edu/submissions/NHDOTOUT/craig/HSM/Chapter%206_SelectingCountermeasures.pdf)

**FHWA local/rural toolkit restatement**
- FHWA's Step 4 "Diagnose Site Crash Conditions" lists crash report forms, the Haddon Matrix, and crash and condition diagrams.
  - Example tabular crash listing columns: No., Date, Time, Type, Ped/Bike, Fatal, Injuries, Property Damage, Day/Night, Wet/Dry, Contributing Cause.
  - In the example, 12 of 17 crashes are angle crashes with "Failure to Yield Right of Way," and the collision diagram shows them concentrated on the south leg.
  - Source: [FHWA Step 4 Diagnose](https://highways.dot.gov/safety/local-rural/improving-safety-rural-local-and-tribal-roads-safety-toolkit/step-4-diagnose)
- FHWA: "most crashes cannot be related to a singular causal event… crashes are the result of a convergence of a series of events." Hence "contributing factors" rather than "causes." — [FHWA Step 4 Diagnose](https://highways.dot.gov/safety/local-rural/improving-safety-rural-local-and-tribal-roads-safety-toolkit/step-4-diagnose)
- FHWA: "In rural areas, especially on low volume roads, intersections may not have enough crash history to reveal crash patterns. In these cases, a systemic analysis would be a good alternative." — [FHWA Step 4 Diagnose](https://highways.dot.gov/safety/local-rural/improving-safety-rural-local-and-tribal-roads-safety-toolkit/step-4-diagnose)
- FHWA gives three ways to identify countermeasures: (1) by crash type of concern, via the CMF Clearinghouse; (2) by location characteristics (intersection and curve guidebooks); (3) by best practices (Proven Safety Countermeasures). — [FHWA Step 4 Diagnose](https://highways.dot.gov/safety/local-rural/improving-safety-rural-local-and-tribal-roads-safety-toolkit/step-4-diagnose)
- Unintended-consequence caution: "if a lane is widened, drivers may feel they can drive faster." — [FHWA Step 4 Diagnose](https://highways.dot.gov/safety/local-rural/improving-safety-rural-local-and-tribal-roads-safety-toolkit/step-4-diagnose)

### Inferences
- HSM Ch. 5's field list maps almost one-to-one onto CrashIQ's planned cross-tab dimensions (lighting × time × type × movement/direction × severity), plus road surface, weather, parties and impairment. Engineers will expect to see those standard fields.
- Ch. 6 Exhibits 6-3 to 6-8 give a defensible first layer for a symptom → factor library, keyed by facility type (segment, signalized, unsignalized, rail, ped, bike) × crash pattern. Because the HSM treats them as checklists, the product should present the output as "possible contributing factors to verify in the field," not as diagnosed causes.
- Field-only factors cannot be confirmed from crash data alone. Examples: sight distance, signal visibility, landscaping, pavement defects. The AI write-up should flag these as "requires field verification," which matches HSM Step 3.

### Gaps
- I could not access the final published HSM (2010) or the HSM 2nd edition text (AASHTO paywall). Exhibit numbers and wording are from the 2009 draft.
- I did not retrieve HSM Ch. 5 Appendices B–D (documentation questions, field prep, prompt lists), which are referenced but not reproduced above.

## Q2. Statistical over-representation methods

### Takeaway
The HSM's formal method is "Probability of Specific Crash Types Exceeding Threshold Proportion," with its extension "Excess Proportion of Specific Crash Types." It is a beta-binomial (method-of-moments) test of a site's crash-type proportion against its reference population. The HSM states it can be used both for screening and for diagnosis. It has documented limits: it ignores volume, and a site can be flagged because it has few non-target crashes. I found no primary FHWA/HSM guidance prescribing chi-square or simple binomial z-tests.

### Cited Findings
- **Definition:** "Sites are prioritized based on the probability that the true proportion, p_i, of a particular crash type or severity (e.g., long-term predicted proportion) is greater than the threshold proportion, p*_i." Data needed: crash data by type and location only. — [HSM Ch.4 draft](https://ftp.granit.unh.edu/submissions/NHDOTOUT/craig/HSM/Chapter%204_NetworkScreening.pdf)
- **Strengths** (HSM exhibit): can be used as a diagnostic tool (Ch. 5); considers variance in data; not affected by regression-to-the-mean (RTM) bias.
- **Limitations:** "Does not account for traffic volume"; "Some sites may be identified for further study because of unusually low frequency of non-target crash types." — [HSM Ch.4 draft](https://ftp.granit.unh.edu/submissions/NHDOTOUT/craig/HSM/Chapter%204_NetworkScreening.pdf)
- **Procedure** (HSM Ch. 4 §4.4.2.9; formulas verbatim from the draft): first organize sites into reference populations, e.g., TWSC vs. signalized. — [HSM Ch.4 draft](https://ftp.granit.unh.edu/submissions/NHDOTOUT/craig/HSM/Chapter%204_NetworkScreening.pdf)
  - Step 1: observed proportion p_i = N_obs,i(target) / N_obs,i(total). It is computed only for sites "that [have] experienced **two or more crashes of the target** collision type or crash severity" (Eq. 4-18).
  - Step 2: threshold p*_i = ΣN_target / ΣN_total across the reference population (Eq. 4-19). The reference-population proportion is "a useful default starting point."
  - Step 3: sample variance (not population variance, which the HSM explicitly warns about), over sites with N_total ≥ 2: Var = [1/(n_sites−1)] × [Σ((N_t² − N_t)/(N_T² − N_T)) − (1/n_sites)(Σ N_t/N_T)²] (Eq. 4-20).
  - Step 4: α = (p*² − p*³ − s²·p*)/s² and β = α/p* − α (Eqs. 4-21, 4-22).
  - Step 5: P(p_i > p*_i | N_t, N_T) = 1 − betadist(p*_i, α + N_t, β + N_T − N_t) (Eq. 4-23).
  - Step 6: rank sites by probability.
- **Worked example** (TWSC angle crashes): p* = 33/150 = 0.22; s² = 0.034; α = 0.91; β = 3.2. Intersection 7 has 5 angle crashes of 34, so p_i = 0.15 and probability = 0.14, interpreted as "a 14% chance that the long-term expected proportion… is actually greater." — [HSM Ch.4 draft](https://ftp.granit.unh.edu/submissions/NHDOTOUT/craig/HSM/Chapter%204_NetworkScreening.pdf)
  - Note: the draft's betadist line uses (0.78+5, 2.8+34−5), which differs from the tabulated α=0.91 and β=3.2. This is an internal inconsistency in the draft. Validate any implementation against the published HSM sample problem.
- **Excess Proportion (§4.4.2.10):** p_diff = p_i − p*_i. It is computed only for sites whose probability exceeds a "limiting probability (e.g., 90 percent)." The sample problem uses 60%.
  - The HSM says the limit can be raised "if many sites have high probability… to limit the number of sites to a reasonable study size."
  - Source: [HSM Ch.4 draft](https://ftp.granit.unh.edu/submissions/NHDOTOUT/craig/HSM/Chapter%204_NetworkScreening.pdf)
- **HSM summary table** lists both measures as accounting for data variance and not affected by RTM, but not accounting for volume. — [HSM Ch.4 draft](https://ftp.granit.unh.edu/submissions/NHDOTOUT/craig/HSM/Chapter%204_NetworkScreening.pdf)
- **FHWA scoping guidance** lists "Probability of Specific Crash Types Exceeding Threshold Proportion" among HSM network screening methods, alongside EB-adjusted expected and excess expected crash frequency. — [FHWA Screening Your Network](https://highways.dot.gov/safety/data-analysis-tools/systemic/screening-your-network-improve-roadway-safety-performance); [FHWA HSM scoping Ch.2](https://highways.dot.gov/safety/data-analysis-tools/hsm/scale-and-scope-safety-assessment-methods-project-development-0)
- **State practice (Oregon DOT APM App. 4A):** critical crash rate and excess proportion are "best used in conjunction."
  - If an intersection is above the critical rate for its reference population, "running the excess proportion of specific crash types… may give the analyst a better view of what crash types are causing concerns."
  - Critical rate needs AADT; excess proportion "just requires a breakdown of crash types."
  - ODOT provides spreadsheets and a PTV Visum add-in. The add-in's approximate crash-to-intersection assignment is "for planning level studies only, not for project level safety analysis."
  - When the reference population is too small, ODOT compares rates to statewide 90th-percentile rates instead.
  - Source: [ODOT APM Appendix 4A (03/2021)](https://www.oregon.gov/odot/Planning/Documents/APMv2_App4A.pdf)
- **Caltrans LRSM:** practitioners "should understand the overall random nature of crashes and the concept of 'regression to the mean'… a site might be selected for study when the number of crashes is randomly high, or overlooked when… randomly low." The LRSM also encourages comparing local crashes "with those occurring in similar areas around the state." — [Caltrans LRSM v1.7](https://dot.ca.gov/-/media/dot-media/programs/local-assistance/documents/hsip/2024/lrsm2024-v2.pdf)
- **Research critique** (search-result snippet of a Utah-related FHWA/ROSAP report; full text not retrieved): "Test of proportion presently does not have a capability to detect elevated crash severity of a specific crash type," and rare high-severity events "can't be detected by a test of proportions." — [ROSAP 88627 (crash-type SPFs vs. test of proportion)](https://rosap.ntl.bts.gov/view/dot/88627/dot_88627_DS1.pdf)
- **Peer-reviewed comparison exists:** "Comparison of Alternative Methods for Identifying Sites with High Proportion of Specific Accident Types," TRR 2019 (2007). Only the abstract stub was seen. — [doi:10.3141/2019-25](https://doi.org/10.3141/2019-25)

### Inferences
- CrashIQ can implement HSM Eqs. 4-18 to 4-24 exactly. Inputs: per-site target and total counts, plus a reference population of "similar" sites (same control type and facility type). Pick a limiting probability, e.g., 0.90 by default with a user setting, and report p_i, p*, P(p_i > p*) and p_diff.
- Built-in minimum-sample rules from the HSM: compute only where target crashes ≥ 2. The variance calculation needs N_total ≥ 2 per site. Recommend 3–5 years of data.
- The same beta-binomial machinery works for any categorical attribute (night, wet, ped, KA severity), since the HSM explicitly allows "collision type or crash severity." Each cross-tab cell can therefore be tested against the same cell share in the reference population.
- Because the test ignores volume and can be inflated by few non-target crashes, pair it with a frequency or rate measure (critical rate or EB) in the output, as ODOT does.

### Gaps
- I found no primary US guidance (HSM, FHWA, Caltrans) prescribing chi-square, Fisher's exact or simple binomial z-tests for crash-type over-representation, or prescribing multiple-comparison corrections across many cross-tab cells. If CrashIQ uses these, it is going beyond standard practice and should document that.
- The full text of the ROSAP 88627 report and the TRR 2019 comparison paper was not reviewed.

## Q3. Published symptom → countermeasure tables and CMF rules

### Takeaway
Machine-readable seed sources exist:
- **Caltrans LRSM:** about 80+ coded countermeasures, each with crash type addressed (All, P&B, Night, Emergency Vehicle, Animal), CRF, life, funding eligibility and systemic opportunity.
- **FHWA FCFT Quick Reference Guide:** focus crash type → contributing factor → systemic countermeasure tables, plus a 6-step selection process.
- **PEDSAFE:** 12 PBCAT crash-type groups → possible causes → candidate countermeasures, with matrices.
- **STEP guide:** roadway configuration × speed × AADT tables for uncontrolled crossings.
- **NCHRP 500:** about 22 emphasis-area guides.
- **CMF Clearinghouse:** 1–5 star ratings based on a 150-point NCHRP 17-72 score.

The standard rule for combining CMFs is to multiply them. FHWA research says this tends to overestimate and suggests combining no more than two. Caltrans caps HSIP benefit/cost (B/C) calculations at three countermeasures, applied multiplicatively.

### Cited Findings
**Caltrans LRSM (v1.7, April 2024)**
- Countermeasure tables are split by signalized intersections (SI##), non-signalized (NS##), roadway segments (R##) and ped/bike. Fields:
  - Crash Types: "All", "P & B", "Night", "Emergency Vehicle", "Animal"
  - CRF used for HSIP calls-for-projects
  - Expected Life: 10 or 20 years
  - Funding Eligibility: 90%, or 50% for SI03 signal timing only
  - Systemic Approach Opportunity: Very High, High, Medium, Low
  - Source: [Caltrans LRSM v1.7](https://dot.ca.gov/-/media/dot-media/programs/local-assistance/documents/hsip/2024/lrsm2024-v2.pdf)
- Code suffixes encode the target crash group: NT = night, PB = ped/bike, EV = emergency vehicle, AL = animal, RA = roundabout. — [Caltrans LRSM v1.7](https://dot.ca.gov/-/media/dot-media/programs/local-assistance/documents/hsip/2024/lrsm2024-v2.pdf)
- Example rows from the LRSM tables:
  - SI01NT Add intersection lighting: Night, CRF 40%, 20 yr, Medium systemic
  - SI02 Improve signal hardware (lenses, retroreflective backplates…): All, 15%, 10 yr, Very High
  - NS13 Improve sight distance (clear sight triangles): All, 20%
  - NS14 High friction surface treatment: All, 55%
  - NS15 Splitter islands on minor road: All, 40%
  - NS18 Reduced left-turn conflict intersections: All, 50%
  - NS19 Right-turn lane: All, 20%
  - Source: [Caltrans LRSM v1.7](https://dot.ca.gov/-/media/dot-media/programs/local-assistance/documents/hsip/2024/lrsm2024-v2.pdf)
- Appendix B gives each countermeasure "Where to use," "Why it works," "General Qualities (Time, Cost and Effectiveness)," and a CMF Clearinghouse "Crash Types Addressed" with a CRF range.
  - Example SI01NT: use at "Signalized intersections that have a disproportionate number of night-time crashes and do not currently provide lighting… (this strategy would be supported by a significant number of crashes that occur at night)." Clearinghouse: Night, All; CRF 20–74%.
  - This "where to use" text is effectively a symptom trigger.
  - Source: [Caltrans LRSM v1.7](https://dot.ca.gov/-/media/dot-media/programs/local-assistance/documents/hsip/2024/lrsm2024-v2.pdf)
- LRSM warning: "a reasonable level of traffic 'engineering judgment' is required and… this manual should not be used as a simple cheat-sheet for preparing and submitting applications." — [Caltrans LRSM v1.7](https://dot.ca.gov/-/media/dot-media/programs/local-assistance/documents/hsip/2024/lrsm2024-v2.pdf)
- LRSM: practitioners "should be looking for patterns in the crash data and not just the total number of crashes. These patterns include: types of crashes, severity of crashes, mode of travel, pavement conditions, time of day." The LRSM recommends collision diagrams "showing the direction of movement of vehicles, types of crashes, and pedestrians involved." — [Caltrans LRSM v1.7](https://dot.ca.gov/-/media/dot-media/programs/local-assistance/documents/hsip/2024/lrsm2024-v2.pdf)
- **Combining CMFs (Caltrans HSIP rule):**
  - The multiplicative method is "a common, generally accepted method… presented in the HSM and in the CMF Clearinghouse."
  - "Caltrans only allows up to three (3) individual countermeasures… in the B/C ratio for a project location site." Each successive countermeasure applies "based on the remainder of the crashes after the effect of the prior countermeasures."
  - Using a CMF outside its range of applicability may over- or underestimate the effect.
  - Source: [Caltrans LRSM v1.7](https://dot.ca.gov/-/media/dot-media/programs/local-assistance/documents/hsip/2024/lrsm2024-v2.pdf)
- The HSIP Analyzer requires crash tables per crash-type dataset ("All", "Night", "Ped & Bike", etc.) matched to the selected countermeasures. — [Caltrans HSIP Analyzer instructions 2020](https://dot.ca.gov/-/media/dot-media/programs/local-assistance/documents/hsip/2020/hsipanalyzerinstructions2020bcr.pdf)

**FHWA FCFT Quick Reference Guide (FHWA-HRT-20-053, Nov 2020)**
- Six-step countermeasure selection:
  1. Identify a focus crash type, defined by maneuver × day/night × segment type (curve/tangent) or intersection type
  2. Identify contributing factors
  3. Assemble a candidate list from NCHRP 500, the HSM, the CMF Clearinghouse, Proven Safety Countermeasures, Countermeasures That Work, PEDSAFE, BIKESAFE and state toolboxes
  4. Keep countermeasures that explicitly address the contributing factors ("only a clear, explicit relation… should be indicated")
  5. Identify which have CMFs; give "extra consideration" to CMFs specific to the focus crash type
  6. Select
  - Source: [FHWA-HRT-20-053](https://www.govinfo.gov/content/pkg/GOVPUB-TD2-PURL-gpo154695/pdf/GOVPUB-TD2-PURL-gpo154695.pdf)
- Contributing-factor tables, derived from random-forest analysis of multistate data:
  - Angle crashes at rural two-lane 4-leg stop-controlled intersections: larger mainline AADT, larger cross-street AADT, wider lane width, higher design speed or speed limit (multiple states); absence of mainline left-turn channelization (select states).
  - Run-off-road crashes on rural two-lane curves: larger AADT, smaller curve radius, narrower shoulder (multiple states); grade, surface width, speed limit (one state).
  - Source: [FHWA-HRT-20-053](https://www.govinfo.gov/content/pkg/GOVPUB-TD2-PURL-gpo154695/pdf/GOVPUB-TD2-PURL-gpo154695.pdf)
- Systemic countermeasures linked to those factors:
  - Intersection: left- and right-turn lanes, yellow change intervals, retroreflective backplates, multiple low-cost countermeasures at stop-controlled intersections, advance signs.
  - Non-intersection: SafetyEdge, rumble strips and stripes, enhanced friction and enhanced delineation for curves, roadside design at curves, advance curve markings, advance signs.
  - Source: [FHWA-HRT-20-053](https://www.govinfo.gov/content/pkg/GOVPUB-TD2-PURL-gpo154695/pdf/GOVPUB-TD2-PURL-gpo154695.pdf)
- FHWA view on methods: "A predictive approach based on a combination of historical crash, exposure, and roadway data is more reliable than an approach based only on cross-tabulations or ad hoc analyses to identify geometric and operational attributes that may increase crash potential." — [FHWA-HRT-20-053](https://www.govinfo.gov/content/pkg/GOVPUB-TD2-PURL-gpo154695/pdf/GOVPUB-TD2-PURL-gpo154695.pdf)

**FHWA Proven Safety Countermeasures (PSC)**
- PSCs are grouped into Pedestrian, Roadway Departure, Intersections and Crosscutting. "Each countermeasure addresses at least one safety focus area." — [FHWA PSC](https://highways.dot.gov/safety/proven-safety-countermeasures)
- Items found on the page:
  - Backplates with Retroreflective Borders; Corridor Access Management; Crosswalk Visibility Enhancements
  - Dedicated Left- and Right-Turn Lanes; Enhanced Delineation for Horizontal Curves; Leading Pedestrian Interval; Lighting; Local Road Safety Plans
  - Longitudinal Rumble Strips/Stripes on Two-Lane Roads; Median Barriers; Medians and Pedestrian Refuge Islands; Pavement Friction Management
  - Pedestrian Hybrid Beacons; RRFB; Reduced Left-Turn Conflict Intersections; Road Safety Audit; Roadside Design Improvements at Curves; Roundabouts
  - SafetyEdge; Systemic Application of Multiple Low-Cost Countermeasures at Stop-Controlled Intersections; Walkways; Wider Edge Lines; Yellow Change Intervals
  - Source: [FHWA PSC](https://highways.dot.gov/safety/proven-safety-countermeasures)

**NCHRP Report 500 series**
- About 22 implementation guides are listed by FHWA. They include unsignalized intersections, signalized intersections, run-off-road, horizontal curves, head-on, trees, utility poles, pedestrians, bicycles, older drivers, speeding, work zones, heavy trucks and motorcycles, plus Vol. 21 "Safety Data and Analysis in Developing Emphasis Area Plans."
- Each strategy lists target group, expected effectiveness, keys to success, potential difficulties, measures and data, costs and other fields. The guides are explicitly intended "in site diagnosis… [and] to identify proven, tried, and experimental countermeasures."
- Source: [FHWA NCHRP 500 page](https://highways.dot.gov/safety/data-analysis-tools/rsdp/rsdp-tools/national-cooperative-highway-research-program-nchrp-1)

**PEDSAFE**
- Uses 12 crash-type groups defined by PBCAT. For each, it gives "possible cause/problem" → "candidate countermeasures," and it has interactive matrices relating 7 countermeasure groups to the 12 crash types and 8 performance objectives.
- Example: Dart/Dash; Cause #2, pedestrian struck crossing a high-speed and/or high-volume arterial → relocate bus stop, improve/add nighttime lighting, overpass/underpass…
- Example: multiple threat (stopped vehicle blocks view) → relocate bus stop to far side, improve lighting, curb extensions…
- PEDSAFE caveat: lists are not "comprehensive," and practitioners "are required to supplement the analysis."
- Sources: [PEDSAFE Crash Type Analysis](https://pedbikesafe.org/PEDSAFE/guide_analysis_CrashTypeAnalysis.cfm); [PEDSAFE matrices](http://walkinginfo.org/pedsafe/matrices/)

**FHWA STEP Field Guide (uncontrolled crossings)**
- Table 1 maps roadway configuration (2 lanes … 4+ lanes with or without raised median) × speed limit (≤30, 35, ≥40 mph) × AADT (<9,000; 9,000–15,000; >15,000) to countermeasure options.
- Table 2 maps "safety issues addressed" to countermeasures. Example: raised crosswalk for 2–3 lanes, AADT <9,000, ≤30 mph, addressing conspicuity and excessive speed; road diet addressing conflicts, speeds and insufficient separation.
- Source: [FHWA STEP Field Guide](https://rosap.ntl.bts.gov/view/dot/43674/dot_43674_DS1.pdf)

**CMF Clearinghouse star rating**
- 1–5 stars, "an exercise in judgment and a degree of subjectivity." Since about February 2021 it uses the NCHRP 17-72 150-point criteria.
- Before-after and cross-sectional studies are scored on data (55), study design/statistics (75) and significance (20).
- Score → stars: 135–150 = 5; 110–134 = 4; 75–109 = 3; 35–74 = 2; 0–34 = 1. A CMF needs at least 75 points (50%) for 3 stars.
- Example criteria: RTM addressed or systemwide treatment (25 points); ≥50 treatment sites/miles (10); ≥200 treatment-group crashes (10).
- Sources: [CMF Clearinghouse SQR](https://cmfclearinghouse.fhwa.dot.gov/sqr.php); [CMF rating transition flyer](https://cmfclearinghouse.fhwa.dot.gov/collateral/CMF_flier2.pdf); [CMF newsletter 2020Q4](https://cmfclearinghouse.fhwa.dot.gov/newsletter/2020Q4.html)
- FHWA: the Clearinghouse flags HSM-included CMFs, which "typically have a higher quality rating." Users should pick CMFs from studies with characteristics similar to their own site. — [FHWA Step 4 Diagnose](https://highways.dot.gov/safety/local-rural/improving-safety-rural-local-and-tribal-roads-safety-toolkit/step-4-diagnose)

**Combining multiple CMFs (FHWA/VHB, Gross & Hamidi, 2011)**
- HSM position: CMFs are multiplicative where treatments are concurrent and presumed independent. It is not appropriate to multiply CMFs that apply to different crash types or severities; instead, apply each to its own crash subset. The combined effect "may be over-estimated if the CMFs are multiplied."
- Methods reviewed: 4.1 multiplicative; 4.2 most-effective only; 4.3 systematic reduction, CMF2,red = (1−CMF2)/2 + CMF2; 4.4 Turner 2/3 dampening, CMF = 1 − ⅔(1 − CMF1·CMF2); plus meta-analysis and crash-type-overlap methods.
- Findings:
  - The multiplicative method "overestimates the actual reduction in a majority of instances" (Mounce 2005, cited).
  - Methods 4.1 and 4.3 fell within the range of actual combined-treatment studies; methods 4.2, 4.4 and 4.5 appeared to underestimate.
  - The report recommends "that no more than two CMFs be combined."
  - "Engineers should be equally concerned about overestimation and underestimation."
- Source: [FHWA Combining Multiple CMFs (2011)](https://cmfclearinghouse.fhwa.dot.gov/collateral/Combining_Multiple_CMFs_Final.pdf)
- A CMF is multiplied by expected crashes without treatment. CRF = 100% × (1 − CMF). — [FHWA Step 4 Diagnose](https://highways.dot.gov/safety/local-rural/improving-safety-rural-local-and-tribal-roads-safety-toolkit/step-4-diagnose)

**RSA prompt lists**
- FHWA RSA Guidelines (FHWA-SA-06-06), Section 8: prompt lists "help the RSA team identify potential safety issues and to ensure that they do not overlook something important." — [FHWA RSA Prompt Lists](https://highways.dot.gov/safety/data-analysis-tools/rsa/fhwa-road-safety-audit-guidelines/80-road-safety-audit-prompt-lists); [Prompt List](https://highways.dot.gov/safety/data-analysis-tools/rsa/fhwa-road-safety-audit-guidelines/prompt-list)

### Inferences
- A practical pattern-library schema follows from these sources:
  `facility_type × crash_pattern (type/movement/light/surface/party) → possible_contributing_factors[] (HSM Ex. 6-3..6-8, FCFT tables) → countermeasures[] (LRSM code, PSC flag, crash-type-addressed, CRF/CMF, star rating, CMF Clearinghouse ID, "where to use" trigger) → field_verification_items[]`
- Caltrans' crash-type groups (All, Night, P&B, EV, Animal) define how CRFs are applied in California HSIP. CrashIQ's cross-tab output should produce those exact subsets so B/C can be run in the HSIP Analyzer.
- For combined benefits, default to the Caltrans multiplicative method with a 3-countermeasure cap for California HSIP work. Show a conservative alternative (FHWA method 4.3) and warn when CMFs target different crash types.

### Gaps
- The full LRSM table (all ~86 countermeasures and CRFs) was not transcribed. The source PDF is cited; extract it programmatically from v1.8 if that version is current.
- The complete current PSC list was not fully verified. My parse may have missed speed-management and bicycle items, and FHWA has added items over time.
- BIKESAFE matrices were not reviewed. The Clearinghouse's minimum-star recommendation for HSIP use (e.g., ≥3 stars) is not stated in the retrieved pages, so I found no source for any specific threshold.

## Q4. Systemic risk factors and selecting locations without crash history

### Takeaway
The FHWA Systemic Safety Project Selection Tool (2013; updated by the 2024 Systemic Safety User Guide) has four steps:
1. Identify focus crash types and risk factors from systemwide severe-crash data
2. Screen and prioritize candidate locations by the presence of those risk factors, not crash counts
3. Select countermeasures
4. Prioritize projects

Risk factors are explicitly characteristics associated with crashes, not causes.

### Cited Findings
- Systemic planning "looks for similar issues across the roadway system rather than focusing on select locations with high crash histories." Candidates are found by "comparing the actual conditions of segments, curves, and intersections with a set of observed characteristics associated with the locations where the focus crash types actually occurred." — [FHWA Systemic Tool Element 1](https://highways.dot.gov/safety/data-analysis-tools/systemic/systemic-safety-project-selection-tool/element-1-systemic)
- "Identification of potential risk factors does not necessarily imply the observed characteristics 'caused' the crashes; rather… so that similar 'looking' locations can be identified and prioritized." — [FHWA Systemic Tool Element 1](https://highways.dot.gov/safety/data-analysis-tools/systemic/systemic-safety-project-selection-tool/element-1-systemic)
- Step 1 has three tasks: select focus crash types (those with the most severe crashes, often from SHSP emphasis areas); select focus facilities; identify and evaluate risk factors. — [FHWA Systemic Tool Element 1](https://highways.dot.gov/safety/data-analysis-tools/systemic/systemic-safety-project-selection-tool/element-1-systemic)
- Candidate risk-factor data:
  - Segments: lanes, shoulder type and width, road edge, access density, curve radius and superelevation, curve density, speed limit, curve/tangent speed differential, medians, pavement friction
  - Intersections: number of approaches, skew, proximity to curves, approach lanes, signal timing, rail proximity, traffic control, street lighting, commercial development
  - Source: [FHWA Systemic Tool Element 1](https://highways.dot.gov/safety/data-analysis-tools/systemic/systemic-safety-project-selection-tool/element-1-systemic)
- Example: NYSDOT disaggregated fatal and serious injury crashes by emphasis area and system. Intersections were 41% statewide, but roadway departure was the largest share on the state system (30%), so NYSDOT chose roadway departure as its focus. — [FHWA Systemic Tool Element 1](https://highways.dot.gov/safety/data-analysis-tools/systemic/systemic-safety-project-selection-tool/element-1-systemic)
- The FCFT guide allows thresholds and weights. Example: "rather than simply identifying sites with horizontal curves, an analyst may specify the degree of curve over or radius under which crash potential increases," with more weight on sharper curves than on narrower lanes. — [FHWA-HRT-20-053](https://www.govinfo.gov/content/pkg/GOVPUB-TD2-PURL-gpo154695/pdf/GOVPUB-TD2-PURL-gpo154695.pdf)
- Caltrans LRSM systemic benefits include "Reduced data needs. The Systemic Approach can be used without a detailed crash history." The spot-location approach is "ideally implemented along with the Systemic Approach." — [Caltrans LRSM v1.7](https://dot.ca.gov/-/media/dot-media/programs/local-assistance/documents/hsip/2024/lrsm2024-v2.pdf)
- For uncontrolled ped crossings, STEP selects countermeasures from lanes, median, speed limit and AADT, which are systemic risk-type attributes, plus observed issues. — [FHWA STEP Field Guide](https://rosap.ntl.bts.gov/view/dot/43674/dot_43674_DS1.pdf)
- The 2024 Systemic Safety User Guide is "a substantial update" to the 2013 tool. — [FHWA Systemic Safety User Guide 2024](https://highways.dot.gov/sites/fhwa.dot.gov/files/2024-07/SystemicSafetyUserGuide.pdf)

### Inferences
- CrashIQ can support systemic analysis by computing, across the whole network, the over-representation of site attributes among severe focus-crash locations versus all locations (e.g., share of KA ROR crashes on curves under radius X versus share of mileage). It can then score uncrashed sites by attribute presence with weights. This requires a roadway inventory (MIRE-type), not just crash data.

### Gaps
- The 2024 Systemic Safety User Guide PDF could not be downloaded (bot block), so updated risk-scoring steps were not reviewed.
- Specific published risk-factor thresholds were not collected. FHWA presents them as agency-derived.

## Q5. Collision diagram automation, crash trees, and defensibility/documentation

### Takeaway
Automated collision diagrams are established commercially and in public tools. They bucket crashes by manner of collision, vehicle directions and first harmful event, and let analysts correct miscoded attributes from narratives. Guidance on defensibility rests on documenting the data period, the reference population, RTM handling, CMF source and quality, and engineering judgment. I found no US standard for "crash tree" methods.

### Cited Findings
- The HSM endorses software-generated collision diagrams for multiple sites and a standard symbol set from the ITE *Manual of Transportation Engineering Studies*. — [HSM Ch.5 draft](https://ftp.granit.unh.edu/submissions/NHDOTOUT/craig/HSM/Chapter%205_Diagnosis.pdf)
- Numetric markets automated intersection collision diagrams.
  - Crashes are "bucketed by the manner of the collision, the travel direction of the first and second vehicle, and the first harmful event (to ensure bikes, pedestrians, and animals are part of the analysis)."
  - Engineers can read officer narratives and "update incorrect crash attributes such as manner of the collision, travel direction, vehicle maneuver, and first harmful event."
  - This is vendor material and not independently validated.
  - Source: [Numetric Collision Diagrams](https://numetric.com/intersection-analytics/collision-diagrams)
- FHWA lists the Accident Information Management System (AIMS), a GIS tool with intersection and mid-block crash analysis modules, among its safety data tools. — [FHWA AIMS](https://highways.dot.gov/safety/data-analysis-tools/rsdp/rsdp-tools/accident-information-management-system-aims)
- Academic work is automating crash diagrams with vision-language models (multi-lane roundabout case study, arXiv preprint, not peer-reviewed). — [arXiv 2604.15332](https://arxiv.org/pdf/2604.15332v1.pdf)
- ODOT offers a Crash Graphing Tool, a Crash Decoder Tool and a Visum add-in, and limits approximate crash attribution to planning-level use. — [ODOT APM Appendix 4A](https://www.oregon.gov/odot/Planning/Documents/APMv2_App4A.pdf)
- Defensibility elements found in the sources:
  - 3–5 year study period ([HSM Ch.5](https://ftp.granit.unh.edu/submissions/NHDOTOUT/craig/HSM/Chapter%205_Diagnosis.pdf))
  - Similar-site reference populations ([HSM Ch.5](https://ftp.granit.unh.edu/submissions/NHDOTOUT/craig/HSM/Chapter%205_Diagnosis.pdf))
  - RTM awareness ([LRSM](https://dot.ca.gov/-/media/dot-media/programs/local-assistance/documents/hsip/2024/lrsm2024-v2.pdf))
  - CMF applicability ranges, and consistent application of one combining method across all projects "to ensure a fair comparison" ([LRSM](https://dot.ca.gov/-/media/dot-media/programs/local-assistance/documents/hsip/2024/lrsm2024-v2.pdf))
  - CMF star rating and study similarity ([CMF Clearinghouse](https://cmfclearinghouse.fhwa.dot.gov/sqr.php))
  - Location-coding caveats ([HSM Ch.5](https://ftp.granit.unh.edu/submissions/NHDOTOUT/craig/HSM/Chapter%205_Diagnosis.pdf))
  - Field verification of data-derived concerns ([HSM Ch.5](https://ftp.granit.unh.edu/submissions/NHDOTOUT/craig/HSM/Chapter%205_Diagnosis.pdf))
  - Formal written owner response for RSAs ([FHWA Step 4](https://highways.dot.gov/safety/local-rural/improving-safety-rural-local-and-tribal-roads-safety-toolkit/step-4-diagnose))
- The Haddon Matrix is the structured "event-sequence" framework that FHWA and the HSM recommend for organizing pre-crash, crash and post-crash factors. It is the closest documented analogue to a crash tree. — [FHWA Step 4 Diagnose](https://highways.dot.gov/safety/local-rural/improving-safety-rural-local-and-tribal-roads-safety-toolkit/step-4-diagnose); [HSM Ch.6 draft](https://ftp.granit.unh.edu/submissions/NHDOTOUT/craig/HSM/Chapter%206_SelectingCountermeasures.pdf)

### Inferences
- An automated collision diagram should key on manner of collision, vehicle 1 and 2 directions and movements, approach or leg, and first harmful event. It should expose the narrative for QA, since miscoded direction or type is a known failure mode.
- To be defensible to reviewers, each CrashIQ finding should carry an audit trail:
  - Data source and period
  - Crash-location assignment rule (e.g., an intersection influence radius)
  - Reference population and threshold p*
  - Test statistic and limiting probability
  - The HSM/LRSM/FCFT table row used for each contributing factor
  - CMF ID, star rating and applicability notes
  - Explicit "field verification required" items

### Gaps
- I found no FHWA or AASHTO standard for "crash tree" or fault-tree diagnosis in US practice. Mentions online appear to be ad hoc or non-US.
- I found no formal published reviewer checklist (e.g., from Caltrans HSIP or FHWA) on documentation for automated diagnosis. Defensibility expectations above are compiled from method guidance, not a single checklist.
- The ITE symbol standard was not retrieved (ITE is paywalled).
