# Shared fixes found while building MN (not applied; Hermes merges centrally)

1. `names.street_key`: Minnesota route codes aren't known: `ISTH 94`, `USTH 169`, `MNTH 13`, `CSAH 81`, `CR 81`
   (and the OSM ref `MN 55`) stay literal, so they never match TIGER's `I- 94`, `US Hwy 169`, `State Hwy 13`, `Co Rd 81`.
   Worked around in `mn_mncrash.route_names`. Shared fix: map ISTH->I, USTH->US, MNTH/MN->SR, CSAH/CR/CNTY RD->CO RD.
   Test: `street_key("MNTH 13") == street_key("State Hwy 13")`, `street_key("CSAH 81") == street_key("Co Rd 81")`.
2. `names.street_key`: `I-35E` -> `I 35` but `SB I-35E` -> `I 35E` (the letter suffix is dropped only without a
   direction prefix). Worked around by stripping NB/SB/EB/WB in the reader. Test:
   `street_key("SB I-35E") == street_key("I-35E")`, and decide whether 35E/35W stay distinct (they are different roads).
