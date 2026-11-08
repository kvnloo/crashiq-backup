# New York: official crash-analysis methods (Hermes, 2026-11-07)

All files downloaded 2026-11-07 to `~/.hermes/cache/scratch/states/ny/manuals/` (not committed). Page numbers are the
**printed** page, with the PDF page in brackets. Numbers are copied from the documents; nothing is computed here.

## 1. Manuals found

| # | Title | URL | Edition / date |
|---|---|---|---|
| 1 | Highway Safety Improvement Program Procedures and Techniques ("Red Book") | https://www.dot.ny.gov/divisions/operating/osss/highway-repository/RedBook.pdf | April 2026 |
| 2 | Highway Safety Investigation Procedures Manual ("Yellow Book") | https://www.dot.ny.gov/divisions/operating/osss/highway-repository/YellowBook.pdf | April 2026 |
| 3 | Highway Design Manual, Chapter 5 Basic Design, §5.3 Crash Analysis | https://www.dot.ny.gov/divisions/engineering/design/dqab/hdm/hdm-repository/chapt_05.pdf | Revision 104, April 24 2026 (effective design approval on/after Aug 1 2026) |
| 4 | Safety Performance Function (SPF) Parameters for Intersections, Ramps, and Segments (Version 1.1) | https://www.dot.ny.gov/divisions/operating/osss/highway-repository/SPF_Parameters.xlsx (+ SPF_Spreadsheet_Example.xlsx) | v1.1, undated in file |
| 5 | Average Accident Rates (state highways, by facility / intersection type) — index page | https://www.dot.ny.gov/divisions/operating/osss/highway/accident-rates | newest link = "Average Accidents Rates Table_2016.pdf"; **all PDF links on the page return an HTML error page (checked 2026-11-07)** |
| 6 | Average Accident Costs & Severity Distribution — index page | https://www.dot.ny.gov/divisions/operating/osss/highway/accident-costs | newest link 2016 (broken); 2012-13 PDF downloads (SIMS report, Aug 2011–Jul 2013) |
| 7 | NYSDOT 2017–2019 "Average Crash Rates for State Highways by Facility Type" as reproduced in a NYSDOT project report: PIN 1045.18 NYS Route 378 Troy-Menands Bridge PSR/PEL, Appendix 2 Traffic Report | https://www.dot.ny.gov/portal/page/portal/content/delivery/region1/projects/104518-Home/104518-Repository/02%20Final%20DRAFT_NYS%20378%20Bridge%20rpt_PSR_PEL_20241_02112026%20Appendix%202.pdf | report Aug 2025 / Feb 2026; rates "based on crash data September 1, 2017 to August 31, 2019" |
| 8 | FHWA HSIP Evaluation Guide (linked from the NYSDOT Crash Analysis Toolbox) | https://www.dot.ny.gov/divisions/operating/osss/highway-repository/HSIPGuide.pdf | FHWA, May 2017 |

Not found / not public: a current (post-2019) average crash rate table as a NYSDOT file (the Red Book says SPFs and
average crash rates "are available in CLEAR Safety", Red Book p.87 [93], which is login-gated); default countermeasure
costs and service lives ("currently not available at NYSDOT", Red Book p.49 [55]); a CMF list as a file (CMFs live in
CLEAR Safety).

## 2. What each says

### Red Book (April 2026)
- **Screening method (p.35–40 [41–46]):** network screening ranks sites by **Potential for Safety Improvement (PSI)**.
  Where AADT exists: PSI = **excess expected crash frequency** = EB-expected − SPF-predicted (Eq. 2–3, Empirical Bayes,
  N_expected = w·N_predicted + (1−w)·N_observed). Where AADT is missing: PSI = **excess observed crash frequency** =
  observed − average observed for the facility type (Eq. 1), per mile for segments/ramps, per intersection for
  intersections. Ranking: simple ranking for intersections and ramps; segments simple or **sliding window, window
  "typically 0.3 miles", increment "typically 0.1 miles"** (p.40 [46]). Also LOSS (Level of Service of Safety).
- **Severity focus (p.6 [12], p.35 [41]):** annual statewide screening focuses on **fatal and serious injury (KA)**
  crashes on the state system; fall back to KAB or KABC when KA is too sparse.
- **Years (p.37 [43]):** "five consecutive years of roadway and crash data reflecting current conditions are used in
  screening"; drop years before a major change (e.g. stop → signal).
- **Facility types (p.38 [44], App. B p.87–89 [93–95]):** "NYSDOT has defined seventy facility types for network
  screening" (App. B lists segments, ramps, intersections, ramp terminals).
- **SPFs (App. C p.92–93 [98–99]):** NY-specific; segments N = Length × AADT^β1 × exp(α + β2·AADT), length
  coefficient fixed at 1.0, length-dependent dispersion; intersections N = AADTmaj^β1 × AADTmin^β2 × e^α; ramps
  N = AADT^β1 × exp(α + β2·AADT). Two base SPFs per type (KABCO and KABC); CLEAR applies proportions for KA etc.
- **Crash costs (Table 3, p.48 [54]):** K $18,186,968; A $991,313; B $309,976; C $194,893; O $18,794; combined
  K/A $2,601,585; K/A/B $1,241,963; K/A/B/C $475,186; K/A/B/C/O $137,317; A/B/C $292,755; B/C $215,404. Year: the
  Yellow Book's identical Table 2 is labelled **2024 dollars**; "based on the FHWA guide Crash Costs for Highway Safety
  Analysis"; "adjusted annually using the Consumer Price Index".
- **Economics (p.49 [55]):** discount rate **3%**; BCR threshold 1.0 (p.17 [23]) but below 1 does not disqualify.
- **CMFs (p.47–48 [53–54]):** from the CMF Clearinghouse / research first, then from SPFs or average crash rates, then
  engineering judgment; CLEAR Safety holds default CMFs.
- **Evaluation (p.59–60 [65–66], p.70 [76]):** minimum 3 full years before and 3 after; 3–5 years recommended for
  countermeasure evaluations; EB before-after preferred (p.67 [73]).
- **Rates in exposure units:** the Red Book itself uses crashes per mile / per intersection for observed screening and
  per 100 million VMT only for the federal performance measures (p.19 [25]). No rate table.

### Yellow Book (April 2026)
- **When an investigation is required (Table 1, p.3 [9]):** KA or KABC **LOSS = 4 → Highway Safety Investigation
  required** (LOSS ≤ 3 optional); test of proportions flags over-represented crash types (optional trigger).
- **Study period (p.4 [10], p.9 [15]):** "typically includes the latest three years of complete crash data"; extend for
  low-volume roads; build a collision diagram one year at a time to decide.
- **Crash costs (Table 2, p.16 [22]):** same values as Red Book Table 3, **"2024 dollars"**.
- **Forms:** CLEAR Safety's crash list "supersedes the TE-213 form previously used in the SIMS application" (p.6
  [12]); collision diagram template in App. D; crash history list App. A (p.30 [36]). Benefit-cost: annual benefit
  = Σ_i crash cost_i × (expected without − expected with countermeasure) (p.16–18 [22–24]).
- **Magnitude classes (Table 3, p.19 [25]):** < 10% small, 10–25% medium, > 25% large.

### Highway Design Manual Ch. 5 §5.3 (Rev. 104, 2026-04-24)
- Every highway/bridge project that can affect crash frequency/severity needs an **Initial Crash Screening (HSS100)**
  plus an Intermediate or Advanced analysis (p.5-26 [26]).
- Initial screening steps (p.5-27 [27]): sites = SPF facility types; past PIL/AWP within 5 years; HSI within 5 years;
  test of proportions; **PSI > 0**; LOSS.
- **Years of data:** the published page literally reads "ADD IN OLD TEXT WITH NUMBER OF YEARS OF DATA (2 years for
  AADT over 100,000, 3 years normally, and 5 years for AADT under 2,000)" and "If the most current crash data used in
  the analysis gets to be more than 5 years old the entire crash analysis needs to be redone" (p.5-27 [27]). An editing
  note left in the manual; the 2/3/5-year rule is what it states.
- Cites fatal $18,186,968 and serious injury $991,313 (p.5-26 [26]).

### Average crash rates (2017–2019, via PIN 1045.18 report, App. 2, PDF p.103 and p.126–130)
- Formulas used there: segment rate = 1,000,000 × crashes/year ÷ (365 × AADT × length mi) → **acc/MVM**; intersection
  rate = 1,000,000 × crashes/year ÷ (365 × entering AADT) → **acc/MEV** (PDF p.102–103).
- A location whose rate exceeds the NYSDOT average for its facility type is a **High Accident Location (HAL)** (PDF
  p.102). Columns: All Types, Wet Road, Fixed Object (segments); All Types, Wet Road, Left Turn, Rear End, Overtaking,
  Right Angle, Right Turn, Head On, Sideswipe (intersections).
- Rows the report itself labels (Exhibits 1–2, PDF p.103), "mainline & juncture":
  - Urban, controlled access (full), divided, 4 lanes: All 1.33, Wet 0.26, Fixed object 0.27 acc/MVM
  - Urban, free access, undivided, 4 lanes: All 6.41, Wet 1.22, Fixed object 0.31 acc/MVM
  - Urban intersection, 3-leg, signal, 1–4 lanes: All 0.32, Wet 0.06 acc/MEV
  - Urban intersection, 3-leg (stated as "No Control All Lanes"): All 0.06, Wet 0.01 acc/MEV
  - Urban intersection, 4-leg, signal, 1–4 lanes: All 0.56, Wet 0.10 acc/MEV
- The full table is on PDF p.126–130, but the text layer drops the rural/urban and access headings, so the other rows
  are **not copied** here. (Text dump: `manuals/psr_378_appendix_rates.txt`.) The same report's p.122–125 reproduce the
  SIMS "Average Accident Costs/Severity Distribution" (Fatal / Injury / PDO, not KABCO).

### SPF Parameters v1.1 (xlsx)
- 576 rows = **113 facility types** (64 intersection, 28 segment, 21 ramp) × {Total, Fatal and Injury}; columns CA
  (long-term **calibration factor**), CB, BC, B1, B2, BL, D1–D3, plus EB/excess/LOSS calculator columns.
  CA = 1 on 522 of 576 rows. Example: Urban 4-Leg Signalized (type 25) total: BC −7.601, B1 0.539, B2 0.451, D1 0.39;
  F+I: BC −8.804, B1 0.569, B2 0.455, D1 0.34.

## 3. Differences from California (Caltrans LRSM, TASAS, Caltrans costs)
1. **Screening:** NY ranks by **EB excess expected KA crashes** (PSI, HSM method) with LOSS; Caltrans TASAS Table C
   flags locations whose actual rate significantly exceeds the **base (expected) rate** for the highway type.
2. **Rate tables:** NY's per-MVM / per-MEV averages were last posted for 2017–2019 and the posted files are now broken;
   current averages sit inside CLEAR Safety (gated). Caltrans publishes TASAS base rates.
3. **Severity focus:** NY network screening is **KA** first; Caltrans TASAS rates are total and fatal+injury rates
   (CA side from the existing CA pack, not re-read today).
4. **Costs:** NY uses FHWA-2018-method KABCO costs in **2024 dollars** (K $18.19M, A $0.99M, B $0.31M, C $0.19M,
   O $18.8k); compare with Caltrans' own LRSM/B-C crash costs (CA values not re-read today — see California notes).
5. **Study period:** HDM says 2 / 3 / 5 years by AADT (> 100,000 / normal / < 2,000), Yellow Book 3 years typical,
   screening 5 years. Caltrans corridor studies commonly use 3 years (TASAS) — confirm in the CA pack.
6. **Non-reportable crashes:** NY exports carry "NON-REPORTABLE" (property damage below the DMV reporting threshold);
   SIMS cost tables include them ("Includes Both Reportable and Non-Reportable Accidents"). California has no such class.
7. **Location:** NY state highways are referenced by **reference marker** (route + region/county + 0.1-mi marker) and
   the CLEAR Milepoint LRS, not postmiles.
8. **Discount rate 3%** (NY HSIP default).

## 4. Not checked
- Current (2020+) average crash rates and the rural/urban rows of the 2017–2019 table.
- CLEAR Safety's CMF list and its proportions for KA from the KABC SPFs.
- Whether NYSDOT updates the crash costs every year (the manuals say CPI-adjust annually; CLEAR holds the newest).
- California cost/rate values were not re-read today; comparisons are by method only.
