# North Carolina: safety-analysis methods, rates and costs (NCDOT)

Hermes, 2026-11-07. Every number below is copied from the manual cited next to it; PDFs are in
`~/.hermes/cache/scratch/states/nc/manuals/` (not committed). Page numbers are the printed page numbers unless
"PDF p." is given. "Not found" means I looked in these documents and NCDOT's safety pages and didn't find it.

## Manuals found

| # | Title | URL | Edition / date |
|---|---|---|---|
| M1 | 2021 ~ 2025 Five Year Crash Rates (Traffic Safety Unit) | https://connect.ncdot.gov/resources/safety/Documents/Crash%20Data%20and%20Information/2025%20Crash%20Rates.pdf | 2021-2025 data, PDF created 2026-04-08, 6 pp. |
| M2 | 2025 Standardized Crash Cost Estimates for North Carolina | https://connect.ncdot.gov/resources/safety/Documents/Crash%20Data%20and%20Information/Crash%20Costs%202025.pdf | 2025 dollars, PDF created 2026-04-08, 6 pp. |
| M3 | 2026 HSIP Overview (Highway Safety Improvement Program, Traffic Safety Systems Section) | https://connect.ncdot.gov/resources/safety/HSIP%20Library/2026%20HSIP-Overview.pdf | March 2026, 10 pp. |
| M4 | 2024 HSIP Warrants (previous edition, for comparison) | https://connect.ncdot.gov/resources/safety/HSIP%20Library/2024%20HSIP%20Warrants.pdf | May 2024, 5 pp. |
| M5 | TEAAS training Chapter 15, Analysis Techniques | https://connect.ncdot.gov/resources/safety/Documents/TEAAS/Chapter%2015%20Analysis%20Techniques.pdf | Revised 2012-11-27, 30 slides |
| M6 | North Carolina Project Development Crash Reduction Factor (CRF) Information | https://connect.ncdot.gov/resources/safety/TrafficSafetyResources/NCDOT%20CRF%20Update.pdf | Last updated 2025-06-06, 35 pp. |
| M7 | Updated Statewide and Regional Calibration Factors for HSM Crash Prediction Models (2020-2023), NCDOT RP 2025-06 (Penn State, VHB) | https://connect.ncdot.gov/projects/research/RNAProjDocs/RP2025-06_Final%20Report.pdf | March 2026 (last updated 2026-04-24), 109 pp. |
| M8 | Collision Diagrams (TEAAS collision diagram instructions) | https://connect.ncdot.gov/resources/safety/Crash%20Data%20and%20TEAAS%20System/TEAAS/Collision%20Diagram%20Instructions.pdf | Last updated 2013-01-18, 45 pp. |
| M9 | Crash Costs one-pager (Traffic Safety Unit Programs) | https://connect.ncdot.gov/resources/safety/TrafficSafetyResources/One%20Pager_Crash%20Costs.pdf | 2023 costs, PDF 2024-11-14 |
| M10 | Crash Reporting Data Informational Guide | https://connect.ncdot.gov/resources/safety/Crash%20Data%20and%20TEAAS%20System/Crash%20Data%20and%20Information/Crash%20Reporting%20Data%20Informational%20Guide.pdf | 2014-03-14, 8 pp. (downloaded, not read in detail) |

An "HSIP Manual" link on the Traffic Safety Manuals page (`.../TEPPL All Documents Library/HSIP Manual.aspx`) redirects
to the Highway Safety Programs page; no separate HSIP manual PDF was found. The yearly HSIP Overview (M3) is the
working document.

## Crash rates (M1)

- **Unit:** crashes per **100 million vehicle miles of travel (100 MVMT)** (M1 p. 1, note 1). Five-year window,
  2021-2025. Only route segments with computerized traffic volumes (M1 pp. 2-6 note).
- **Formula** (M5 slides 16-17): crash rate = crashes / exposure, exposure = AADT × 365 × years × segment miles
  (the 2012 slide says 3 years; the published table now uses 5). Rates are computed for **sections (strips) only**,
  with no Y-line (0 ft), split urban/rural and by road classification (M5 slide 16). **No intersection rate per
  million entering vehicles (MEV) was found.**
- **Rate types:** total, fatal, non-fatal injury, wet, night, run-off-road, plus a severity index (M1 p. 1).

Statewide summary, 2021-2025 (M1 p. 1):

| System | Area | Total | Fatal | Non-fatal injury | Wet | Night | Run-off-road | Severity index |
|---|---|---|---|---|---|---|---|---|
| Interstates | Rural | 78.00 | 0.59 | 14.98 | 15.21 | 23.89 | 23.88 | 4.10 |
| Interstates | Urban | 132.70 | 0.53 | 26.19 | 22.70 | 33.19 | 23.09 | 3.37 |
| Interstates | Statewide | 116.48 | 0.55 | 22.87 | 20.48 | 30.44 | 23.33 | 3.52 |
| US routes | Rural | 112.06 | 1.17 | 28.31 | 17.34 | 37.37 | 31.63 | 5.37 |
| US routes | Urban | 284.30 | 1.27 | 71.79 | 39.62 | 62.19 | 30.35 | 3.90 |
| US routes | Statewide | 201.60 | 1.22 | 50.91 | 28.93 | 50.27 | 30.96 | 4.29 |
| NC routes | Rural | 166.30 | 1.88 | 43.53 | 21.62 | 59.39 | 52.62 | 5.80 |
| NC routes | Urban | 303.08 | 1.34 | 78.63 | 39.05 | 68.17 | 32.02 | 3.97 |
| NC routes | Statewide | 229.70 | 1.63 | 59.80 | 29.69 | 63.46 | 43.08 | 4.68 |
| Primary | Rural | 120.20 | 1.24 | 29.58 | 18.13 | 40.77 | 36.24 | 5.34 |
| Primary | Urban | 217.09 | 0.94 | 51.81 | 31.58 | 49.82 | 27.29 | 3.77 |
| Primary | Statewide | 176.02 | 1.07 | 42.39 | 25.88 | 45.98 | 31.08 | 4.22 |
| Secondary roads | Rural | 226.66 | 2.46 | 56.59 | 30.56 | 91.09 | 104.84 | 5.76 |
| Secondary roads | Urban | 317.65 | 1.35 | 83.83 | 41.71 | 76.48 | 53.09 | 4.10 |
| Secondary roads | Statewide | 285.36 | 1.74 | 74.16 | 37.76 | 81.67 | 71.45 | 4.57 |
| All system routes | Rural | 143.13 | 1.50 | 35.40 | 20.81 | 51.61 | 51.01 | 5.48 |
| All system routes | Urban | 244.09 | 1.05 | 60.41 | 34.30 | 56.98 | 34.22 | 3.88 |
| All system routes | Statewide | 203.02 | 1.23 | 50.23 | 28.81 | 54.79 | 41.05 | 4.34 |

By road type (M1 pp. 2-6; "*" = under 100 system miles, use with caution), total crash rate, 2021-2025:

| Road type | Rural US | Urban US | Rural NC | Urban NC | Rural primary | Urban primary | Rural secondary | Urban secondary |
|---|---|---|---|---|---|---|---|---|
| 2 lanes undivided | 155.72 | 313.09 | 179.34 | 264.58 | 171.11 | 281.26 | 226.48 | 263.54 |
| 2 lanes + TWLTL | 110.47* | 284.11* | 160.74* | 237.22* | 137.61* | 260.66* | 164.01* | 309.08* |
| 3 lanes undivided | 205.55* | 649.53* | 163.30* | 752.13* | 181.95* | 678.44* | 80.58* | 644.80* |
| 4+ lanes undivided | 184.33* | 601.41 | 230.20* | 573.57 | 197.50* | 588.98 | 304.93* | 516.49 |
| 4+ lanes + TWLTL | 140.65 | 328.56 | 114.98* | 325.00 | 130.63 | 327.35 | 124.03* | 459.48 |
| 4+ divided, no control of access | 98.00 | 347.20 | 110.65 | 295.65 | 101.08 | 326.98 | 299.25* | 359.64 |
| 4+ divided, partial control | 83.64 | 209.58 | 91.37* | 281.78* | 84.34 | 223.79 | 0.00* | 266.59* |
| 4+ divided, full control | 65.12 | 111.74 | 46.75* | 92.42* | 74.24 | 128.93 | 0.00* | 138.20* |
| Interstates (full control) | rural 78.00 | urban 132.70 | | | | | | |

(The fatal, non-fatal injury, wet, night and run-off-road columns for every row are in M1 pp. 2-6; this table copies
only the total-crash column.)

**Critical rate** (M5 slides 20-21, "Rate Quality Control Method", Poisson-based):
critical rate = average rate + K·√(average rate / exposure) + 1 / (2 · exposure), with K = 1.645 (95% confidence)
and the same exposure as above. (The square-root sign is lost in the PDF's text layer; the slide cites Khisty &
Lall, where the formula has it.) The comparison group is "other roads with similar characteristics (i.e. all urban
sections of 2-lane undivided US roads in the state)", which is the M1 table.

## Severity weighting (M1, M5)

- **Severity index** = (76.8 × (K + A) + 8.4 × (B + C) + PDO) / total crashes (M1 p. 1 note 2; worked example M5
  slide 7, where U crashes weigh 1 like PDO).
- Typical values: 8.4 marks "more severe" (M5 slide 4); the normal pedestrian-crash index is about 13.4 and bicycle
  about 11.3 (M5 slide 5). The statewide average is 4.34 for 2021-2025 (M1 p. 1).
- The HSIP warrants use the index as a threshold (e.g. I-3u: at least 6.5; I-3r: at least 9.0; M3 p. 7).

## Crash unit costs (M2, 2025 dollars)

Per crash, by worst injury in the crash, total crashes (M2 Table 1a, p. 1): **K $13,565,000; A $788,000;
B $263,000; C $153,000; PDO $15,100**; average crash $138,000; F+A $4,051,000; B+C $194,000.
Rural / urban (M2 Table 2, p. 1): K $13,646,000 / $13,443,000; A $792,000 / $782,000; B $255,000 / $269,000;
C $146,000 / $156,000; PDO $15,100 / $15,100.
Also per crash type (frontal impact, lane departure, rear end, pedestrian, bicycle, train, truck, animal; M2
Tables 1b-1i, pp. 1-4); e.g. frontal impact K $14,388,000, A $914,000, B $305,000, C $170,000, PDO $15,100.
Method (M2 Appendix pp. 5-6): FHWA *Crash Costs for Highway Safety Analysis* (2018) person-injury unit costs
(2010 $), CPI and median-weekly-earnings ratios to the current year, NC per-capita-income adjustment, then NC's
average injuries per crash by severity. Yearly memos from 1993 on (M9).
The CRF list (M6 p. 3) uses grouped **2024** costs per pattern for benefit-cost: e.g. total crashes F+A $4,129,000,
B+C $187,000, PDO $15,100 (M6 p. 9, rows 2.1.x).

## Network screening (M3)

NCDOT screens with **safety warrants**, not a critical-rate ranking: each potentially hazardous (PH) location must
meet at least one warrant, then is weighted by "crash frequency, target crash percentage, and severity" (M3 p. 1).
2026 results: 3,487 intersections, 825 sections, 1,178 non-motorist intersections, 42 non-motorist midblocks,
64 bridges (M3 p. 2). Data: reported crashes on public roads, **2021-2025 for 5-year warrants and 2016-2025 for
10-year warrants** (M3 p. 6). Examples (M3 pp. 6-10):

- I-1u frontal impact, urban, 5 years: ≥ 25% of crashes in the last 2 years AND (≥ 12 frontal impacts and ≥ 60%
  frontal) OR (≥ 35 crashes, ≥ 35% frontal, frontal severity index ≥ 6.0). (2024: 55%, M4 p. 6.)
- I-1r frontal impact, rural, 10 years: ≥ 9 frontal impacts, ≥ 20% in the last 3 years, ≥ 60% frontal.
- I-2u / I-2r last-year increase: ≥ 25 crashes and ≥ 40% in the last year (urban; 38% in 2024) / ≥ 20 and ≥ 32% (rural).
- I-3u / I-3r frequency with severity: ≥ 25 crashes, SI ≥ 6.5, ≥ 40% in last 2 years (urban; SI 6.0 in 2024) /
  ≥ 20 crashes, SI ≥ 9.0, ≥ 30% in last 3 years (rural). I-3: ≥ 3 K or A frontal-impact crashes in 5 years.
- I-4u / I-4r night: ≥ 12 night crashes and ≥ 45% at night (urban; 40% in 2024) / ≥ 10 and ≥ 46% (rural).
- Section warrants need, over 5 years, a minimum total and crashes per mile (M3 p. 8): freeway 30 / 30;
  US non-freeway 20 / 40; NC non-freeway 15 / 30; SR non-freeway 12 / 24; city non-freeway street 20 / 40; then
  F-1..F-4 (freeway) and N-1..N-4 (non-freeway) target-share warrants (run-off-road, wet, night; pp. 8-9).
  Animal crashes are removed from section warrants.
- BP-1 non-motorist intersection: ≥ 4 in 10 years with ≥ 50% in the last 5, or ≥ 3 in 5 years. MB-1 midblock:
  ≥ 4 non-intersection non-motorist crashes in 10 years. B-1 bridge: ≥ 5 run-off-road crashes in 10 years and
  ≥ 50% run-off-road, 2-lane roads only (pp. 9-10).

## Study rules (M3 pp. 3-5)

- Urban intersections: most recent **5 years**; rural intersections **10 years**; intersection **Y-line 150 ft**.
  Sections: 5 years, Y-line 0 ft, animal crashes deleted. Non-motorist: 10 years, Y-line 300 ft default.
  Bridges: 10 years, 500 ft from each end of the structure.
- Each analysis delivers a crash listing, location map, area map and collision diagram (filed in the HSIP Tracker).

## SPF / HSM calibration (M7)

Statewide calibration factors, 2020-2023, total crashes (M7 Chapter 4, report pp. 21-39 = PDF pp. 32-50):
R2U 1.365; R4D 1.461; R4U 0.996; U2U 2.194; U3T 1.531; U4D 3.023; U4U 3.690; U5T 1.396; U6D 1.091; U7D 1.361;
U8D 1.933; rural 4-lane freeway 1.381; urban freeway 4-lane 1.474, 6-lane 1.372, 8-lane 1.286; Rur2L-3ST 0.672;
Rur2L-4SG 0.831; Rur2L-4ST 0.733; RurML-3ST 0.824 (40 crashes, unreliable); RurML-4SG 0.499; RurML-4ST 1.321;
UrbArt-3SG 2.053; UrbArt-3ST 1.895; UrbArt-4SG 3.435; UrbArt-4ST 1.486; U68-4SG-2x2 2.327; rural roundabouts
1.969; urban roundabouts 2.300; entrance ramps 0.624; exit ramps 1.721; ramp terminals 1.907. Regional factors
(Coast / Piedmont / Mountain) for R2U, R4D, Rur2L-4SG, Rur2L-4ST and UrbArt-4SG are in the same chapter
(e.g. R2U 1.574 / 1.488 / 1.221). Factors are reported only where the sample had ≥ 100 observed crashes a year
(M7 p. 21). NCDOT points to national spreadsheet tools for predictive analysis (Safety Planning Resources page).

## CMF guidance (M6)

NCDOT publishes **CRFs** (CRF = 100 × (1 − CMF)) in 10 categories, chosen from the CMF Clearinghouse (downloaded
Dec 2021) and research; CRFs from any other source need approval of the CRF Committee (all Regional Traffic
Engineers + the Safety Evaluation Engineer) (M6 pp. 2-3). Each row gives target crashes, service life, maintenance
cost and the crash costs for the benefit-cost. Examples: two-way stop to single-lane roundabout, urban, injury
crashes 78% (2.1.1, p. 9); signal to single-lane roundabout, urban, injury 55% (2.1.4); left-turn lane at a
signalized 4-leg rural intersection, rear-end crashes 45% (3.1.4, p. 13); intersection lighting, nighttime fatal
crashes 77% (7.19.1A, p. 27).

## Required study forms

Not found as a numbered form. The HSIP analysis package is a crash listing, location map, area map and collision
diagram (M3 p. 3), with diagrams drawn per M8; field results go into the HSIP Tracker (M3 p. 5).

## Differences from California (Caltrans LRSM, TASAS, Caltrans crash costs)

California facts here are from the repo: `reports/Crash analysis industry methods.md` (LRSM v1.7/v1.8) and
`data/reference/crash_costs_ca.csv` (LRSM v1.8, May 2026, Appendix D p. 100, 2026 $).

1. **Rate unit and table:** NC publishes one statewide table a year, crashes per 100 MVMT for sections, by system
   (Interstate / US / NC / secondary), urban/rural and cross-section (M1). The LRSM uses per 100 MVMT for segments
   **and per million entering vehicles for intersections**; **NC publishes no intersection rate per MEV** (not found).
   CrashIQ's CA rate groups come from the Caltrans rate book; NC's equivalent is M1.
2. **Screening:** NC flags locations with pattern **warrants** that include recency tests (e.g. 25% of crashes in the
   last 2 years) and a severity index (M3). Caltrans' HSIP avoids rate-based ranking for lack of statewide volumes
   and uses 3-5 years of observed crashes (LRSM, per the repo report). NC's critical rate (K = 1.645) is a
   study-level check (M5).
3. **Severity weighting:** NC's EPDO weights are 76.8 (K+A), 8.4 (B+C), 1 (PDO and U) (M1 p. 1, M5 slide 7).
4. **Study periods:** urban intersections 5 years, rural intersections 10 years, non-motorist and bridges 10 years,
   intersection Y-line 150 ft (M3 p. 3). LRSM recommends at least 5 years of network-wide data.
5. **Crash costs:** NC prices each severity separately and also by crash type and urban/rural (M2): K $13,565,000,
   A $788,000, B $263,000, C $153,000, PDO $15,100 (2025 $). Caltrans LRSM v1.8 combines K and A by location type
   (KA $2,379,000 signalized intersection / $3,784,000 non-signalized / $3,276,000 roadway; B $213,000; C $121,000;
   O $20,000; 2026 $). CrashIQ's cost ranking needs a per-state cost table, not just new numbers.
6. **CMFs:** a state-approved CRF list with a committee gate for other sources (M6), instead of the LRSM's
   countermeasure table.
7. **HSM calibration:** NC has its own 2020-2023 calibration factors (M7), several far from 1 (UrbArt-4SG 3.435).
8. **Severity code U:** NC crash severity includes U (injury unknown), weighted like PDO in NC's severity index;
   CrashIQ prices CA's U at C (user decision, `crash_cost.py`). The NC pack needs its own rule.
