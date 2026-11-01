# California crash costs (`crash_costs_ca.csv`): state-pack data (#19)

Source note: `knowledge/sources/ca-caltrans-lrsm.md`.

Cost per crash by KABCO severity and location type, for ranking locations by crash cost (#273; user decision
2026-10-25, docs/03 "Ranking by crash cost"). The same basis as the HSIP benefit-cost calculation.

## Source
- **Caltrans, Local Roadway Safety Manual (LRSM), Version 1.8, May 2026**, Appendix D "Benefit Cost Ratio (BCR)
  Calculations", the crash-cost table under step 2 ("Annual benefit of project"; the table has no number), printed
  page 100 (PDF page 106; footer "5/11/2026 … Page | 100").
- URL: https://dot.ca.gov/-/media/dot-media/programs/local-assistance/documents/hsip/2026/lrsm2026final.pdf
  (Last-Modified 2026-06-30; 2,024,114 bytes; SHA-256 d5ec1b7f270009ac4728c1497801960b53af8263f083d9fd2c1678a6396b5a7e),
  downloaded 2026-11-01 by the Engineering session with the user's OK. Not stored in the repo.
- Values copied from the document's text (pdftotext), not typed from memory. Dollars: "Based on Table 7-1, Highway
  Safety Manual (HSM), First Edition, 2010. Adjusted to 2026 Dollars." (the table's footnote).

| LRSM row | Severity | Location type | Cost |
|---|---|---|---|
| 3 | Fatality and Severe Injury Combined (KA) | Signalized Intersection | $2,379,000 |
| 3 | Fatality and Severe Injury Combined (KA) | Non-Signalized Intersection | $3,784,000 |
| 3 | Fatality and Severe Injury Combined (KA) | Roadway | $3,276,000 |
| 2 | Evident Injury – Other Visible (B) | any | $213,000 |
| 1 | Possible Injury – Complaint of Pain (C) | any | $121,000 |
| 0 | Property Damage Only (O) | any | $20,000 |

The LRSM combines fatal and severe injury (K and A) at one price per location type ("Figures were calculated based on
an average Fatality (K) / Severe Injury (A) ratio for each area type").

## How CrashIQ applies it (`backend/crashiq/crash_cost.py`)
- Each crash once, at its KABCO level. K and A take the KA price of the crash's location type: a segment crash
  `roadway`; an intersection with a signal `signalized_intersection`; with a stop sign `non_signalized_intersection`.
- **Not in the LRSM, decided by the user (2026-11-01, Engineering session, #273):**
  - an injury crash with the level not stated (U) is priced at C, and the U count is shown beside the cost;
  - a KA crash at an intersection whose control isn't known (no OSM signal or stop tag) takes the signalized price
    (the lower one), and the location is marked "control unknown";
  - stop, yield and roundabout control count as non-signalized (PM, 2026-11-01; recorded in docs/03 #335).
- Update: replace the table when Caltrans publishes a new LRSM, with the new edition, page and download date here.
