# Florida: safety-analysis manuals, rates and crash costs (checked 2026-11-07)

PDFs downloaded to `~/.hermes/cache/scratch/states/fl/manuals/` (not committed; URLs in `urls.json` there). Page numbers
are the printed page numbers unless "PDF p." is written. California comparisons use what CrashIQ already ships:
Caltrans LRSM v1.8 (May 2026) Appendix D crash costs (`data/reference/crash_costs_ca.csv`), the HSM Ch. 4 critical-rate
method in `backend/crashiq/profile.py`, and TASAS base rates.

## 1. FDOT Design Manual (FDM) 2026, Chapter 122 "Design Exceptions and Design Variations"
- URL: https://fdotwww.blob.core.windows.net/sitefinity/docs/default-source/roadway/fdm/2026/2026fdm122varexcept.pdf?sfvrsn=c229234b_4 (Topic #625-000-002, dated January 1, 2026).
- §122.6 Crash Analysis (p. 26): B/C over the life of the exception, **discount rate 4%**. Historical (HCM) and predictive (RSAP, HSM) methods both allowed. The Historical Crash Method uses crashes from **Signal Four Analytics**, "all severity types (KABCO) and all location verified statuses (i.e. verified as well as preliminary)" (p. 27).
- **Table 122.6.1, FDOT Average Crash Costs by Facility Type** (p. 27), cost per crash, State Highway System, 2015–2019 crashes:

  | Facility | Divided urban | Divided suburban | Divided rural | Undivided urban | Undivided suburban | Undivided rural |
  |---|---|---|---|---|---|---|
  | 2–3 lanes | $107,732 | $201,527 | $355,183 | $124,618 | $267,397 | $523,727 |
  | 4–5 lanes | $123,406 | $225,315 | $473,637 | $112,896 | $190,276 | n/a |
  | 6+ lanes | $123,598 | $166,258 | $451,492 | $41,650 | n/a | n/a |
  | Interstate | $153,130 | n/a | $327,385 | n/a | n/a | n/a |
  | Turnpike | $139,221 | n/a | $304,397 | n/a | n/a | n/a |

  Average cost per crash $159,093. Method: FHWA T7570.2 (1994), VSL raised to $9.7 million (note 2).
- **Table 122.6.2, FDOT KABCO Crash Costs** (comprehensive, p. 28): **K $10,890,000; A $888,030; B $180,180; C $103,950; O $7,700.** Source note: CAR system, analysis years 2015–2019, published by the FDOT State Safety Office on 2/23/2022. The dollar year isn't stated; the 2026 MUTS bulletin says these are the costs "consistent with the 2026 FDM".
- **Table 122.6.3, HSM Calibration Factors for Florida** (p. 29): roads R2U 1.00, R4D 0.68, U2U 1.02, U3T (U32LT) 1.04, U4U 0.73, U4D 1.63, U5T (U52LT) 0.70; intersections RTL3ST 1.27, RTL4ST 0.74, RTL4SG 0.92, RML3ST 2.20, RML4ST 1.64, RML4SG 0.45, USA3ST 1.14, USA4ST 1.87, USA3SG without ped. CMFs 2.58, USA3SG with ped. CMFs 2.50, USA4SG 2.27.
- **Table 122.6.4, HSM Crash Distribution for Florida** (K/A/B/C/O shares, p. 30), e.g. R2U 0.028/0.094/0.181/0.187/0.509; U4D 0.008/0.046/0.142/0.234/0.571; urban freeways 0.006/0.035/0.113/0.206/0.641; all roadways and ramps 0.007/0.041/0.124/0.217/0.611. Source: CAR 2015–2019.

## 2. Highway Safety Improvement Program Guidelines (FDOT State Safety Office), August 2021
- URL: https://fdotwww.blob.core.windows.net/sitefinity/docs/default-source/safety/6-resources/florida-hsip-manual-v2021-f-(2021-08-12).pdf?sfvrsn=960bbf43_2 (the copy linked from FDOT's Publications page; an August 2020 edition is also online).
- Data (p. 10): "strongly recommends using crash data with verified geolocations ... Verified geolocations shall come from FDOT systems, staff, or consultants", and **"at least three to five years of crash data under consistent site conditions"**. PDO crashes "are not a major consideration in the HSIP".
- Projects: estimated **BCR ≥ 1.0**, typically low cost (under $1,000,000), concept to construction under 3 years (p. 4).
- **Table 2, Florida crash costs by severity** (p. 20): K $10,560,000; A $599,040; B $162,240; C $100,800; O $7,600; weighted average $151,677. These are older than FDM 2026 Table 122.6.2; the HSIP text itself says the FDM is the source of the current values. Use FDM.
- B/C procedure (p. 19–20): five years of observed crashes, CMF applied, present value. When severity of past or future crashes isn't reliable, the weighted average cost is used.
- **Network screening** (§4.1.1, p. 27): the SSO screens statewide every year and gives Districts the results. "When HSM methods are applicable, the SSO recommends using the **peak searching method based on expected fatal and injury crash frequency**." SAFE (STRIDES 2 Zero) for signalized intersections on the SHS. Otherwise "simple queries or GIS analysis based on observed fatal and injury crash frequency". **Up to five consecutive years** of data.
- CMF selection (§2.5, §4.3.2 p. 33): FHWA CMF Clearinghouse and the HSM; conservative CMFs (the upper 95% confidence limit) encouraged (p. 21).

## 3. Safety Crash Data Guidance ("Crash Data Process", v18, April 2023)
- URL: https://fdotwww.blob.core.windows.net/sitefinity/docs/default-source/safety/11a-safetyengineering/crash-data/crash-data-process_v18.pdf?sfvrsn=311253ee_1 (pages dated 04.10.2023 / 04.17.2023; the "crash-data-guidance_apr2023" link FDOT's Safety Analysis Methods page gives returns 404).
- Signal Four is "the single source of crash data for completing any FDOT safety analyses" (PDF p. 4).
- Years (PDF p. 4): pull **the last five full calendar years**; at least 3 years if conditions changed; 5 years for the HSM Part C predictive method.
- KABCO crosswalk (PDF p. 5): K Fatal = FTCR "Fatal"; A Serious = "Incapacitating"; B Moderate = "Non-incapacitating"; C Minor = "Possible"; O = "None". The importers use exactly this map.
- **Five approved analysis methods, in FDOT's order of preference** (PDF p. 17): 1) excess expected average crash frequency with EB; 2) predicted average crash frequency with SPFs; 3) relative severity (average crash cost vs the reference population, with FDM Tables 122.6.1/122.6.2); 4) **critical crash rate**; 5) qualitative analysis.

## 4. FDOT crash-rate method (CAR / State Safety Office) – Safety FAQ and Crash Data Academy CDA-9
- FAQ: https://www.fdot.gov/docs/default-source/safety/11a-safetyengineering/crash-data/frequently-asked-questions.pdf (undated; cites 2008 data). CDA-9 "High Crash Location Analysis for the SHS", 2017-03-02: https://www.fdot.gov/docs/default-source/safety/11a-safetyengineering/crash-data-academy/FDOT_CDA-9_HighCrashLocAnalysisforSHS_2017-03-02.pdf
- Exposure (FAQ PDF p. 3): **MVM = ADT × miles × days / 1,000,000** for segments; **MEV = ADT × days / 1,000,000** for intersections.
- Average rate: crashes ÷ exposure over all sites of the same rate category **within the District** (FAQ PDF p. 3); CDA-9 (PDF p. 24) says county, district and statewide averages are computed for each roadway and intersection type.
- FDOT solves the critical-rate equation for K instead of fixing K: **CONLV = (ACTUAL − AVERAGE + 1/(2·MVM)) / √(AVERAGE/MVM)** (MEV for intersections), then reports a confidence level from a lookup (K < 0.6740 → 50%; 1.2816–1.6449 → 90%; 1.6449–1.9600 → 95%; ≥ 3.7190 → 99.99%) (FAQ PDF p. 3–4).
- Segments use a sliding 0.3-mile window (CDA-9 PDF p. 17).
- **Statewide average crash rate tables: not found as a current public table.** FDOT computes them inside CAR/S4 per district and rate category. A 2016 FDOT design-exception workshop appendix with "Florida SHS Average Crash Rates by Facility" exists (https://www.fdot.gov/docs/default-source/roadway/QA/Data/2016-DesignExceptionsWorkshop-Appendix.pdf), but the server returned a truncated file (11.2 MB, no PDF trailer, twice), so its numbers weren't read. UF GeoPlan's FGDL "Florida 5-year crash rates with district and state averages" (2014, 2018) is a lead not checked.

## 5. Manual on Uniform Traffic Studies (MUTS), January 2027 (Topic No. 750-020-007)
- URL: https://fdotwww.blob.core.windows.net/sitefinity/docs/default-source/traffic/trafficservices/studies/muts/muts-2027/manual-on-uniform-traffic-studies-(muts)-2027_clean.pdf?sfvrsn=4f1d4f70_2 . Released by TEO Bulletin 26-03 (October 30, 2026), effective on projects beginning design on or after January 1, 2027.
- Chapter 5 "Data Collection for Transportation Safety Studies": HSM predictive method N_predicted = N_spf × (CMF1 × … × CMFn) × C (p. 5-2). Historical crash data from S4 (access needs FDOT permission; p. 5-17). **"Historical crash data of a minimum of 5 years shall be used"** for EB (§5.4.3.3, p. 5-19). Signal studies: "a minimum of five years of crash data should be reviewed" (Ch. 2, PDF p. 21).
- **Required study forms** (FDOT Forms Library): 750-020-04 Condition Diagram; 750-020-05i Collision Diagram for Segments; 750-020-05j Collision Diagram for Intersections; **750-020-05k Collision Summary**; 750-020-05a–h, l, n, o HSM data-collection sheets per facility type; 750-020-06a–c freeway segment/ramp data; 750-020-01 Signal Warrant Summary (Figures 5-1 to 5-17, pp. 5-20 to 5-36).
- Chapter 14 lighting justification repeats the FDM Table 122.6.2 KABCO costs (p. 14-10).
- **Intersection Control Evaluation retired:** Bulletin 26-03 (p. 1, "Implementation"): "Effective November 2, 2026, FDOT is discontinuing the ICE Program and retiring the ICE Manual, website, forms, procedures, tools ... This applies to Chapter 2 and 5 of the MUTS." So an FDOT ICE study is no longer a deliverable on new projects.

## 6. FDOT Highway Safety Manual User Guide, 2015
- URL: https://fdotwww.blob.core.windows.net/sitefinity/docs/default-source/safety/safety/11a-safetyengineering/transsafeng/strategicplandocs/2015fdothsmuserguide.pdf?sfvrsn=217d6331_0
- §2.6 lists the **2012** calibration factors (e.g. U4D 1.63, U3SG 1.56, R23ST 1.30). Superseded by FDM 2026 Table 122.6.3 (which keeps U4D 1.63 but differs elsewhere, e.g. urban 3-leg signalized 2.58/2.50).

## 7. Crash Reduction Factors (FDOT, as of 02/14/2014)
- URL: https://fdotwww.blob.core.windows.net/sitefinity/docs/default-source/roadway/qa/tools/crf.pdf?sfvrsn=ffd98504_2 — a 3-page table of Florida before/after CRFs by improvement type and crash type (e.g. "New signal at channelized intersection": total 12, fatal 15, injury 20 percent). Note on the sheet: CRFs from fewer than 5 projects are not recommended for B/C. Current FDOT guidance points to the CMF Clearinghouse and HSM instead (HSIP §4.3.2). The one-page "SPFs / CMFs / CRFs" sheets on the Safety Analysis Methods page are definitions only.

## 8. Other
- FDOT Systemic Safety Analysis, Signalized Intersections on the SHS, Technical Memorandum, May 2024 (https://fdotwww.blob.core.windows.net/sitefinity/docs/default-source/traffic/trafficservices/strides2zero/systemic-safety-analysis---technical-memorandum.pdf?sfvrsn=60fb6fa_1), Table A.1: statewide crashes 2018 741,262; 2019 746,153; 2020 589,856; 2021 703,324; 2022 706,267 (5-year average 697,372; 3,170 fatal crashes a year). That matches the FLHSMV open file's ~700k crashes a year (2023–2025).
- Not downloaded (404 on FDOT's current links): Safety Analysis Guidebook for PD&E Studies (2019) and the FDOT ICE Manual (now retired anyway). FHWA's 2024 Florida HSIP report download failed.

## What differs from California (what CrashIQ does today)
1. **Crash costs:** Florida prices each KABCO level separately (K $10.89M, A $888k, B $180k, C $104k, O $7.7k; FDM 2026 Table 122.6.2). Caltrans LRSM prices K and A together by location type (KA $2.379M signalized, $3.784M non-signalized, $3.276M roadway; B $213k; C $121k; O $20k). A Florida fatal crash costs 4.6× a California signalized KA crash; Florida PDO is 39% of California's. FDM also gives an average cost per crash by facility type (Table 122.6.1) for relative-severity work, which California doesn't have.
2. **Crash rate method:** same exposure units as CrashIQ (MVM for segments, MEV for intersections), but FDOT reports a **confidence level** (solve for K, look up 50%…99.99%) against the **district** average of the same rate category, not a fixed-K critical rate against a reference group. CrashIQ's `critical_rates` (K = 1.645) would match FDOT's "95%" threshold, but the reference population differs (district, not the user's corridor set). Segment screening uses 0.3-mile sliding windows.
3. **No public base-rate table** like TASAS: FDOT's averages live in CAR/S4 (login). A Florida pack can't ship "expected rates" without a user's S4 export or an FDOT table.
4. **Method order:** FDOT's preferred method is EB excess expected crashes with Florida-calibrated SPFs (FDM Table 122.6.3), then SPF prediction, relative severity, critical rate, qualitative. California's LRSM is BCR-centred, with historical crash counts.
5. **Data rules:** S4 is the required source, with verified as well as preliminary locations (FDM 122.6.1); 5 full calendar years (MUTS §5.4.3.3, HSIP, Crash Data Guidance). Severity labels: Florida "Incapacitating / Non-incapacitating / Possible" = A / B / C.
6. **Forms:** Florida requires its own collision diagram and summary forms (750-020-05i/j/k) and a condition diagram (750-020-04). CrashIQ's diagrams would need these layouts for FDOT submittals.
7. **ICE retired** (Nov 2, 2026), so no Florida ICE deliverable; California's ICE (Caltrans TOPD 13-02) still applies there.
8. **Discount rate** 4% for B/C (FDM 122.6).
