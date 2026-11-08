# Virginia: safety and crash-analysis methods CrashIQ must follow (2026-11-07)

Written by Hermes. All PDFs were downloaded 2026-11-07 to `~/.hermes/cache/scratch/states/va/manuals/` (not committed).
Page numbers: "pdf p" is the PDF page; the printed page is given where it differs. Numbers are copied from the
manuals. "Not found" means I looked and did not find it in an official VDOT document.

## 1. Manuals found

| # | Title | URL | Edition / date |
|---|---|---|---|
| M1 | VDOT Traffic Crash Costs 2026 (memo, S. Read, State Highway Safety Engineer) | https://www.vdot.virginia.gov/media/vdotvirginiagov/about/strategic-highway-safety-plan/VDOT-Crash-Costs-Memo-2026_acc10062026_RM.pdf | dated 09/01/2026 |
| M2 | Virginia Highway Safety Improvement Program (VHSIP) — HSIP Implementation Guidelines (Reference Guide) | https://www.vdot.virginia.gov/media/vdotvirginiagov/about/strategic-highway-safety-plan/VHSIP-Reference-Guide_2025_acc08182025_RM.pdf | 2025 (file accessioned 2025-08-18) |
| M3 | Traffic Operations and Safety Analysis Manual (TOSAM) v2.0 | https://www.vdot.virginia.gov/media/vdotvirginiagov/doing-business/technical-guidance-and-support/technical-guidance-documents/traffic-operations/traffic-operations-and-safety-analysis-manual-tosam.pdf | release Feb 2020 (page lists "published April 5, 2023") |
| M4 | Virginia State Preferred CMF List | https://www.vdot.virginia.gov/media/vdotvirginiagov/doing-business/technical-guidance-and-support/traffic-operations/vhsip/VDOT-State-Preferred-CMF-List-2026_acc10152026_RM.pdf | 2026 (accessioned 2026-10-15) |
| M5 | VTRC 26-R34, Intersection Safety Performance Function Calibration for Project Planning and Design (J. Appiah) | https://vtrc.virginia.gov/media/vtrc/vtrc-pdf/vtrc-pdf/26-R34.pdf | March 2026 |
| M6 | VHSIP Spot Safety Application — Example (Excel B/C form) | https://www.vdot.virginia.gov/media/vdotvirginiagov/doing-business/technical-guidance-and-support/traffic-operations/vhsip/VHSIP-Spot-Safety-Application---Example_acc10012025_RM.xlsx | FY 2025 form (accessioned 2025-10-01) |
| M7 | VHSIP Systemic Safety Application (Excel) | https://www.vdot.virginia.gov/media/vdotvirginiagov/doing-business/technical-guidance-and-support/traffic-operations/vhsip/VHSIP-Systemic-Safety-Application_acc10012025_RM.xlsx | accessioned 2025-10-01 |
| M8 | VTRC 06-R30, Development and Evaluation of Virginia's Highway Safety Corridor Program (Fontaine, Read) | https://vtrc.virginia.gov/media/vtrc/vtrc-pdf/vtrc-pdf/06-r30.pdf | April 2006 |
| M9 | IIM-TOD-397, Virginia iCAP (intersection control) policy and guidance | https://vdot.virginia.gov/media/vdotvirginiagov/about/vdots-transportation-system/highways/innovative-intersections/iim-tod-397-icap-policy-and-guidance.pdf | signed 2023-06-16 |

Also read (secondary, not manuals): VDOT study reports that quote statewide rates (§4), and FHWA's noteworthy-practice
page on Virginia SPFs (https://highways.dot.gov/safety/learn-safety/noteworthy-practices/virginia-develops-and-uses-state-specific-performance).

## 2. Crash costs (M1)

Table 1, "Virginia KABCO Crash Unit Costs (2026)", M1 pdf p1, **2026 dollars**, per crash at its KABCO level:

| Severity | Economic | QALY | **Comprehensive** |
|---|---|---|---|
| K | $2,418,564 | $14,590,979 | **$17,009,543** |
| A | $183,910 | $814,866 | **$998,777** |
| B | $81,434 | $248,556 | **$329,990** |
| C | $57,602 | $133,171 | **$190,773** |
| O | $17,344 | $0 | **$17,344** |

- "The Comprehensive Crash Costs in Table 1 should be used by practitioners in Virginia when calculating the benefit-cost
  ratio for specific safety treatments" (p1).
- Table 2, weighted costs (p1): K/A $3,058,109; K/A/B $922,935; K/A/B/C $741,842; K/A/B/C/O $261,212; A/B/C $392,198;
  B/C $288,821. Weights are the 2021–2025 Virginia crash counts in Table 7 (p4): K 4,346, A 29,443, B 121,673,
  C 51,088, O 407,081.
- Method (p2–p3): FHWA *Updated Crash Costs for Highway Safety Analysis* tool, adjusted to Virginia with Virginia
  2021–2025 crash and person-injury counts (Table 4) and 2026 CPI 331.180, MUWE 1246.00, PCI $81,123 (VA) / $77,816 (US)
  (Table 6). National 2024-dollar costs for comparison (Table 3, p2): K $15,988,000, A $1,705,100, B $384,000,
  C $204,600, O $18,100.
- Table 8 (p4–p5): costs by crash type × severity (e.g. Head on K $18,994,572, A $1,270,992; Angle K $17,494,430,
  A $1,110,571). "Should not be summed across categories" (p4).
- **One cost per severity for every location type** — no intersection/roadway split.

The FY2025 spot application form (M6, sheet "Delivery_Funding") still carries older costs in its worked example (fatal
injury $16,842,855.59, citing "VDOT 2013 Highway Safety Improvement Program Guidelines" and FHWA-HRT-05-051); the 2026
memo supersedes them for B/C ("should be used by practitioners", M1 p1).

## 3. Benefit/cost and years of data (M2, M6)

- "benefits are determined using the latest three to five years of available crash data related to the proposed
  improvement" (M2 pdf p11, §2.2). Spot program: "Analyzing crashes for a three or five-year period … Longer five-year
  periods may be used for … roadway departures or vulnerable road user crashes" (M2 pdf p19, §3.1).
- Application form (M6, sheet "Crash History"): **Discount rate 0.03**, **number of years in crash history 5**.
  Present value of benefits over the countermeasure's service life (sheet "Delivery_Funding").
- Scoring (M2 Appendix C, pdf p44–p45): "Is the location included on the Potential for Safety Improvement (PSI)
  segment or …" 25 points if on PSI else 10; B/C ratio: spot form "If B/C >= 1, then 40, else 0"; systemic form
  "If B/C ≥ 10, then 40 points; if B/C ≥ 5 and < 10, then 20 points; if B/C ≥ 1 and < 5, …" (pdf p45).
- HRRR projects need "a benefit-cost ratio greater than 1.0" (M2 pdf p30, §6.2).
- Engineering studies with detailed crash analysis must be signed and sealed (TE Memo 362.1, cited at M2 pdf p20, fn 3).
- TOSAM (M3 pdf p76, printed p54): for EB analyses "At least two years of crash data (five years, preferred)"; don't use
  history if the road had major geometric or control changes in the past two years.

## 4. Statewide average crash rates (the TASAS base-rate equivalent)

- **Not found as a published VDOT table or manual.** VDOT's averages live inside its crash tools ("VDOT's Crash Summary
  Book", in the Power BI crash tool; earlier the Tableau T-CAT), which this session did not open (the public Power BI tool
  is interactive, not a download).
- Secondary quotes in VDOT-hosted study reports (not manuals, for orientation only):
  - Route 5 Henrico study, Table 7 (pdf p8): statewide crash rate 143.33 per 100 million vehicle miles, "Based on 2019
    Statewide Crash Rates for Rural Minor Arterial".
    https://www.vdot.virginia.gov/media/vdotvirginiagov/projects/richmond/henrico---route-5-safety-and-operations-study/Final-Route-5-Operational-Safety-Study-in-Henrico-acc.pdf
  - Coalfields Expressway study (Dec 2025, pdf p25): "2017-2024 statewide average for rural primary roadways is 111.5
    crashes per 100M VMT"; KABC 57.6; fatal 1.8 per 100 MVMT (pdf p24).
    https://www.vdot.virginia.gov/media/vdotvirginiagov/projects/bristol/route-121-pre-engineering-study-buchanan-county/CFX-Existing-Conditions---DEC-2025_acc12162025_PM.pdf
  - Rte 501 Campbell study (pdf p14): "VDOT's Crash Summary Book was used to compare the corridor with overall district
    and statewide crash rates between 2020 and 2024."
- **Exposure units:** segments per **100 million VMT** in every Virginia source read (M8 p42; the studies above).
  Intersection rates per million entering vehicles: **not found** in a VDOT manual.

## 5. Screening method

- **Current: Potential for Safety Improvement (PSI)**, from Virginia-specific SPFs with the EB method. TOSAM glossary
  (M3 pdf p19): "PSI: Factor that indicates a higher historical crash rate than the rate predicted by the HSM
  methodology… A positive PSI value indicates a location in need of safety improvement." FHWA: "After performing network
  screening, the VDOT central office identifies the top 100 sections and top 100 miles of segments with the largest
  Potential for Safety Improvement (PSI)" (FHWA noteworthy-practice page above). PSI lists feed the VHSIP score (M2 p44).
- **Critical rate (older, still in the HRRR definition):** M8 pdf p42 (printed 38): Rc = Ra + k·√(Ra/M) + 1/(2M), Ra =
  average rate for similar facilities (per 100 million VMT), M = VMT in 100 million, k = 2.576 (99%) in that study;
  "If the ratio of the crash rate to the critical rate is greater than 1.0, the segment has a potentially significant
  crash problem." Four facility types: 2-lane undivided, >2-lane undivided, divided … (M8 p42). The 2025 VHSIP guide's
  HRRR definition instead uses "the Critical Cash [sic] Rate (one standard deviation above the state average) for that
  classification" (M2 pdf p29, §6).
- 5-step study process for spot projects: network screening → diagnosis → countermeasure selection → economic appraisal
  → prioritization (M2 pdf p20, §3.1).

## 6. Severity weighting

- B/C uses comprehensive cost per KABCO level (M1 Table 1). EPDO weights: **not found** in the current manuals (FHWA's
  2018 Virginia HSIP report mentions EPDO for district funding targets only).
- Severity scale: KABCO (M1; the crash data's CRASH_SEVERITY field is K/A/B/C/O).

## 7. SPFs and calibration factors (M5, M3)

- M5 Table 11, "Recommended Calibration Factors for Total Crashes" (pdf p33, printed 27), HSM 2nd-edition draft
  intersection SPFs, 1,326 Virginia intersections:
  - Rural two-lane: 3SG 0.79, 3ST 1.20, 4SG 0.94, 4ST 0.91.
  - Rural multilane: 3SG 1.17, 3ST 1.39, 4SG 0.98, 4ST 1.88 (barely missed acceptance, CV 0.16).
  - Urban/suburban arterials, ≤5 lanes: 3SG 1.30, 3SG-HS 0.98, 3ST 1.50, 3ST-HS 0.88, 4SG 1.59, 4SG-HS 0.76, 4ST 1.47,
    4ST-HS 0.95; 5SG not enough sample.
  - One road ≥6 lanes: 3SG 0.98, 3ST 1.05, 4SG 0.56, 4ST 1.41. One-way: 4SG 1.55. 4-leg all-way stop: not enough sample.
  - Dispersion parameters are in the same table. Fatal-and-injury calibration *functions* are in Table 12 (not copied).
- Segment and freeway SPFs: VTRC 14-R14 (multilane and freeway segments) and 11-CR1 (intersections) exist; not
  downloaded or read this session.
- TOSAM (M3 pdf p77, printed 55): predictive models "should be calibrated for Virginia conditions whenever possible"
  and "shall only be used to compare predicted or expected crashes between analysis alternatives"; Virginia severity
  proportion tables "not yet produced" (as of TOSAM v2.0).

## 8. CMF guidance (M4, M3)

- Use the Virginia State Preferred CMF List (M4) first. The list gives CMF, crash type, severity, service life,
  functional class, site description and reference (M4 pdf p2–p3); "The FHWA CMF Clearinghouse served as the primary
  source" (p2).
- If not on the list: CMF Clearinghouse star rating above three, or HSM Part D standard error < 0.1; "The VDOT project
  manager shall approve" the CMF (M3 pdf p77, printed 55). The application form asks "Does your CMF Exist in the
  Virginia State Preferred CMF List? (yes/no)" (M6 sheet "Improvements").

## 9. Required forms

- VHSIP Spot Safety Application (M6) and Systemic Safety Application (M7), both Excel, submitted "through the SMART
  Portal" (M2). VRU and rail-crossing proposals have their own rubrics (M2 Appendix C).
- Intersection control: iCAP / VJuST per IIM-TOD-397 (M9).

## 10. Differences from California (what CrashIQ must switch per state)

1. **Crash costs:** Virginia gives one comprehensive cost per KABCO level (K $17,009,543 … O $17,344, 2026 $, M1);
   Caltrans LRSM v1.8 prices K and A *together* by location type (KA signalized $2,379,000, non-signalized $3,784,000,
   roadway $3,276,000; B $213,000; C $121,000; O $20,000 — `data/reference/crash_costs_ca.csv`). Virginia's K is
   4.5–7.1× California's KA price, so cost rankings are not comparable across states.
2. **Statewide rates:** California has a published base-rate table (TASAS / "2024 Basic Average Crash Rate Table", rate
   groups + ADT factor, `backend/crashiq/rate_groups.py`). Virginia's averages are only in its Power BI crash tool
   (Crash Summary Book), by functional class / system, per 100M VMT; no rate-group table found.
3. **Screening:** Virginia ranks by PSI from its own SPFs (EB, top-100 lists); CrashIQ's California mode compares
   locations with TASAS base rates (California's own screening rules were not re-read this session). CrashIQ's critical-rate column (HSM Ch. 4, 95%) is close
   to Virginia's old method (M8 used 99%, k = 2.576).
4. **B/C:** Virginia form: 3% discount rate, 5 years of crash history, B/C ≥ 1 to score (spot), tiers at 1/5/10
   (systemic). California's HSIP BCR rules differ (LRSM Appendix D; not re-read this session).
5. **Calibration:** Virginia publishes intersection calibration factors (M5); California's LRSM does not use HSM
   calibration for HSIP.
6. **Data years:** Virginia: 3–5 years (M2), TOSAM: ≥2, 5 preferred. California LRSM: not re-checked here.
7. **Legal:** Virginia crash data and studies carry 23 USC 407 and DPPA terms (M2 pdf p19; data portal), and detailed
   crash-analysis studies must be PE-sealed (TE-362.1).

## Not checked

VTRC segment/freeway SPF coefficients (14-R14, 11-CR1); the Power BI Crash Summary Book's rate tables; M5 Table 12
(fatal+injury calibration functions); M4's individual CMF values; the 2023 FHWA HSIP report (download blocked).
