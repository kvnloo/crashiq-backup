# Massachusetts: safety-analysis manuals, rates, costs, screening (Hermes, 2026-11-07)

PDFs are in `~/.hermes/cache/scratch/states/ma/manuals/` (not committed). Page numbers are the printed page, with the
PDF page in brackets where they differ. Every number below is copied from the cited document; "not found" means I
looked and the document doesn't give it.

## Documents

| # | Title | URL | Edition / date |
|---|---|---|---|
| 1 | Intersection and roadway crash rate data for analysis (web page) | https://www.mass.gov/info-details/intersection-and-roadway-crash-rate-data-for-analysis | intersection rates queried 2018-06-26; FC rates queried 2023-06-01 |
| 2 | Crash Rate Procedures (worksheet instructions) | https://www.mass.gov/doc/crash-rate-analysis-instructions/download | undated, 2 pp. |
| 3 | Intersection Crash Rate Worksheet / Segment Crash Rate Worksheet (required forms) | https://www.mass.gov/doc/intersection-worksheet/download ; https://www.mass.gov/doc/roadway-worksheet/download | undated, 1 p. each |
| 4 | Crash Costs for Highway Safety Analysis (web page) | https://www.mass.gov/info-details/crash-costs-for-highway-safety-analysis | 2024 costs |
| 5 | MassDOT Safety Alternatives Analysis Guide | https://www.mass.gov/doc/massdot-safety-alternatives-analysis-guide/download | October 2021, 59 pp. |
| 6 | Safety Alternatives Analysis Spreadsheet Tool, Method 3 | https://www.mass.gov/doc/massdot-safety-alternatives-analysis-spreadsheet-tool-method-3-september-2024/download | Sep 2024 (xlsx; Methods 1 and 2 "available by request") |
| 7 | HSIP Project Selection Criteria | https://www.mass.gov/doc/highway-safety-improvement-program-criteria/download | undated; cluster tables on 2018–2020 (intersections) and 2011–2020 (ped/bike) data |
| 8 | Highway Safety Improvement Program (web page) + Top crash locations and maps (web page) | https://www.mass.gov/info-details/highway-safety-improvement-program ; https://www.mass.gov/info-details/top-crash-locations-and-maps | current |
| 9 | Calibration of Safety Performance Functions for Massachusetts Urban and Suburban Intersections (UMass Lowell, UMTC 16.01) | https://www.mass.gov/doc/calibration-of-safety-performance-functions-for-massachusetts-urban-and-suburban-intersections/download | March 2016 |
| 10 | Development of Safety Performance Functions for Network Screening: Roadway Segments and Intersections on Arterials and Collectors (VHB) | https://www.mass.gov/doc/development-of-safety-performance-functions-for-network-screening-roadway-segments-and-intersections-on-arterials-and-collectors/download | updated February 2024 |
| 11 | Road Safety Audit Guidelines | https://www.mass.gov/doc/massdot-road-safety-audit-guidelines/download | Nov 2015, revised Oct 2024 |
| 12 | Road Safety Audit Report Template (docx) | https://www.mass.gov/doc/massdot-road-safety-audit-report-template/download | current |
| 13 | Traffic and Safety Engineering 25% Design Submission Guidelines | https://www.mass.gov/doc/25-design-traffic-submission-guidelines/download | revised 2022-05-31 |
| 14 | Intersection Control Evaluation (ICE) Procedure Requirements | https://mass.gov/doc/massdot-ice-procedure-requirements/download | updated 2024-10-10 |
| 15 | Massachusetts HSIP Implementation Plan | https://www.mass.gov/doc/2027-massachusetts-hsip-implementation-plan/download (also the 2026 plan) | September 2026 (and September 2025) |
| 16 | 2023 Strategic Highway Safety Plan | https://www.mass.gov/doc/massachusetts-shsp-2023/download | 2023 |

Not obtained: the "Crash costs methodology" PDF (https://www.mass.gov/doc/crash-costs-methodology/download; mass.gov
returned "Not allowed" to the downloader, rate-limited) and the 2017 Top Crash Locations Report (same). Their content
is summarized on pages 4 and 8, which I did read.

## Crash rates (doc 1, 2, 3)

- **Formulas** (doc 2, p.1–2): intersection `R = A × 1,000,000 / (V × 365)` in crashes per **million entering
  vehicles (MEV)**; A = average crashes per year, V = intersection ADT = sum of seasonally adjusted peak-hour approach
  volumes ÷ K factor ("A default value of 0.09 can be assumed for insufficient ATR data"; PM peak preferred). Segment
  `R = A × 1,000,000 / (L × V × 365)` in crashes per **million vehicle miles traveled (MVMT)**.
- **Study period** (doc 2): "5 year time period preferred, 3 year minimum". Same in doc 13 p.4 ("latest 5 years …
  (preferred) or the latest 3 years … (minimum)").
- **Required**: the worksheet "is a requirement for MassDOT design projects. This includes … Environmental Impact
  Reports, Functional Design Reports, Traffic & Safety Analyses and Mitigation Projects" (doc 2, p.1). Doc 13 p.4:
  segment crash rates by worksheet for Interstate and local roads; arterials and collectors "can be evaluated using the
  crash-based Network Screening Tool"; compare to District and statewide averages.
- **Statewide averages** (doc 1). MassDOT itself warns the rate method "is being replaced with a more scientific
  approach" and the intersection data "is not a random sample … use it with caution, or only as a general screening
  tool".

Average crash rate per MEV by intersection type (queried 2018-06-26):

| Location | Signalized | Unsignalized |
|---|---|---|
| Statewide | 0.78 | 0.57 |
| District 1* | 0.80* | 0.44* |
| District 2 | 0.89 | 0.62 |
| District 3 | 0.89 | 0.61 |
| District 4 | 0.73 | 0.57 |
| District 5 | 0.75 | 0.57 |
| District 6 | 0.71 | 0.52 |

\* District 1 should use statewide rates (low sample).

Crash rate per MVMT by federal functional class (queried 2023-06-01; doc 7 labels the same table "2021"):

| Functional class | Rural | Urban |
|---|---|---|
| Statewide | 0.97 | 2.10 |
| Interstate | 0.45 | 0.81 |
| Principal Arterial – other freeways and expressways | 0.70 | 0.90 |
| Principal Arterial – other | 0.61 | 3.05 |
| Minor Arterial | 1.02 | 2.98 |
| Major Collector | 1.05 | 2.85* |
| Minor Collector | 2.53 | – |
| Local | 1.41 | 2.50 |

\* all urban collectors. A crash at an intersection or between two classes goes to the higher class.

- **Critical rate**: not found. MassDOT compares to the district/statewide average (doc 1, 13) or ranks by EPDO / excess
  expected crashes (doc 7); no critical-rate formula is published in these documents.

## Crash costs (doc 4, 5)

2024 comprehensive crash unit costs per crash, by the most severe injury (doc 4; FHWA-SA-17-071 method):

| K | A | B | C | O | KA | KAB | KABC | KABCO |
|---|---|---|---|---|---|---|---|---|
| $19,435,000 | $1,112,900 | $354,100 | $208,000 | $20,900 | $3,582,900 | $835,100 | $573,600 | $160,200 |

Doc 5 (Oct 2021) still prints the **2019** costs (Table 4, p.21 [PDF 28]): K $16,257,800, A $941,300, B $284,600,
C $179,600, O $16,700, K+A $2,764,700, K+A+B $706,100, K+A+B+C $441,000, K+A+B+C+O $121,400; and **average FI and PDO
costs by facility type** (Table 5, p.21), e.g. U3SG $339,500, U3ST $352,800, U4SG $327,200, U4ST $319,100, U2UA $484,100
(District 1–6: $501,300 / $490,700 / $532,100 / $402,400 / $522,500 / $462,000), U4UA $481,300, U4DA $530,800,
R2U $878,400; PDO $16,700 for all. Footnote 3: "contact the MassDOT Traffic and Safety Section to ensure they have the
most up-to-date average crash costs." Economic analysis: uniform-series present worth, **discount rate 7%** (p.23
[PDF 30]).

## Severity weighting and screening (doc 7, 8, 10, 11)

- **EPDO**: "Starting in 2016, the weighting factors were updated so that fatal and injury crashes are worth 21 and a
  property-damage only crash is worth 1" (before 2016: fatal 10, injury 5, PDO 1) (doc 8, HSIP page footnote; doc 7).
  The 21 comes from the crash costs ("so as not to end up just chasing fatal crashes, all of the fatal and injury
  crashes were weighted together", top-crash-locations page).
- **Clusters** (doc 8): intersection clusters use junction types four-way, T, Y, five-point; 3 most recent closed
  years; 25 m (82 ft) search-and-merge radius; ranked by EPDO. Ped/bike clusters: 100 m (328 ft), 10 closed years.
- **HSIP eligibility** (doc 7): top 5% EPDO clusters per region (RPA/MPO). Minimum EPDO for top-5% intersections
  (2018–2020): BRPC ≥89, CCC ≥93, CMRPC ≥117, FRCOG ≥72, MAPC ≥108, MRPC ≥96, MVC ≥45, MVPC ≥111, NMCOG ≥119, NPEDC ≥26,
  OCPC ≥178, PVPC ≥157, SRPEDD ≥122 (pedestrian and bicycle tables in the same document, 2011–2020). Ranking: EPDO
  preferred; "When feasible, expected crashes based on Safety Performance Functions and Empirical Bayes is preferred. If
  not, crash rate formulas (EPDO per Million Entering Vehicles or per million vehicle miles traveled) can be used".
  Segments: rate above the statewide average for the functional class (with an RSA), or **top 5% by excess expected
  crash frequency (EB-adjusted)** in the IMPACT network-screening tool, for 5 arterial/collector facility types, all or
  FI crashes, statewide and per MPO/RPA. Every spot HSIP candidate needs an RSA.
- **Network-screening SPFs** (doc 10, Feb 2024, p.5): state-specific planning-level SPFs, developed on 5 years
  (2015–2019) and applied to 2017–2021 closed data (p.9 [PDF 11]); regional models (e.g. Berkshire + Franklin + Pioneer
  Valley combined for rural). No reliable SPFs for Interstates and local roads.
- **RSA trigger** (doc 11, p.4–5): projects at or next to a high-crash location (vehicle, bicycle or pedestrian;
  "check all available years' crash clusters"; compare EPDO to the regional maximum in doc 7), or HSIP-funded. Doc 13:
  if HSIP-eligible, an RSA replaces the safety review; collision diagrams for intersections with more than 3 crashes per
  year, from police reports with diagrams and narratives.
- **ICE** (doc 14): a high-crash location for ICE = an intersection on the MassDOT crash cluster map (p.3).

## SPF / HSM calibration and CMFs (doc 5, 9)

- Calibrated HSM SPFs exist only for urban/suburban intersections U3SG, U3ST, U4SG, U4ST (doc 5 Table 1, p.5 [PDF 12])
  plus segment SPFs for network screening (doc 10).
- **Calibration factors Ci** (doc 9, Table 28, p.40 [PDF 58]): HSM SPFs: 3SG **1.50**, 3ST **0.77**, 4SG **1.49**,
  4ST **1.03**; MA Bayesian NB SPFs: 3SG 0.95, 3ST 1.13, 4SG 1.00, 4ST 1.04. Recommendation: use the Bayesian SPFs.
  MA multiple-vehicle SPF coefficients (Table 27): 3SG a −8.30, b 0.81, c 0.21, k 0.41; 3ST −20.02, 1.66, 0.54, 0.24;
  4SG −11.79, 0.92, 0.52, 0.10; 4ST −8.70, 0.31, 0.86, 0.36.
- Alternatives analysis (doc 5, p.10 [PDF 17]): "Method 1 is the preferred method for alternatives analysis, followed by
  Method 2. Written justification must be provided when Method 2 or Method 3 are employed." Method 1 = EB expected
  (3–5 years), Method 2 = SPF predicted, Method 3 = observed (e.g. roundabouts, "MassDOT does not have a calibrated SPF
  for roundabouts").
- **CMFs**: "MassDOT's State-Preferred CMF List, available in the Massachusetts Safety Analysis Tools" (doc 5, p.5
  [PDF 12]), All and FI levels; other CMFs need MassDOT Safety Group review. The list itself is inside the spreadsheet
  tools; Methods 1–2 tools are by request (doc 8).

## Required study forms
Intersection and Segment Crash Rate Worksheets (doc 3); Safety Alternatives Analysis spreadsheet tools (doc 6, Methods
1–2 by request); RSA report template (doc 12); ICE form (doc 14, Stage 1); collision diagrams and collision map (doc 13).

## Different from California
1. Severity weighting: MA ranks by **EPDO 21 : 1** (any injury or fatal = 21); Caltrans LRSM prices each KABCO level
   (CrashIQ `crash_cost.py`: LRSM v1.8 KA by location type, B, C, O).
2. Costs: MA 2024 K $19,435,000 / A $1,112,900 / B $354,100 / C $208,000 / O $20,900 separately for K and A; LRSM v1.8
   (2026 $) combines K+A by location type (KA $2,379,000 signalized … $3,784,000 non-signalized) with B $213,000,
   C $121,000, O $20,000 (`data/reference/crash_costs_ca.csv`).
3. Method: MA prefers **SPF + Empirical Bayes** (HSIP ranking and Method 1); Caltrans' LRSM "has avoided using
   methodology requiring … Empirical Bayes" and uses 3–5 years of observed crashes (reports/Crash analysis industry
   methods.md).
4. Rates: MA intersection average 0.78 / 0.57 per MEV (signalized / unsignalized) and per-MVMT rates by functional
   class; no rate groups like Caltrans' TASAS 31 intersection groups, and no critical-rate formula.
5. Discount rate 7% in MA alternatives analysis; HSIP eligibility is relative (top 5% per region), not a BCR cutoff as
   in Caltrans HSIP calls.
6. Study period: 5 years preferred, 3 minimum (MA) — same span as LRSM's 3–5 years.
7. MA intersection clusters use police-coded junction type and a 25 m radius; CrashIQ assigns crashes to intersections
   from the street network.

## Not found / not checked
Critical-rate method (not found); the crash-cost methodology PDF and crash-type costs (download blocked); the CMF list
contents and Methods 1–2 spreadsheets (by request); KABCO-specific EPDO beyond 21:1 (not found); HSIP B/C cutoff (not
found; HSIP plan reports program B/C only).
