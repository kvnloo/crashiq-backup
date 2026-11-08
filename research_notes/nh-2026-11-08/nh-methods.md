# New Hampshire methods (NHDOT), checked 2026-11-08

No pack, so no `methods_nh.json`. What NHDOT's documents say, for when an export arrives.

| Item | Value | Source | Verified |
|---|---|---|---|
| Crash cost, fatal (K) | $13.6 million per crash (2021 $) | NHDOT HSIP Implementation Plan, final 2025, https://www.dot.nh.gov/sites/g/files/ehbemt811/files/inline-documents/nhdot_hsip_implementationplan_final_2025_1.pdf (page not recorded) | no (403 to scripted download; text via search extract) |
| Crash cost, suspected serious injury (A) | $737,900 per crash (2021 $) | same | no |
| Crash cost, fatal + injury average (KABC) | $582,125 | same | no |
| Crash cost, PDO (O) | $8,623 | same | no |
| Crash cost, B and C separately | missing: not in the text read | | |
| Cost basis | "NHDOT received technical assistance from FHWA to update their average crash costs" | same | no |
| Benefit-cost | HSM Part D; CMFs from the HSM and the CMF Clearinghouse; initial B/C of at least 2.0 | HSIP 2021 Annual Report: New Hampshire, https://highways.dot.gov/sites/fhwa.dot.gov/files/2021_NH_HSIP_Report.pdf | no |
| Screening | high crash (fatal and serious injury) or high risk (systemic) locations | NHDOT HSIP Manual and Guidance (Dec 2013), https://www.dot.nh.gov/sites/g/files/ehbemt811/files/inline-documents/hsip-nh-guidance-12-2013.pdf, as summarised by FHWA's Noteworthy Practices | no |
| Crash rates by facility | missing: no NHDOT statewide average crash-rate table found | | |
| Critical-rate method | missing | | |

Differences from California: NH prices crashes by severity with its own FHWA-assisted table (2021 $) where Caltrans
uses its own; NH screens on fatal + serious injury (KA) crashes. No statewide base rates found.

`~/.hermes/state-manuals/nh/` is empty: dot.nh.gov returns 403 (Akamai) to curl, even with a browser user agent.
Save the two NHDOT PDFs from a browser to verify the values and record their pages and sha256.
