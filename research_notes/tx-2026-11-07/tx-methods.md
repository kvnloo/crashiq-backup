# Texas: official safety and crash-analysis methods (Hermes, 2026-11-07)

PDFs downloaded 2026-11-07 to `~/.hermes/cache/scratch/states/tx/manuals/` (not committed). Page numbers are the
printed page numbers, with the PDF page in brackets. Numbers are copied from the manuals; "not found" means I looked in
these documents and did not find it.

## Manuals

| # | Title | Edition / date | URL |
|---|---|---|---|
| M1 | 2026 HSIP Guidelines (TxDOT Traffic Safety Division) | 2026 program call, 78 pp | https://www.txdot.gov/content/dam/docs/division/trf/highway-safety-engineering/hsip-guidance-program.pdf |
| M2 | 2026 Highway Safety Improvement Program Webinar Slides | 2026 | https://www.txdot.gov/content/dam/docs/division/trf/highway-safety-engineering/2026-hsip-webinar-slides.pdf |
| M3 | Traffic and Safety Analysis Procedures Manual (TSAP, TxDOT Design Division) | June 2024, effective 2024-06-21, 633 pp | https://www.txdot.gov/content/dam/txdotoms/des/tsp/tsp.pdf (HTML: https://www.txdot.gov/manuals/des/tsp/index.html) |
| M4 | Statewide Traffic Crash Rates 2024 (Texas Motor Vehicle Crash Statistics) | data as of 2025-04-09, 1 p | https://www.txdot.gov/content/dam/docs/division/trf/crash-records/2024/02.pdf |
| M5 | TTI 0-7083-R1, Calibrating the HSM Predictive Methods for Texas Highways: Technical Report | FHWA/TX-23/0-7083-R1 | https://library.ctr.utexas.edu/hostedpdfs/tti/0-7083-r1.pdf |
| M6 | TTI 5-7083-01-R1, Implementation of Safety Prediction Methods for Texas Highways (updated calibration) | FHWA/TX-24/5-7083-01-R1 | https://library.ctr.utexas.edu/hostedpdfs/tti/5-7083-01-R1.pdf |
| M7 | CRIS Automated Interface User Guide, Public and Standard Extracts | v29.0 | https://www.txdot.gov/content/dam/docs/division/trf/crash-records/automated-interface-guide-for-public-and-standard-extracts-v29.pdf |

Not downloaded: FHWA's Texas 2025 HSIP report (highways.dot.gov returned 403 to the script).

## Crash rates: formula and exposure units (M3)

- Segment: R = C × 100,000,000 / (L × V × N × 365), crashes per 100 million vehicle miles (MVMT); C crashes in the
  study period, V daily traffic, L miles, N years (M3 p. 6-4 [113]). Worked example: 2 mi, 20,000 ADT, 50 crashes
  2016–2020 → 68.5 per 100 MVMT (p. 6-5 [114]).
- Intersection: R = C × 1,000,000 / (V × N × 365), crashes per million entering vehicles (MEV), V = daily entering
  volume (p. 6-4 [113]; again p. 10-25 [202], "typically three to five years of data").
- Rates are computed for total, fatal, injury and/or fatal+injury crashes and compared with the statewide average
  for similar facility types (p. 6-4). Threshold as written: "significantly higher than the statewide average (more
  than five crashes per million entering vehicles for intersections or 5 crashes per 100 million vehicle miles of
  travel for segments)" (p. 6-4). The wording is ambiguous (an absolute 5, or 5 above the average); ask TxDOT.

## Statewide average rates (M4, 2024, crashes per 100 MVMT, all severities)

| By highway system | Rural | Urban |
|---|---|---|
| Interstate | 52.59 | 152.18 |
| US Highway | 69.39 | 181.37 |
| State Highway | 94.00 | 215.41 |
| Farm-to-Market | 121.15 | 260.52 |

| By road type | Rural | Urban |
|---|---|---|
| 2 lane, 2 way | 100.46 | 224.19 |
| 4 or more lanes, divided | 57.92 | 162.90 |
| 4 or more lanes, undivided | 105.15 | 319.64 |

The same one-page table exists for every year (e.g. `.../crash-records/2020/02.pdf`, `.../2019/02.pdf`). M3's
Table 6-2 (p. 6-5) shows how it's used: a corridor's yearly rate next to the statewide average by road type and by
highway system. **Not found:** statewide average intersection rates per MEV, rates by severity (F+I), city-street or
county-road rates, and a critical-rate formula. M3 Table 10-8 (p. 10-25) names "comparison of project crash rates with
the state-wide critical rates" but no formula or table for them appears in M3.

## Years of data (M3 p. 6-2 to 6-3 [111–112], Table 6-1)

Standard historical analysis: the most recent 5 complete calendar years. Minimum 3 (recent construction, land-use
change, before/after study). 8 years for rural areas with few crashes, detailed bicycle/pedestrian analysis, or
commercial-vehicle analysis. Less than 3 needs the TxDOT project manager's pre-approval. HSIP uses exactly the last 3
calendar years (2022–2024 for the 2026 call) (M1 p. 28 [29]).

## Crash costs (M1 p. 28 [29])

"For the 2026 HSIP Program Call, the cost per crash will be $4,290,000 for K or A crashes and $360,000 for B crashes.
Only preventable KAB crashes from years 2022-2024 ... are used." Based on National Safety Council comprehensive costs
(M1 Table 2, p. 15 [16]). C and O crashes have no cost (they don't enter the SII). Change log: costs updated 2022
(M1 p. 77 [78]). The 2021 edition's values ($3,700,000 K/A, $520,000 B) appear only in search snippets; that file is
no longer on ftp.txdot.gov (404).

## Severity weighting and screening

- KABCO is TxDOT's scale (M3 §5.2.1, PDF p. 90).
- HSIP screening: districts get On-System KA crash reports (by control-section, on curves, rural 4-lane undivided
  without paved shoulders, work code 541 rural 2-lane < 24 ft and ≥ 400 ADT, pedestrian KA); B crashes enter the SII
  but "for screening purposes only" K and A count (M1 p. 28 [29]). Systemic and annual-priority approaches rank by
  crash history, volume, functional class, speed, curve advisory speed, geometry (M1 §Project Identification).
- Benefit/cost: Safety Improvement Index (SII) = present worth of preventable crash-cost savings over the service life
  ÷ construction cost; S = annual savings from R (reduction factor), F (preventable K+A crashes), Cf, I (preventable B),
  Ci, Y (years of data), minus M (maintenance change); traffic growth Aa/Ab and service life L adjust it (variables
  M1 p. 15 [16]; the formula itself is an image there). SII ≥ 1.0 is cost-effective (p. 17 [18]); SII < 3.0 projects
  are "medium/high risk" if estimates rise (M2).
- Network screening (HSM Part B): M3 §5.3.3 (p. 5-7 [95]) describes HSM network screening; no TxDOT-specific screening
  performance measure (e.g. excess expected crashes) was found.

## CMFs / reduction factors

- HSIP: TxDOT's own reduction factors per work code, M1 Appendix B (p. 30 onward) and the summary table p. 51 [52].
  Examples: 101 Install warning/guide signs 20%, 15 yr; 107 Install traffic signal 20%, 10 yr (M2 says rural 35% vs
  urban 20% from new research); 109 LPI 16%; 110 Install pedestrian signal 34%; 115 Ped countdown 50%;
  201 Install median barrier 50%, 25 yr (p. 38 [39]); 502 Widen lanes 15%, 20 yr (p. 43 [44]). Each code has
  "preventable crash" criteria in CRIS codes (Appendix C, p. 60).
- Project analysis: CMF Clearinghouse, "only CMFs with a star rating of three or higher may be used"; lower needs the
  TxDOT project manager's acceptance; record CMF ID and stars (M3 §5.4.3, p. 5-18 [106]).

## SPF / HSM calibration factors (M5, M6)

Texas local calibration factors exist for HSM Ch. 10, 11, 12, 18 and by region (M3 App. G §6). Examples (M5
Table 49, p. 90 [107], segments): R2U 0.82, R4D 0.91, R4U 0.69, U2U MV 0.94 / SV 1.10, U3T MV 0.61 / SV 1.48,
U4D MV 1.67 / SV 1.97, U4U MV 1.34 / SV 1.5, U5T MV 0.50 / SV 0.74. Intersections (Table 52, p. 96 [113]): rural
two-lane 3ST 0.62, 4ST 0.64, 4SG 0.58; rural multilane 3ST 0.71, 4ST 0.75, 4SG 0.29; urban 3ST-MV 0.45, 3ST-SV 0.16,
4ST-MV 0.47, 4ST-SV 0.23 (rest of the table not copied). M6 Table 7 updates driveway-related MV factors: U2U 1.30,
U3T 0.99, U4D 2.08, U4U 0.96, U5T 0.92.

## Required study forms (M3 appendices)

Scoping Form (App. B §1), Field Visit Checklist (App. C §1), Intersection Analysis Checklist (K-19), Crash Diagram
Template (App. K §9, p. K-41), Example Crash Data Summary (App. G §4), Interchange Analysis Checklist (L-2), TIA
Quality Control Checklist (Q-2). HSIP: the HSIP Project Submission file with the SII calculator (M1 p. 1 [2]).

## Differences from California (CrashIQ's current pack)

1. Rates: TxDOT publishes one statewide average per highway system or road type (rural/urban, all severities, per
   100 MVMT); Caltrans TASAS base rates are per facility type with separate total and F+I rates, and for
   intersections per MEV. No Texas intersection base rates or critical-rate method found.
2. Crash costs: TX prices only K/A ($4.29M, one price for both, no location type) and B ($360k); Caltrans LRSM v1.8
   prices KA by location type (signalized $2.379M, non-signalized $3.784M, roadway $3.276M), B $213k, C $121k,
   O $20k (data/reference/crash_costs_ca.csv).
3. B/C: TX uses the SII with TxDOT work-code reduction factors and 3 years of preventable KAB crashes; CA uses the LRSM
   BCR with LRSM CRFs.
4. Study period: TX recommends 5 years (min 3, 8 for sparse/VRU/CMV studies).
5. SPF calibration: TX has published local calibration factors (by region too); CrashIQ has none for CA.
6. Reportability: the extract flags TxDOT-reportable crashes (`Txdot_Rptable_Fl`, "occurred on a trafficway and resulted in ...") and "$1,000 Damage to any One Person's Property" (
   `Thousand_Damage_Fl`); filter on these before comparing counts with CA.
