# Washington DC (dc): safety and crash-analysis methods (2026-11-07)

Written by Hermes. Numbers come only from the documents below, with page numbers. "Not found" = searched for, not in
any DC document found. Copies sit in `~/.hermes/cache/scratch/states/dc/manuals/` (not committed). The FHWA files
are blocked for scripted download (Akamai "Access Denied" to curl). For those, the extracted text was saved, not the
PDF. HSIP page numbers count the extractor's page breaks, so they may be off by one from the printed page.

## Bottom line

- **DC has no published statewide average crash rates by facility type**: no equivalent of Caltrans' TASAS base rates,
  and no published critical-rate table. Not found in the HSIP reports, the Traffic Safety Statistics reports, or the CTR
  guidance.
- **Screening** is a ranked list, not a rate-vs-average test: intersections ranked by frequency, rate (per MEV),
  severity cost, delta trend, and a **Composite Crash Index (CCI) = 0.25·rank(frequency) + 0.25·rank(rate) +
  0.50·rank(severity)**. Since 2024–25, a Traffic Safety Input (TSI) 2.0 score is used too. It covers only 3 years of
  crashes, with 30% crash patterns, 20% High Injury Network, 20% high-risk populations, 20% VRU generators and
  10% roadway.
- **Crash costs:** DC uses "published crash cost rates by the Federal Highway Administration" (TSS 2015-2017 p. 5) and
  prints no values. DC-specific costs were not found. FHWA's current national values are listed below as the
  referenced source.
- **HSM:** DDOT "has formalized the use of the HSM predictive method within the HSIP Intersection program" (SPFs +
  CMFs). No DC calibration factors are published (not found).
- **Development studies (CTR):** DDOT **removed** the three-year crash analysis from CTR/TIA in 2022. Applicants do a
  qualitative, site-visit safety review instead.

## Documents

### 1. District of Columbia HSIP 2025 Annual Report (DDOT, submitted to FHWA)
URL: https://highways.dot.gov/sites/fhwa.dot.gov/files/2026-09/DISTRICT%20OF%20COLUMBIA_HSIP%20REPORT_2025_508_0.pdf
(posted 2026-09; text saved as `hsip_2025.txt`). The 2024 report (https://highways.dot.gov/sites/fhwa.dot.gov/files/2025-03/HSIP_Report_DISTRICT%20OF%20COLUMBIA_2024_508.pdf) was saved too.

- p. 4: SHSP 2021-2025 in force; "The next SHSP that covers 2026-2030 is in development." Goals: fatalities from 36
  (2020) to 11 by 2030; fatality rate goal "0.26 fatalities per 100 VMT by 2030, compared to 1.14 in 2020" (as
  written; per 100 million VMT is meant).
- p. 4–5: 2024 targets (5-year rolling averages): fatalities 26; fatalities per 100M VMT 0.70; serious injuries 316;
  serious injuries per 100M VMT 8.46; non-motorized fatalities + serious injuries 136.6. The crash data system is
  named TARAS.
- p. 6: network screening "considers the entire network, including all functional classifications of roads". Locations
  are ranked by "crash frequency, crash rate, crash severity, and crash trends (i.e., change over time)". The "injury
  composite crash index (CCI), which involves a weighted combination of injury crash rate, severity, and frequency"
  has a ped/bike CCI version.
- p. 10 (Intersection program, methodology dated 10/1/2020): identification by crash frequency, crash rate, crash
  severity, probability of specific crash types. Prioritisation weights: rank of injury crash frequency 25, rank of
  injury crash rate 25, rank of injury crash severity 50.
- p. 11 (Left Turn Crash program, methodology dated 1/31/2019): "Ranking based on net benefit: 50, Cost Effectiveness: 50".
- p. 16 (signs program): identification by crash frequency, crash rate and **critical rate**. The critical-rate formula
  and threshold are not given.
- p. 18: HSM predictive method in the HSIP Intersection program: "Safety performance functions (SPFs) are used to
  calculate the predicted number of crashes based on intersection type and AADT. Crash modification factors (CMFs) are
  then applied". It replaced "the prior use of benefit-cost methodology". Countermeasures are picked with "HSM, CMF
  Clearinghouse, SafetyAnalyst, usRAP", engineering studies and RSAs.
- p. 18: TSI 2.0 weights (see bottom line); crash patterns use "the past three years".
- Years of data required: 3 years (TSI 2.0, CCI reports). A 5-year rule was not found.

### 2. Traffic Safety Statistics Report for the District of Columbia (2015-2017), DRAFT
Howard University Transportation Research Center for DDOT, 112 pp. URL:
https://ddot.dc.gov/sites/default/files/dc/sites/ddot/publication/attachments/Crash%20Statistics%20Report%202015-2017_final%20draft.pdf
(`tss_2015_2017.pdf`). This is the newest edition found. The HSIP 2025 report still cites "internal review of annual
Crash Statistics report" (p. 10), so newer editions may exist internally. The 2014-2016 edition was saved too
(`tss_2014_2016.pdf`).

- p. 4, Eq. 1, intersection crash rate: **R = A × 1,000,000 / (V × 365)**, crashes per million entering vehicles
  (MEV), where A = average crashes per year and V = entering AADT. Locations without volumes are skipped.
- p. 5, severity cost method: costs "computed based on published crash cost rates by the Federal Highway
  Administration". **Values and their year are not printed.** It uses crash outcome (fatal / injury / PDO), not the
  person injury code, "to avoid inaccuracies".
- p. 5, Eq. 2: **CCI = 0.25·RF + 0.25·RR + 0.50·RS** (RF, RR, RS = ranks by frequency, rate, severity); the lowest
  CCI ranks highest. Eq. 3 is an alternative: 0.20 / 0.20 / 0.60.
- p. 6, Eq. 4, delta change: the slope of a linear regression of crashes on year, (nΣxy − ΣxΣy)/(nΣx² − (Σx)²).
- p. 7, Table 3.1 (2015 / 2016 / 2017): total crashes 24,265 / 26,447 / 26,459; fatal crashes 26 / 27 / 31; injury
  crashes 6,215 / 6,305 / 6,626; PDO 18,024 / 20,115 / 19,802; fatalities per 100M VMT 0.70 / 0.76 / 0.89\*.
  "Disabling injuries" 326 / 335 / 325.
- p. 62, Table 5.3: top-20 intersections by rate, e.g. Firth Sterling Ave & Howard Rd SE, 9.132 per MEV in 2017 (rank 1);
  14th St & U St NW 6.967 (rank 2). These are site rates, not averages.
- p. 73, Table 6.1: DC fatalities per 100M VMT 2009–2016: 0.91, 0.69, 0.89, 0.52, 0.79, 0.70, 0.70, 0.76. DC VMT
  ≈ 3.6 billion per year (3,607–3,720 million).
- p. 74, Table 6.2: DC injuries per 100M VMT 2009–2016: 181.01, 195.57, 202.96, 200.28, 205.56, 217.09, 224.22,
  231.23\*. US: 74–80.
- Facility-type average rates, critical rate, segment rate formula (per MVMT): **not found**.

### 3. High Crash Intersection Site Visits (DDOT, 2016-01-07)
URL: https://ddot.dc.gov/sites/default/files/dc/sites/ddot/page_content/attachments/High%20Crash%20Intersection%20Report_010716_FINAL%20(3).pdf
(`high_crash_int_2016.pdf`, 43 pp.). Field reviews of the ranked intersections. It contains no rate tables or costs
(searched; only a project budget line).

### 4. Guidance for Comprehensive Transportation Review (CTR), v2.0, January 2022 (DDOT)
URL: https://ddot.dc.gov/sites/default/files/dc/sites/ddot/CTR%20Guidance%20-%20January%202022%20Version%202.0.pdf
(`ctr_2022.pdf`, 174 pp.). This is the required study form for development traffic studies.

- p. 12: "The three-year vehicle crash analysis was removed as a CTR/TIA requirement. Instead, individual developments
  are expected to focus on pedestrian safety … provide a qualitative review of safety conditions based on field
  observations".
- p. 66, §3.5 Safety Analysis: a qualitative safety analysis for all modes. The study must say whether any study
  intersection is a DDOT high crash location, review any DDOT Vision Zero or HSIP safety studies, and check sight
  triangles per DEM 30.5.1 and DEM 32.12 and the AASHTO Green Book.

### 5. FHWA Crash Costs for Highway Safety Analysis, fact sheet (October 2025), the cost source DC cites
URL: https://highways.dot.gov/sites/fhwa.dot.gov/files/2025-10/CrashCostFactSheet_508_OCT2025.pdf (`fhwa_crashcost_2025.txt`).
Table 1, comprehensive crash unit costs, **2024 dollars**: K $15,988,000; A $1,705,100; B $384,000; C $204,600;
O $18,100. Step 5: states may scale these by the state-to-national per-capita-income ratio. DC's ratio isn't given and
DC hasn't published one (not found). This is a national source, not a DC adoption.

### Searched, not found
DC statewide average crash rates by facility type; critical-rate formula and confidence level; DC crash costs; DC SPF
calibration factors; DC CMF list; a DDOT safety-study manual for consultants. The DDOT Design and Engineering Manual
(https://ddot.dc.gov/page/standards-and-guidelines → DDOT wiki "Standards and Manuals") is a design manual; its safety
chapter wasn't read. The current SHSP (2021-2025) PDF wasn't located on FHWA's SHSP page
(https://highways.dot.gov/safety/hsip/shsp/district-columbia).

## How DC differs from California

| Topic | California (CrashIQ today) | DC |
|---|---|---|
| Average rates to compare against | Caltrans TASAS base rates by facility / rate group | None published. Compare within DC (rank lists) |
| Intersection rate | per MEV | per MEV, same formula (TSS p. 4) |
| Segment rate | per MVMT (LRSM) | Not published (statewide only, per 100M VMT, TSS p. 73–74) |
| Screening | Rate and frequency, LRSM; HSIP B/C with LRSM CRFs | CCI rank composite 25/25/50, TSI 2.0 score, HSM predictive (SPF+CMF) for intersections |
| Crash costs | Caltrans LRSM Appendix D | FHWA national (values not printed by DC); FHWA 2024 $ above |
| Severity | Full KABCO from CCRS | Public data merges B and C ("minor"); K and A exact |
| Years | LRSM: at least 5 years network-wide | 3 years (TSI 2.0, CCI reports) |
| Development studies | Crash history common in TIS | No crash analysis in CTR since 2022; qualitative only |
