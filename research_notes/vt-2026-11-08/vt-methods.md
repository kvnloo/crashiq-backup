# Vermont: study methods (Hermes, 2026-11-08)

Manuals in `~/.hermes/state-manuals/vt/` (sha256 in `data/reference/methods_vt.json`).

## Crash costs: missing
VTrans' High Crash Location Report 2012-2016 (PDF p. 12) prices a Severity Index with NSC 2014 economic costs: each
person killed $1,500,000, each person injured $88,500, each PDO crash $11,300. They are per person, and the public
crash layer has no people counts, so they can't be applied per crash. They are also economic, not comprehensive.
Not used; no Caltrans or FHWA substitute.

## Statewide average rates: missing
"Summary Statewide Average Crash Rate 2012-2016" (1 page) gives rates by functional class (e.g. urban principal
arterial 5.1796 crashes per MVM). Not loaded: 2012-2016 only, and CrashIQ has no Vermont AADT or functional class.

## Screening: HSM critical rate (national), Vermont's method noted
VTrans' High Crash Location method (HCL Report 2012-2016, PDF pp. 10-11): a section or intersection with 5 or more
crashes in 5 years and an Actual/Critical rate ratio of 1.000 or more, the critical rate built on the statewide
average for its functional class with K = 2.58. Not built (needs the statewide rates and AADT); CrashIQ uses the HSM
critical rate against the corridor's own sites (HSM 1st ed., Ch. 4, Sec. 4.2.3), as in every state.

## Minimum years: missing
VTrans states no minimum. Its HCL period is "Typically … 5 except where Roadway Improvements have occurred" (HCL
Report 2012-2016, PDF p. 12).

## SPF calibration: missing
No Vermont calibration factors found. The SHSP 2022-2026 (downloaded) sets goals, not methods.
