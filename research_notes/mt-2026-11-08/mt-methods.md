# Montana methods (rates, costs, screening), 2026-11-08

Files kept in `~/.hermes/state-manuals/mt/`.

| Value | Montana | Source | In CrashIQ |
|---|---|---|---|
| Crash costs per crash | K $6,168,300 · A $326,400 · B $119,200 · C $67,100 · O $10,800 (ePDO weights 571.14 / 30.22 / 11.04 / 6.21 / 1) | Numetric Help Center, "MTD - Crash Injury Severity (KABCO) Rankings", 2025-02-05: "Montana Department of Transportation default … costs that are used in AASHTOWare Safety" (`numetric_mdt_kabco_costs_2025-02-05.html`, sha256 793a336b…) | `verified: false`: a vendor's page, not an MDT document, and no dollar year. Not printed. |
| Statewide average crash rates | not found | MDT publishes yearly crash summaries by county/city, not rate tables by facility type | missing |
| Screening | Montana-specific SPFs and Level of Service of Safety (Roadway Departure Study, Intersection Safety Study) | FHWA HSIP reports for Montana 2022-2025 (section "Does the State use the HSM…"); the reports also say "MDT's Safety Program has a safety manual used by Safety Staff. This is an internal document." | HSM critical rate against the corridor's own sites (national method, user's decision) |
| Minimum years | not found | the internal Safety Manual | missing |
| SPF calibration | not published | internal | missing |
| Benefit-cost | B/C ≥ FHWA threshold; evaluation of projects with CN+CE > $100,000 | HSIP reports (as above) | not used |

The FHWA HSIP report PDFs (highways.dot.gov) refuse scripted downloads (HTTP 403, Akamai), so they were read through
the search engine's extract only and are not stored; page numbers are not cited for them.

Differences from California: no TASAS-style base rates; costs are per crash by KABCO level (no location-type split);
MDT's own network screening is SPF/LOSS-based and internal.

## What the user should ask MDT (Traffic and Safety Bureau)

1. The crash unit costs MDT uses for HSIP benefit-cost, with their dollar year (to replace the vendor figure).
2. Whether the Safety Manual (internal) can be shared, for minimum years and the screening thresholds.
