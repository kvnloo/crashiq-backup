# Oregon: safety analysis methods, rates and crash costs (2026-11-07)

Every number below is copied from the manual cited, with its page. PDFs are in
`~/.hermes/cache/scratch/states/or/manuals/` (not committed). "PDF p." = page of the PDF file; "doc p." = the number
printed on the page. Checked 2026-11-07.

## Manuals found

| # | Manual | URL | Edition / date |
|---|---|---|---|
| 1 | ODOT Analysis Procedures Manual v2 (APM), Chapter 4 Safety | https://www.oregon.gov/odot/Planning/Documents/APMv2_Ch4.pdf | "Last Updated 12/2025" (141 pages) |
| 2 | APM Appendix 4A, Crash Attribution and Automation | https://www.oregon.gov/odot/Planning/Documents/APMv2_App4A.pdf | PDF dated 2022-05-19 (page says updated 06/08/2022) |
| 3 | APM Chapter 19, Traffic Analysis Reports (what a study must contain) | https://www.oregon.gov/odot/Planning/Documents/APMv2_Ch19.pdf | "Last Updated 08/2023" |
| 4 | ODOT Highway Safety Improvement Program Guide ("A Guide to Developing Highway Safety Projects") | https://www.oregon.gov/odot/engineering/docs_trafficeng/safety_hsip-guide.pdf | February 2021 |
| 5 | ODOT Safety Investigation Manual (SIM) | https://www.oregon.gov/odot/Engineering/Docs_TrafficEng/Safety-Investigation-Manual.pdf | January 2022 Edition |
| 6 | ODOT Crash Reduction Factor Manual (the ARTS/HSIP CMF list) | https://www.oregon.gov/odot/Engineering/ARTS/CRF-Manual.pdf | October 2026 Edition (327 pages) |
| 7 | Oregon State Highway Crash Rate Tables 2024 (CAR Unit), incl. Table II | https://www.oregon.gov/odot/Data/Documents/Crash_Rate_Tables_2024.pdf and https://www.oregon.gov/odot/Data/Documents/Crash_Rate_Table_II.pdf | posted 2026-10-26 / 2026-10-06 |
| 8 | Oregon Transportation Safety Action Plan 2021 (TSAP) | https://www.oregon.gov/odot/Safety/Documents/2021_Oregon_TSAP.pdf | 2021 (PDF re-saved 2024-08-05) |
| 9 | ODOT CDS Code Manual (crash data dictionary, severity codes) | https://www.oregon.gov/odot/Data/documents/CDS_Code_Manual.pdf | downloaded 2026-11-07 |

Not found as an Oregon publication: a crash-cost table per single KABCO level (Oregon publishes K+A and B+C combined,
below), a required "study form" (ODOT gives spreadsheets instead: the Critical Rate Calculator, the Excess Proportion
calculator and the SIM Worksheet, https://www.oregon.gov/odot/planning/pages/technical-tools.aspx). The ARTS criteria
page https://www.oregon.gov/odot/Engineering/ARTS/Criteria.pdf returned 404 on 2026-11-07.

## 1. Exposure units and rate formulas (APM Ch. 4)

- Intersections: crashes per **million entering vehicles (MEV)**; segments: crashes per **million vehicle miles
  traveled (MVMT)** (APM 4.3.4, PDF p. 21-23, doc p. 4-21 to 4-23).
- `MEV = AADT x 365 x n / 1,000,000`, n = number of years (doc p. 4-23); `MVMT = AADT x L x 365 x n / 1,000,000`, L =
  segment length (doc p. 4-23). Intersection crash rate = crashes x 10^6 / (AADT x 365 x years) (doc p. 4-3).
- Table II footnote: rate = (crashes x 1,000,000) / VMT, crashes per million vehicle miles (Crash_Rate_Table_II.pdf p. 1).
- Example 4-1 (doc p. 4-24): 22 crashes, 1.6 mi, AADT 23,000, 3 years -> 0.55 crashes per MVM.

## 2. Statewide average rates

### Intersections: APM Exhibit 4-1 (doc p. 4-3), crashes per MEV
Source given: *Assessment of Statewide Intersection Safety Performance*, FHWA-OR-RD-18, PSU/OSU, June 2011, Table 4.1,
data 2003-2007, 500 intersections. Only intersection / intersection-related crashes.

| | Rural 3SG | Rural 3ST | Rural 4SG | Rural 4ST | Urban 3SG | Urban 3ST | Urban 4SG | Urban 4ST |
|---|---|---|---|---|---|---|---|---|
| Intersections | 7 | 115 | 20 | 60 | 55 | 77 | 106 | 60 |
| Mean rate | 0.226 | 0.196 | 0.324 | 0.434 | 0.275 | 0.131 | 0.477 | 0.198 |
| Median | 0.163 | 0.092 | 0.320 | 0.267 | 0.252 | 0.105 | 0.420 | 0.145 |
| Std dev | 0.185 | 0.314 | 0.223 | 0.534 | 0.155 | 0.121 | 0.273 | 0.176 |
| CV | 0.819 | 1.602 | 0.688 | 1.230 | 0.564 | 0.924 | 0.572 | 0.889 |
| **90th percentile** | 0.464 | 0.475 | 0.579 | 1.080 | 0.509 | 0.293 | 0.860 | 0.408 |

3SG/4SG = 3/4-leg signalized, 3ST/4ST = 3/4-leg minor-street stop. Rule: a rate "close to or over" the 90th percentile is
flagged (doc p. 4-3). Configurations not in the table are flagged by default (doc p. 4-3); Exhibits 4-2 and 4-3 (doc
p. 4-4, 4-5) say which rate to borrow for a 3-leg stop with a driveway leg and a 4-leg 3-way stop.

### Segments (state highways only): Crash Rate Table II, crashes per MVMT, mainline only (no connections, frontage roads)
Crash_Rate_Table_II.pdf p. 1 (2024 edition; "Miles" = 2024 only):

| Jurisdiction / functional class | Miles | 2024 | 2023 | 2022 | 2021 | 2020 |
|---|---|---|---|---|---|---|
| Total state highway system | 7,369.91 | 0.91 | 0.89 | 0.86 | 0.91 | 0.84 |
| Interstate freeways | 729.57 | 0.45 | 0.42 | 0.42 | 0.44 | 0.38 |
| Other freeways/expressways | 90.69 | 0.77 | 0.77 | 0.72 | 0.75 | 0.61 |
| Non-freeways (combined) | 6,549.65 | 1.33 | 1.33 | 1.27 | 1.35 | 1.27 |
| Urban highway system | 1,083.28 | 1.12 | 1.07 | 1.01 | 1.08 | 0.96 |
| Urban interstate | 220.00 | 0.54 | 0.49 | 0.46 | 0.50 | 0.41 |
| Urban other fwy/expwy | 75.89 | 0.81 | 0.77 | 0.72 | 0.75 | 0.61 |
| Urban non-freeways | 787.39 | 1.96 | 1.87 | 1.77 | 1.89 | 1.74 |
| Urban other principal arterials | 587.53 | 1.99 | 1.89 | 1.78 | 1.92 | 1.76 |
| Urban minor arterials | 162.82 | 1.74 | 1.75 | 1.68 | 1.70 | 1.59 |
| Urban collectors | 37.04 | 2.04 | 1.84 | 2.08 | 1.58 | 1.92 |
| Urban cities (all) | 592.50 | 1.33 | 1.24 | 1.17 | 1.26 | 1.10 |
| Urban cities, non-freeways | 423.05 | 2.55 | 2.34 | 2.19 | 2.32 | 2.08 |
| Urban cities, other principal arterials | 334.73 | 2.61 | 2.35 | 2.20 | 2.35 | 2.10 |
| Urban fringe (all) | 490.78 | 0.74 | 0.75 | 0.71 | 0.75 | 0.72 |
| Rural highway system | 6,286.63 | 0.68 | 0.70 | 0.70 | 0.73 | 0.69 |
| Rural interstate | 509.57 | 0.34 | 0.33 | 0.38 | 0.36 | 0.33 |
| Rural non-freeways | 5,762.26 | 0.91 | 0.93 | 0.91 | 0.97 | 0.92 |
| Rural other principal arterials | 2,641.18 | 0.79 | 0.82 | 0.79 | 0.86 | 0.83 |
| Rural minor arterials | 1,801.89 | 1.13 | 1.16 | 1.15 | 1.14 | 1.13 |
| Rural major collectors | 1,282.29 | 1.48 | 1.53 | 1.44 | 1.68 | 1.27 |
| Rural minor collectors | 34.03 | 2.24 | 3.69 | 2.29 | 3.30 | 2.98 |
| Rural cities (all) | 152.82 | 1.05 | 1.20 | 0.95 | 1.04 | 0.99 |
| Rural areas (all) | 6,133.81 | 0.67 | 0.68 | 0.69 | 0.72 | 0.68 |

(The PDF text layer splits some digits, e.g. "0. 77"; values above were read back from it; the full table, with every
sub-row, is on that page.) Tables III-V (rates per highway and section) are in the 298-page 2024 Crash Rate Tables PDF.
No published rates for city streets or county roads: the 90th-percentile intersection rates (Exhibit 4-1) are the only
off-system comparison.

## 3. Screening methods

- **Critical crash rate** (APM 4.3.4, doc p. 4-20 to 4-31): `Rc = Ra + P x sqrt(Ra / M) + 1 / (2 x M)`, M = MEV or
  MVMT, P = 1.645 at 95% (doc p. 4-31: "Typical use would be 95% confidence (P=1.645)"). Ra = reference-population
  average; a statewide variant uses the Exhibit 4-1 mean instead (doc p. 4-22, 4-24). Run for total crashes and,
  suggested, for fatal + injury-A crashes only (doc p. 4-22). Worked example doc p. 4-31: Ra 0.17, M 13.9 -> Rc 0.39;
  F+A: 0.04 -> 0.17. Needs at least 5-10 sites per reference population (doc p. 4-24). Intersection analysis uses only
  intersection crashes; segment analysis only segment crashes, except Table II comparisons, which use all crashes on the
  segment (doc p. 4-22, 4-23). Segments ~1 mile, avoid < 0.5 mile (doc p. 4-23).
  SIM 2.4 (PDF p. 19) gives the same formula with "K = 1.645 for 90%" — the two ODOT manuals disagree on the confidence
  label for 1.645.
- **Excess proportion of specific crash types** (APM 4.3.5, Appendix 4A; ODOT calculator): required with critical rate
  for TSPs and corridor plans (APM Exhibit 4-4 text, doc p. 4-6).
- **SPIS (Safety Priority Index System)** (APM 4.3.1, doc p. 4-18): ODOT's statewide hot-spot screen since 1986, on
  0.10-mile segments, 3 years of crashes, score from frequency + rate + severity; a segment qualifies with 3+ crashes or
  1+ fatal in 3 years; top 5% / 10% listed every year; top 5% sites get a Region safety investigation each year. Since
  the 2015-2017 SPIS, PDO crashes are planned to be excluded and one Injury-A crash qualifies a segment. Every
  application must report top 5%/10% sites from the 3 most recent SPIS listings (doc p. 4-6). SPIS's own scoring
  formula is on the SPIS website, not in the APM (not downloaded).
- Minimum requirement when nothing else applies: compare intersections to Exhibit 4-1 90th percentiles and segments to
  Table II (doc p. 4-6).

## 4. Years of data

- APM: "it is recommended that five years of crash data be used whenever possible" (doc p. 4-14); critical rate: never
  less than three years (doc p. 4-21); SPIS: three years (doc p. 4-18).
- SIM 2.5 (PDF p. 21): "A general recommendation is to use 3 years of crash data"; 5 years when data are few.
- HSIP/ARTS: "five years of the most recent crash data available" and B/C >= 1.0 (HSIP Guide p. 12-13, PDF p. 16-17;
  CRF Manual: hotspots need a fatal or serious-injury crash in the last five years).

## 5. Crash costs (comprehensive economic value per crash)

Oregon prices **K and A together, and B and C together**, by highway type and urban/rural. No single-level K, A, B, C.

TSAP 2021, Table 2 (doc p. 48, PDF p. 54), **2019 values**, "based on HSM Appendix 4A and FHWA's Crash Cost Estimates by
Maximum Police-Reported Injury Severity Within Selected Crash Geometrics":

| Crash | Interstate urban | Interstate rural | Other state hwy urban | Other state hwy rural | Off system urban | Off system rural |
|---|---|---|---|---|---|---|
| Fatal + serious (A) | $1,530,000 | $2,260,000 | $1,490,000 | $2,140,000 | $1,110,000 | $1,940,000 |
| Moderate (B) + minor (C) | $77,800 | $89,200 | $80,800 | $91,900 | $81,300 | $93,200 |
| PDO (all) | $21,800 | $21,800 | $21,800 | $21,800 | $21,800 | $21,800 |

HSIP Guide 2021, Table 3-1 (doc p. 12, PDF p. 16), **2012 dollars**, the table the ARTS benefit-cost workbook cites:
K+A $1,150,000 / $2,330,000 (interstate urban / rural), $1,170,000 / $1,680,000 (other state highways), $870,000 /
$1,670,000 (local roads); B+C $69,300 / $79,200, $70,600 / $81,900, $72,400 / $83,900; PDO $19,400. Which table the
current ARTS B/C workbook uses was not checked (the workbook wasn't downloaded).

## 6. Severity

- KABCO, coded per person (CDS Code Manual; decode DB INJ_SVRTY: 1 K, 2 A, 3 B, 4 C, 9 no apparent injury); crash
  severity is fatal / non-fatal injury / PDO plus the highest person level.
- Weighting: no EPDO weights in the APM. The SIM worksheet computes "a severity-based crash rate in which weights can be
  given to each severity based on the context of the analysis" (SIM doc p. 39, PDF p. 48) — weights left to the analyst.
- Since 2015 a pedestrian or bicycle crash with a motor vehicle is at least a "possible injury" (C), never PDO (Crash
  Data Disclaimers).
- Oregon is a self-reporting state; PDO threshold $2,500 since 2018-01-01 (Crash Data Disclaimers). APM doc p. 4-56:
  "Oregon conditions data should not be directly related to national averages or adjacent states (i.e., Washington),
  which have different reporting thresholds."

## 7. HSM calibration factors and CMFs

- APM Exhibit 4-11 (doc p. 4-57), source *Calibrating the Future Highway Safety Manual Predictive Methods for Oregon
  State Highways*: segments R2 0.74; MRU 0.37; MRD 0.77; U2U 0.62; U3T 0.81; U4D 1.41 / 0.64 (use 0.64 for new
  designs); U4U 0.63; U5T 0.64. Intersections R3ST 0.31; R4ST 0.31; R4SG 0.45; MR3ST 0.15; MR4ST 0.39; MR4SG 0.15;
  U3ST 0.35; "U4ST 4-leg, signalized" 0.45 (printed so; the label probably means minor-stop); U3SG 0.73; U4SG 1.05.
  Freeway/interchange (ISATe) calibration failed: report uncalibrated (doc p. 4-56). Uncalibrated results only for
  relative comparison (doc p. 4-57/58).
- CMFs: ODOT Crash Reduction Factor Manual (Oct 2026): one fixed CRF per countermeasure with crash type, severity,
  service life (5/10/20 yr), facility type and context; ARTS projects must use only these. APM allows the CRF list or
  the FHWA CMF Clearinghouse for HSM Part C work (APM Ch. 19, doc p. 19-20).

## 8. What a study must contain (APM Ch. 19, doc p. 19-20; APM Exhibit 4-4)

Historical crash summaries and rate tables in a workbook; HSM Part B screening (critical rate + excess proportion) when
more than about six intersections; SPIS top 5/10% sites; HSM Part C with Oregon calibration where alternatives are
compared. No fixed form; ODOT's spreadsheets are the expected format.

## 9. Differences from California (what CrashIQ does today)

1. **Exposure and comparison rates.** California compares state highways to TASAS base rates (base + ADT factor, per
   MVM / per MV for ramps). Oregon publishes Table II (state-highway mainline, per MVMT, by urban/rural x functional
   class, five years side by side) and, for intersections, a fixed 2003-2007 per-MEV table with 90th percentiles. No
   ADT factor; no ramp rates found.
2. **Intersection flag rule.** Oregon flags an intersection above the **90th percentile** rate (Exhibit 4-1) and above
   its critical rate. CrashIQ has no percentile rule.
3. **Critical rate** is the same HSM formula, but ODOT's default is P = 1.645 and a second run on fatal + injury-A only.
4. **Crash costs** are K+A and B+C combined, by highway type x urban/rural (6 cells each), 2019 values; Caltrans LRSM
   v1.8 (2026 dollars) prices KA by location type (signalized / non-signalized / roadway) and B, C, O separately
   (`data/reference/crash_costs_ca.csv`). Oregon's PDO $21,800 (2019) vs LRSM O $20,000 (2026).
5. **Data window.** APM: 5 years recommended; SIM: 3 years; SPIS: 3 years; ARTS: 5 years. California pack uses its own
   default window.
6. **CMFs.** One fixed CRF per countermeasure (ODOT CRF Manual) for funding; Caltrans has its own LRSM CRF list.
7. **HSM calibration**: Oregon publishes local calibration factors (Exhibit 4-11); CrashIQ CA has none.
8. **Severity data**: Oregon's PDO coverage depends on driver self-reports ($2,500 threshold, ~60% of packets with a
   police report in 2020-2024), so PDO-heavy rates aren't comparable with California's.
9. **Network screening** is SPIS (ODOT's own, 0.1-mile, 3 years), not Caltrans' TASAS Table C / wet-table screens.
