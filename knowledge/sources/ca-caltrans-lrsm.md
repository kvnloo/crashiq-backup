# California: Caltrans Local Roadway Safety Manual (LRSM)

**What:** Caltrans Division of Local Assistance's manual for local road owners: the HSIP countermeasures with their
crash reduction factors (Appendix B) and the benefit-cost method with the crash costs (Appendix D). Updated with each
HSIP call for projects.
**Where:** https://dot.ca.gov/-/media/dot-media/programs/local-assistance/documents/hsip/2026/lrsm2026final.pdf
(public, Caltrans).
**Version used:** **1.8, May 2026** (document footer dated 5/11/2026; server Last-Modified 2026-06-30). Downloaded
2026-11-01 by the Engineering session with the user's OK: 2,024,114 bytes, SHA-256
`d5ec1b7f270009ac4728c1497801960b53af8263f083d9fd2c1678a6396b5a7e`. Not stored in the repo.

## Crash costs (Appendix D, printed page 100 = PDF page 106)
The table under step 2 ("Annual benefit of project"); it has no table number. 2026 dollars ("Based on Table 7-1,
Highway Safety Manual (HSM), First Edition, 2010. Adjusted to 2026 Dollars."). Prices checked against the PDF by the
Tester (2026-11-01, docs/03 #335).

| Severity | Location type | Cost per crash |
|---|---|---|
| Fatality and Severe Injury Combined (KA) | Signalized Intersection | $2,379,000 |
| Fatality and Severe Injury Combined (KA) | Non-Signalized Intersection | $3,784,000 |
| Fatality and Severe Injury Combined (KA) | Roadway | $3,276,000 |
| Evident Injury – Other Visible (B) | any | $213,000 |
| Possible Injury – Complaint of Pain (C) | any | $121,000 |
| Property Damage Only (O) | any | $20,000 |

- Fatal and severe injury are one price by location type ("calculated based on an average Fatality (K) / Severe
  Injury (A) ratio for each area type"), combined since Cycle 7 "to reduce the possibility of selecting an improvement
  project on the basis of randomness".
- There's no price for an injury crash with the level not stated (CCRS U), and no rule for unknown intersection
  control.

## Use in CrashIQ (#273; user decisions 2026-10-25 and 2026-11-01, docs/03)
- `data/reference/crash_costs_ca.csv` holds the six prices; `backend/crashiq/crash_cost.py` prices each crash once
  at its KABCO level: K and A at the KA price of the location type (segment = Roadway; signal = Signalized; stop,
  yield, roundabout = Non-Signalized). U is priced at C. A KA crash at an intersection with unknown control takes the
  Signalized price (the lower one) and the location is marked "control unknown".
- T2's `crash_cost` column and tab 3's "Crash cost" ranking; the count ranking stays the default.
- Later: the HSIP B/C (Appendix D's method with Appendix B's CRFs, the HSIP Analyzer) is out of scope (P2).

## Updates
Caltrans republishes the LRSM before each HSIP cycle and updates Appendix D's costs each time (versions 1.4–1.8).
Replace the CSV, this note and the download details together.
