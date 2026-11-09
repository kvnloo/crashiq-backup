# New Jersey: shared-code fixes (for Hermes to merge centrally)

Worked around in `sources/nj_njdot.road()`; the shared fix would let every state's reader skip it.

1. `names.street_key` keeps `NJ 17` as `NJ 17`, while TIGER's `State Rte 17` becomes `SR 17`. Fix: map a leading 2-letter state code + number (`NJ 17`, `PA 611`) to `SR`. Test: `street_key("NJ 17") == street_key("State Rte 17")`.
2. County routes come as `MERCER COUNTY 622`, `CR 622`, `County Route 622` and `Co Rd 622`; `street_key` gives four different cores (`MERCER COUNTY 622`, `CR 622`, `COUNTY ROUTE 622`, `CO RD 622`). Fix: one `CR <n>` core for all four. Test: all four equal.
3. Not a code fix: NJ county routes 600+ aren't numbered on TIGER. Placing them needs NJDOT's Straight Line Diagram / LRS (SRI + milepost, on ~90% of NJ crashes): a route + milepost placer, as for NY.
