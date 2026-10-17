# Crash-Analysis Research Frontier: TRB Safety Committees, Recent Research Themes, NCHRP Projects, and ML-vs-SPF Evidence (2022–2026)

Scope note: written for a CrashIQ gap analysis (California corridor crash-analysis web tool with an AI analyst that writes findings from computed tables). Preprints are marked **[preprint]**. Items before 2022 are marked **[pre-2022, foundational]**.

## Q1. Is "the January conference in Washington DC with topic committees" the TRB Annual Meeting, and which TRB committees and other venues matter for crash/safety analysis?

### Takeaway
Yes. It is the Transportation Research Board (TRB) Annual Meeting, held every January in Washington, DC. The 105th meeting ran January 11–15, 2026, at the Walter E. Washington Convention Center and Marriott Marquis. Two Safety Section committees are the core of crash analytics: **ACS20 Safety Performance and Analysis** (methods: SPFs, EB, network screening, CMFs, surrogates, crash data) and **ACS10 Transportation Safety Management Systems** (programs and policy). **AED60 Statistical and Econometric Methods** is the statistical-methods home. ACS20 also publishes a free yearly "Synthesis Report on Safety-Related Papers," which is the best single map of the field.

### Cited Findings
**The meeting**
- The 2026 TRB Annual Meeting (the 105th) ran January 11–15, 2026, at the Walter E. Washington Convention Center and Marriott Marquis in Washington, DC. The program and paper abstracts are in the Online Program (annualmeeting.mytrb.org). The 2027 meeting site is live. — [National Academies event page](https://www.nationalacademies.org/events/886); [2027 page](https://www.nationalacademies.org/events/887)
- TRB has nearly 200 standing technical committees. — [Wikipedia: TRB](https://en.wikipedia.org/wiki/Transportation_Research_Board) (secondary source)

**Safety Section (ACS00) committees.** The 2020 TRB reorganization chart lists: Transportation Safety Management Systems (ACS10), Safety Performance Analysis (ACS20), Traffic Law Enforcement (ACS30), Occupant Protection (ACS40), and Impaired Driving (later "Impairment in Transportation", ACS50). — [TRB Committee Structure 4-15-2020 (org chart PDF)](https://travelsurveymethods.org/wp-content/uploads/2020/06/TRBOrganizationChart.pdf)

**ACS20 – Standing Committee on Safety Performance and Analysis**
- Scope: "the advancement, integration and institutionalization of quantitative highway safety information to support transportation decision-making at all levels… foster the continual development, validation and increased knowledge of science-based methods, procedures and measures." — [104th TRBAM Synthesis Report (ACS20)](https://trbacs20.org/wp-content/uploads/2025/01/104th-TRBAM-Synthesis-Report-on-Safety-Related-Papers.pdf)
- ACS20 was formed after the 2020 Annual Meeting by merging two committees: Highway Safety Performance (ANB25) and Safety Data, Analysis and Evaluation (ANB20). Its scope covers "the collection, maintenance and use of crash records and related roadway, road user, and vehicle data; the development of theories, analytical techniques, and evaluation methodologies." — [ACS20(3) subcommittee page](https://trbacs20.org/index.php/about/subcommittees/surrogate-safety-measures); [2013 ANB20 synthesis](https://trbacs20.org/wp-content/uploads/2021/01/2013_92ndTRBAM_Synthesis-Report-on-Safety-Related-Papers.pdf)
- Subcommittees:
  - Safety Analytical Methods, ACS20(1)
  - User Liaison, ACS20(2)
  - Surrogate Safety Measures, ACS20(3)
  - Pedestrian and Bicycle Safety Analysis, ACS20(4), joint with ACH10 and ACH20
  - Joint with ACS10 and AKD30: Rural Road Safety Policy, Programming, and Implementation, ACS10(4)
  - Source: [ACS20 About](https://trbacs20.org/index.php/about)
- The ACS20(3) Surrogate Safety Measures subcommittee covers indicators that "do not require to wait for accidents to happen," such as speed, time-to-collision (TTC), and post-encroachment time (PET). — [ACS20(3)](https://trbacs20.org/index.php/about/subcommittees/surrogate-safety-measures)
- Leadership changed between sources. As of November 2024 the chair was Derek Troyer (FHWA) and the research coordinator was Jonathan Wood (Iowa State) ([104th Synthesis](https://trbacs20.org/wp-content/uploads/2025/01/104th-TRBAM-Synthesis-Report-on-Safety-Related-Papers.pdf)). The 2024 new-attendee table listed Karen Dixon (TTI) as chair ([TRB 2024 New Attendee Table 14](https://onlinepubs.trb.org/onlinepubs/am/2024/NewAttendee/Table14.pdf)), which likely reflects an earlier term.

**ACS10 – Standing Committee on Transportation Safety Management Systems**
- Focus: "the development and coordination of integrated safety management programs to reduce death and injury." — [104th Synthesis](https://trbacs20.org/wp-content/uploads/2025/01/104th-TRBAM-Synthesis-Report-on-Safety-Related-Papers.pdf)
- Members include a Caltrans representative (Rachel Carpenter) and representatives from FHWA, NHTSA, iRAP, and consultancies. — same source
- Subcommittees seen in 2025: School Transportation ACS10(3); Motorcycle and Moped Safety ACS10(5), joint with ACH60. — same source

**AED60 – Standing Committee on Statistical and Econometric Methods** (formerly "Statistical Methods")
- Scope: "development and appropriate application of statistical and econometric methods in the field of transportation"; it serves as "a resource on statistical matters for all other TRB committees." — [AED60 site](http://trbstats.weebly.com/)
- At TRB 2025 it co-organized with the AED00 Data and Data Science Section the session "New-Generation Transport Safety Analysis Using High-Resolution Data: Advanced Statistical and Machine Learning Models" (Lectern 2174). It also ran a safety-and-behavior econometrics session (Lectern 2006). — [AED60 site](http://trbstats.weebly.com/)

**Other committees that sponsor safety papers**
- In the 104th (2025) safety synthesis, paper sponsorship counted: ACS20 165, ACS10 87, ACH30 Human Factors of Vehicles 11, ACH10 Pedestrians 5, ACP10 Regional TSMO 1. — [104th Synthesis](https://trbacs20.org/wp-content/uploads/2025/01/104th-TRBAM-Synthesis-Report-on-Safety-Related-Papers.pdf) (counted from the PDF text)
- Roadside Safety Design committee: AKD20. — [AKD20 site](https://sites.google.com/site/trbcommitteeakd20/)
- An FHWA Safe System workshop slide also lists ACS30 Traffic Law Enforcement, ACS40 Occupant Protection, ACS60 Truck and Bus, AKD10 Performance Effects of Geometric Design, ACH10 Pedestrian, and ACH20 Bicycle. — [Dimaiuta slides, ACS20 Midyear 2021](https://trbacs20.org/wp-content/uploads/2021/07/Dimaiuta_SafeSystemsWorkshopUpdate_ACS20Midyear2021.pdf)
- Code conflict for Truck and Bus Safety: shown as ACS60 in 2020–2023 minutes, but the committee's current site calls it ACD14. — [2020 minutes](https://www.ugpti.org/trb/truckandbus/meetings/2020/2020-meeting-minutes.pdf); [committee site](https://www.ugpti.org/trb/truckandbus/)

**2025 Annual Meeting volume and topic mix (ACS10/ACS20)**
- 28 sponsored events: 3 committee meetings, 8 subcommittee meetings, 2 workshops, 6 lectern sessions, 9 poster sessions. — [104th Synthesis](https://trbacs20.org/wp-content/uploads/2025/01/104th-TRBAM-Synthesis-Report-on-Safety-Related-Papers.pdf)
- Papers by topic (some papers fall in more than one category):

  | Topic | Papers |
  |---|---|
  | Crash Data and Safety Analysis | 176 |
  | Crash Severity Prediction | 93 |
  | Safety Effects of CAVs | 77 |
  | Transportation Safety Management | 72 |
  | Surrogate Measures of Safety | 62 |
  | Network Screening | 18 |
  | Safety Performance Functions | 15 |
  | Real-Time Safety Prediction | 15 |
  | CMFs/CMFunctions | 10 |

  Source: same report
- Session titles included "Safety Performance and Analysis Using Machine Learning or Artificial Intelligence" (Poster 3147), "Decision Making with Safety Surrogates" (Lectern 2171), and "Safety Performance and Analysis with Crash Predictions" (Poster 2206). — same report

**Other venues**
- *Accident Analysis & Prevention* (Elsevier) was founded by Frank Haight in 1969. — [AA&P 50-year bibliometric review (PubMed)](https://pubmed.ncbi.nlm.nih.gov/32562929)
- *Transportation Research Record* (TRR, SAGE) is TRB's journal. Example: vol. 2680 issue 9 (2026). — [TRID record](https://trid.trb.org/View/2652210)
- Lifesavers Conference on Roadway Safety (behavioral and highway-safety-office focus): 2026 edition April 19+, Baltimore, MD, with 70+ workshops in 10 tracks. — [NHTSA event page](https://www.nhtsa.gov/events/lifesavers-conference); [lifesaversconference.org](https://lifesaversconference.org/)
- ITE International Annual Meeting 2026: July 19–22, 2026, Detroit (joint with Great Lakes District). — [ITE 2026 onsite guidebook](https://www.ite.org/ITEORG/assets/File/Annual%20Meeting/2026/ITE_2026_OnsiteProgram_FINAL.pdf)
- *TR News* (TRB magazine) carries practitioner summaries of NCHRP safety work. — [TR News article](https://trnews.org/leveraging-ai-and-big-data-to-enhance-safety-analysis)

### Inferences
- For product benchmarking, the yearly ACS20 synthesis report (trbacs20.org) is the most efficient way to track what is new. It sorts every safety paper into the HSM-process stages that CrashIQ already uses (screening, SPF, CMF, severity).
- By paper count, research attention leans heavily toward severity modeling, surrogates, and CAVs, rather than SPFs or network screening. SPF/EB practice is mature; the new work is in leading indicators and ML/LLM tooling.

### Gaps
- I did not find a current authoritative TRB list of all Safety Section committee codes. The National Academies standing-committee page did not render.
- I could not confirm the current code or name of a dedicated "Traffic Records / crash records" committee. The former ANB20 crash-records scope was absorbed into ACS20.
- I did not verify the managed-lanes committee the user remembered; it is outside safety scope.
- The 105th (2026) synthesis report was not at the expected URL. That URL returned HTML, not a PDF.

## Q2. Recent research themes (2022–2026)

### Takeaway
Six fronts are active:
1. ML/DL crash-frequency and severity models, almost always paired with SHAP for interpretability.
2. EB variants and non-parametric EB.
3. Surrogate safety measures from video, drones, and connected-vehicle (CV) hard-braking data, used for proactive screening. This is close to mainstream: Google and FHWA/NCHRP are investing in it.
4. LLMs for crash narratives (classification, data-quality QC, causation). Results are promising but uneven.
5. Safe System metrics that model kinetic energy and fatal/serious-injury (FSI) probability.
6. Equity-oriented disparity analysis.

### Cited Findings
**Network screening and EB (2025 TRB)**
- The 2025 network-screening papers proposed new SPFs and CMFs to strengthen HSM procedures, "the EB method has been frequently used to rank road sites, as well as the Spatial Autocorrelation. Machine and Deep Learning algorithms are also frequently used… novel data sources coming from both CAVs, and video from cameras and drones, are used for proactive network screening." — [104th Synthesis, Ch. 3 (Fiorentini & Losa)](https://trbacs20.org/wp-content/uploads/2025/01/104th-TRBAM-Synthesis-Report-on-Safety-Related-Papers.pdf)
- The 2025 SPF papers mostly kept negative binomial models. Some tested Poisson-lognormal-Lindley and random-parameter models for excess zeros or temporal/spatial variability, plus macro-level (zonal) SPFs. One paper added TTC as a covariate. — same source, Ch. 4 (Montella et al.)
- Non-parametric EB: CGAN-EB uses conditional GANs in place of the parametric SPF inside EB for hotspot identification. — [arXiv 2112.10588](https://arxiv.org/html/2112.10588v1) [preprint of a journal paper; the arXiv listing names Accident Analysis & Prevention; 2021]
- EB was compared against Potential for Safety Improvement using NB variants for hotspot identification. — [Sustainability (MDPI) 2024, 16(4):1537](https://www.mdpi.com/2071-1050/16/4/1537)

**ML/DL plus interpretability**
- 2025 TRB crash-data papers covered ML methods, LLMs (paper 25-05236), and deep generative models (25-06171). — [104th Synthesis, Ch. 2](https://trbacs20.org/wp-content/uploads/2025/01/104th-TRBAM-Synthesis-Report-on-Safety-Related-Papers.pdf)
- Term counts in the 2025 synthesis text: "machine learning" 181, "SHAP" 57, "Bayesian" 62, "LLM" 20. — same source (my counts from the PDF text, so indicative only)
- An AA&P (2022) paper on ML interpretability in crash-frequency modeling and CMF development reviewed:
  - post-hoc methods: LIME, PDP, global sensitivity analysis, SHAP
  - the trade-off that interpretable-by-design models (CART, MARS) "can result in low predictive accuracy… the derived relationships are inaccurate and can sometimes be misleading"
  - Source: [AA&P S0001457522000537](https://sciencedirect.com/science/article/pii/S0001457522000537)
- Hybrid model: random-forest SHAP combined with random-parameter NB for bicycle crash frequency. — [PubMed 39288451](https://pubmed.ncbi.nlm.nih.gov/39288451)
- Stacking framework: frequentist plus ML heterogeneous ensemble for crash forecasts. — [PubMed 36868672](https://pubmed.ncbi.nlm.nih.gov/36868672)

**Real-time prediction**
- 2025 papers predicted crash likelihood and conflicts in real time. They used extreme value theory (EVT) on TTC, CV data, INRIX speeds, crowdsourced vehicle movements, and UAV data, and dealt with class imbalance. — [104th Synthesis, Ch. 8 (Abdel-Aty & Yang)](https://trbacs20.org/wp-content/uploads/2025/01/104th-TRBAM-Synthesis-Report-on-Safety-Related-Papers.pdf)

**Surrogate safety measures and CV hard braking**
- 62 SMoS papers at TRB 2025: 20 on intersections, 16 on pedestrians/non-motorized users, 24 using traffic conflicts, 17 using simulation. — same source, Ch. 7 (Liu & Saunier)
- Google Research (arXiv Jan 2026) linked Android Auto hard-braking events (HBEs) to police-reported crashes in **California** and Virginia using NB regression, controlling for road type, speed profile, ramp proximity, and slope:
  - an HBE is defined as deceleration beyond −3 m/s²
  - 18× more segments had observed HBEs than had reported crashes
  - HBE rate was significantly and positively associated with crash rate
  - California crash data came from CCRS (data.ca.gov)
  - Sources: [arXiv 2601.06327](https://arxiv.org/abs/2601.06327) [preprint]; [Google Research blog, Jan 13 2026](https://research.google/blog/hard-braking-events-as-indicators-of-road-segment-crash-risk)
- Purdue/INDOT: CV trajectory data used to screen networks for hard braking and hard acceleration. — [Purdue JTRP 1910](https://docs.lib.purdue.edu/jtrp/1910)
- Large-scale study of normalized CV hard braking at signals, roundabouts, and all-way stops (2024). — [MDPI Future Transportation 4(3):46](https://mdpi.com/2673-7590/4/3/46)
- Fleet telematics driver-behavior indices proposed as surrogates for network screening. — [PubMed 36401975](https://pubmed.ncbi.nlm.nih.gov/36401975)
- AI video analytic tool for proactive intersection evaluation using surrogates (AA&P 2023). — [S0001457523003111](https://www.sciencedirect.com/science/article/abs/pii/S0001457523003111)
- City deployment: Bellevue, WA analyzed about 5,000 hours of camera video with AI conflict analytics. — [Seattle Times](https://www.seattletimes.com/seattle-news/transportation/bellevue-uses-ai-technology-to-identify-problem-intersections-and-make-them-safer)
- Review of SMoS on roads (AA&P 2024). — [Sarkar et al., S000145752300427X](https://www.sciencedirect.com/science/article/abs/pii/S000145752300427X)

**LLMs and NLP on crash narratives**
- Kentucky secondary-crash identification [preprint 2025]: 16,656 manually reviewed narratives, tested on 2022 data.
  - Fine-tuned RoBERTa: F1 0.90, accuracy 95%.
  - Zero-shot LLaMA3-70B: F1 0.86, but 139 minutes of inference.
  - Logistic-regression baseline: F1 0.66.
  - Context: only 8–13% of crashes coded "secondary" in 2015–2017 were truly secondary.
  - The authors recommend privacy-preserving local deployment.
  - Source: [arXiv 2508.04399](https://arxiv.org/abs/2508.04399)
- "Accuracy is Not Agreement" (IEEE ITSC 2025): models with higher technical accuracy often agreed less with human experts. LLMs (GPT-4, LLaMA 3, Qwen, Claude) aligned better with experts despite lower accuracy. The authors argue for Cohen's kappa and expert-agreement metrics. — [arXiv 2504.13068](https://arxiv.org/abs/2504.13068)
- CrashLLM / CrashEvent dataset (19,340 Washington State crash reports): fine-tuned LLMs raised average F1 from 34.9% to 53.8% for predicting crash type, severity, and injuries. It was also presented at TRB 2025. — [arXiv 2406.10789](https://arxiv.org/abs/2406.10789v1) [preprint]; [104th Synthesis](https://trbacs20.org/wp-content/uploads/2025/01/104th-TRBAM-Synthesis-Report-on-Safety-Related-Papers.pdf)
- Crash severity inference with GPT-3.5, LLaMA3-8B, and LLaMA3-70B, using chain-of-thought prompting and domain prompts. Tabular records were converted to template narratives. — [arXiv 2408.04652](https://arxiv.org/abs/2408.04652); published in [MDPI Computers 13(9):232](https://mdpi.com/2073-431X/13/9/232)
- TRB 2025 paper 25-05236: an LLM for freeway crash-causation analysis, trained on a dataset compiled from 226 freeway safety studies. — [104th Synthesis](https://trbacs20.org/wp-content/uploads/2025/01/104th-TRBAM-Synthesis-Report-on-Safety-Related-Papers.pdf)

**Safe System and kinetic energy**
- FHWA's Safe System-based framework and methodology for intersections (SSI, FHWA-SA-21-008). — [FHWA Tech Brief](https://highways.fhwa.dot.gov/media/11311)
- Kinetic Velocity Index (TRR 2026): estimates crash-level probability of FSI outcomes. It builds on FHWA SSI, uses more than 900,000 two-vehicle intersection crashes (2013–2024), was developed on Georgia data, and was validated on Massachusetts data. — [TRID 2652210](https://trid.trb.org/View/2652210); [TRR DOI](https://journals.sagepub.com/doi/10.1177/03611981251407922)
- 2025 TRB sessions included "Creating a Safer System" and a Safe System workshop on impaired driving. — [104th Synthesis](https://trbacs20.org/wp-content/uploads/2025/01/104th-TRBAM-Synthesis-Report-on-Safety-Related-Papers.pdf)

**Equity**
- FHWA-HRT-25-035 (Dec 2024), *Exploring Risk Factors to Disparities in Pedestrian and Bicyclist Fatalities and Serious Injuries*: a 151-page scoping review covering how to frame sociodemographic categories, spatial units, and outcome measures, linked to the Safe System approach. — [FHWA PDF](https://highways.dot.gov/sites/fhwa.dot.gov/files/FHWA-HRT-25-035.pdf)
- The word "equity" appears 22 times in the 2025 synthesis text. — [104th Synthesis](https://trbacs20.org/wp-content/uploads/2025/01/104th-TRBAM-Synthesis-Report-on-Safety-Related-Papers.pdf)
- Example studies: GIS-based crash equity analysis (Atlanta) ([TRID 2390027](https://trid.trb.org/View/2390027)); Houston non-motorist equity study that accounts for roadway confounders ([TRID 2382389](https://trid.trb.org/View/2382389)).

**Crash data quality**
- NCHRP 07-35 found that active-transportation crash data suffer from inconsistent reporting, inaccurate or incomplete coding, underreporting, and thin crash typing. — [NCHRP 07-35 project page](http://apps.trb.org/cmsfeed/TRBNetProjectDisplay.asp?ProjectID=5492)

### Inferences
- What sits closest to the frontier for CrashIQ:
  - LLM narrative QC and classification (cheap, local, auditable)
  - CV hard-braking as a leading indicator (California-validated)
  - FSI/KE-weighted Safe System metrics alongside EB rankings
- Validating LLM outputs against expert labels is now a standard research expectation. That supports adding agreement checks to CrashIQ's AI-analyst output.
- Geocoding and location-quality research was nearly absent from the 2025 synthesis ("geocod" appears once). It is a practice problem more than a research topic.

### Gaps
- I did not fetch full 2025–2026 systematic reviews of DL crash prediction or graph neural networks ("graph neural" appears 3 times in the 2025 synthesis; no specific paper verified).
- No specific peer-reviewed study on crash geocoding accuracy was verified in this pass.
- The 2026 (105th) topic counts were not retrieved.

## Q3. Active and recent NCHRP projects relevant to safety analysis

### Takeaway
The most relevant projects:
- NCHRP **17-100**, published as Research Report 1152 (2025): an AI/ML and big-data guide for safety analysis.
- NCHRP **17-71A**, published as Report 1140: the proposed HSM 2nd edition.
- NCHRP **17-149** (anticipated, FY2027): hard braking and other CV metrics as surrogates.
- NCHRP **17-86**, published as Report 1069: CMFs from surrogate measures.
- NCHRP **07-35 / 07-35A**: crash data for active-transportation users.

### Cited Findings
- **NCHRP 17-100 → Research Report 1152 (2025)**, *Leveraging Artificial Intelligence and Big Data to Enhance Safety Analysis: A Guide*.
  - Authors: Yinhai Wang et al. (University of Washington), Texas Tech, DKS Associates, Fred Mannering (USF), and others.
  - It proposes seven steps for designing an ML system, from clarifying requirements through evaluation, and "a planning-first pathway for machine-learning."
  - It notes that most agency users apply models without retraining them, so they must understand model limits.
  - It lists weaknesses by algorithm: SVM/KNN can "become a black box"; decision trees are unstable ("a small change in the data can cause a large change in the results"); Bayesian networks require "greater statistical expertise"; deep learning is computationally demanding.
  - It frames crash-history-only screening as reactive, volume-biased, and "biased by short-term fluctuations… regression to the mean."
  - Sources: [Report PDF](https://nap.nationalacademies.org/resource/29098/9780309599603_508.pdf); [TRID 2678815](https://trid.trb.org/View/2678815); [TR News summary](https://trnews.org/leveraging-ai-and-big-data-to-enhance-safety-analysis)
- **NCHRP 17-71A**, *Proposed AASHTO Highway Safety Manual, Second Edition*. Status: Final. TTI (PI Darren Torbic), $709,705, 1/21/2021–5/21/2024. Published as NCHRP Research Report 1140 (doi 10.17226/28851). — [Project page](http://apps.trb.org/cmsfeed/TRBNetProjectDisplay.asp?ProjectID=5043); [NAP read](https://nationalacademies.org/read/28851/chapter/5)
- **NCHRP 17-149 [Anticipated]**, *Assessing the Reliability of Hard Braking and Other Vehicle-Based Metrics as Surrogate Safety Measures*. $600,000, FY2027, "In development." Not yet awarded. Problem statement: "the reliability and validity of these surrogate measures are not universally" established. — [Project page](http://apps.trb.org/cmsfeed/TRBNetProjectDisplay.asp?ProjectID=6054); [RIP 2712175](https://rip.trb.org/View/2712175)
- **NCHRP 17-86 → Research Report 1069**, *Estimating Effectiveness of Safety Treatments in the Absence of Crash Data: A Guide*. Covers using surrogate measures to develop CMFs. — [TRID 2260068](https://trid.trb.org/View/2260068); [Implementation memo](https://onlinepubs.trb.org/onlinepubs/nchrp/nchrp_rpt_1069Memo.pdf)
- **NCHRP 07-35**, *Improving Crash Data for Active Transportation Users*. UNC (PI Laura Sandt), $499,980, 7/8/2024–9/15/2025. Only partially completed; remaining work continues under **07-35A**. — [Project page](http://apps.trb.org/cmsfeed/TRBNetProjectDisplay.asp?ProjectID=5492)
- **NCHRP Research Report 1181**, *Toolkit for Institutionalizing the Safe System Approach* (2026). — [RIP 1957094](https://rip.trb.org/View/1957094); [TPM portal](https://www.tpm-portal.com/document/nchrp-report-1181-toolkit-for-institutionalizing-the-safe-system-approach-2026/)
- *A Guide to Applying the Safe System Approach to Transportation Planning, Design…* — [NAP 29147](https://www.nationalacademies.org/read/29147); [RIP 1842750](https://rip.trb.org/View/1842750)
- **NCHRP Research Report 1170** (Tech Brief): ATSPMs for proactive safety monitoring at signals. — [Tech Brief PDF](https://nap.nationalacademies.org/resource/29354/NCHRP_Rep_1170_Tech_Brief.pdf)
- From a December 2022 FHWA CMF Clearinghouse overview: NCHRP 17-95 (CMFs for ITS applications, completion expected 2023) and NCHRP 17-104 (roadside design safety prediction models). — [CMF Clearinghouse webinar slides](https://cmfclearinghouse.fhwa.dot.gov/collateral/dec2022webinar_NCHRP_ProjectsOverview.pdf)
- NCHRP Implementation Support Program project on the areawide approach to roadway safety management. — [RIP 2213755](https://rip.trb.org/View/2213755)

### Inferences
- NCHRP 17-149 shows the field does not yet treat CV hard braking as validated for agency decisions. A product feature built on it should label it as an experimental leading indicator.
- Report 1152 is the closest official benchmark for an "AI analyst" feature: start with requirements, have a human double-check output, and keep evaluation benchmarks.

### Gaps
- I did not retrieve the NCHRP project numbers for Report 1181 or 1170, or the full current list of active 17-series safety projects. The apps.trb.org search was not run exhaustively.
- I did not verify an NCHRP project specifically on LLMs for crash data.

## Q4. Reliability of ML prediction vs SPF/EB, and cautions

### Takeaway
Many studies report ML matching or slightly beating NB SPFs on in-sample or holdout fit. The methodological literature and NCHRP 1152 stress four counterweights:
- prediction accuracy is not causal or CMF validity
- tree models are unstable and data-driven models transfer poorly
- RTM and low counts still require EB-style shrinkage
- interpretability, including agreement with experts, is required for defensibility

SPF+EB remains the HSM standard. HSM2 (NCHRP 17-71A) continues that framework.

### Cited Findings
- Mannering, Bhat, Shankar & Abdel-Aty (2020) [pre-2022, foundational]: traditional analysis implicitly assumes a well-estimated model will both reveal causal effects and give the best prediction. Data-driven methods break that link, so there is a trade-off between prediction and causality in highway-safety analysis. — [Analytic Methods in Accident Research 25:100113](https://sciencedirect.com/science/article/pii/S2213665720300038); [author PDF](http://caee.webhost.utexas.edu/prof/bhat/ABSTRACTS/Prediction_causality.pdf)
- AA&P 2022: post-hoc interpretation (SHAP, PDP, etc.) is needed to derive CMF-like relationships from ML. Simple interpretable models can give "inaccurate… misleading" relationships. — [AA&P S0001457522000537](https://sciencedirect.com/science/article/pii/S0001457522000537)
- NCHRP 1152 cautions:
  - decision-tree instability
  - SVM/KNN opacity
  - the transferability of data-based neural networks is limited ("optimal neural network structures can vary per bin, lane, site… this could be an issue that limits the model's transferability")
  - in its example workflow, an engineer double-checks ML outputs
  - Source: [NCHRP 1152](https://nap.nationalacademies.org/resource/29098/9780309599603_508.pdf)
- Regression to the mean (RTM) and the reactive nature of crash-only screening are explicit motivations in NCHRP 1152. — same
- EB is the HSM/SafetyAnalyst approach, combining SPF predictions with observed counts. — [Full vs Simple SPFs, TRR 2398](https://doi.org/10.3141/2398-10) [pre-2022]; [MDPI 2024 EB vs PSI](https://www.mdpi.com/2071-1050/16/4/1537)
- Transfer learning (TrAdaBoost.R2) has been proposed to improve crash-model transferability across jurisdictions. — [AA&P S0001457519317166](https://sciencedirect.com/science/article/pii/S0001457519317166) [pre-2022]
- Example comparison studies of ML vs SPF:
  - Lagos–Ibadan Expressway — [Nigerian J. Tech 44(2)](https://doi.org/10.4314/njt.v44i2.5)
  - motorway tunnels, where ML "slightly improve[s] accuracy" — [summary](https://discovery.researcher.life/article/a-comparative-analysis-of-traffic-accident-frequency-models-for-motorway-tunnels-using-machine-learning/d847b43939153b26b4ac549bf9717a8e)
  - Virginia Tech thesis on ML for SPF development — [VTechWorks](https://vtechworks.lib.vt.edu/items/007dafc8-7bf4-49ad-9903-901f0a614ee6/full)
  - I did not read their numeric results.
- For LLM/NLP, accuracy and expert agreement can move in opposite directions. Use Cohen's kappa and expert validation. — [arXiv 2504.13068](https://arxiv.org/abs/2504.13068)
- Fine-tuned small transformers beat zero-shot LLMs on accuracy and cost for a narrow, well-labeled task. — [arXiv 2508.04399](https://arxiv.org/abs/2508.04399) [preprint]
- Even research that validates hard braking used state-of-practice NB regression with confounder controls rather than black-box ML. — [arXiv 2601.06327](https://arxiv.org/abs/2601.06327) [preprint]

### Inferences
- For CrashIQ, the defensible design is: keep SPF/EB, or at least an RTM-aware ranking, as the authoritative screening result. ML or surrogates can serve as secondary "flags," with SHAP-style explanations.
- AI-written findings should cite the computed tables, state small-number and RTM caveats, and never present associations as CMFs.
- Small corridor samples, the typical CrashIQ use case, are exactly where ML overfits and EB shrinkage matters most. This is an inference from the sources above; no single source states it for corridors.

### Gaps
- I found no 2022–2026 meta-analysis that quantifies ML vs NB/EB out-of-sample performance or hotspot-ranking consistency across many datasets.
- No FHWA or AASHTO position statement on using ML in place of SPFs was found.
- I did not read the full numeric results of the ML-vs-SPF comparison studies listed above.
