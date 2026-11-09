# Shared fixes Colorado would use (not made on this branch)

## 1. Block numbers in CDOT's street fields
CDOT writes a block or house number into either street field: "2946 ARAPAHOE ST" & "29TH ST", "100 BLOCK S QUITMAN
ST" & "W BAYAUD AVE", "WELTON ST" & "1400 BLK". In the Denver 2024 sample "missing street name" (15 of 2,000) is all
"<n> BLK" as Location 2, and house-numbered Location 1 placed 344-411 ft off. Fix in `names.street_key` (or a
pre-split in the core): strip a leading "<n> BLOCK|BLK " and a leading house number before keying; treat a bare
"<n> BLK" secondary as an address on the primary (the D5 house-address path). Test: `street_key("100 BLOCK S QUITMAN
ST") == street_key("S QUITMAN ST")`. The reader passes CDOT's text as reported, per the contract.

## 2. Ramp and freeway forms
"I-70 WB ON RAMP", "I-25 NB/SB RAMP SPLIT", "I70 HWY_EB", "PENA BLVD NB OFF RAMP": 251 of 2,000 pairs had "no
intersection of the two named streets", most with a ramp or freeway name. GPS places these (98% of rows have it).

## 3. `study.default_window` doesn't clamp to `pack.first_year`
Would hit Colorado: `first_year` is 2021 (the layout read), and with the default 18-month lag the window on
2026-11-08 is 2020-2024, so creating a study without years fails ("CDOT crash listing crash data starts in 2021").
Worked around in the pack with `final_lag_months=10` (CDOT called 2025 "considered complete" on 2026-07-23), so the
default is 2021-2025. Same as Arkansas's shared-fixes #4. Fix: `from_ = max(to - DEFAULT_YEARS + 1, pack.first_year)`.
