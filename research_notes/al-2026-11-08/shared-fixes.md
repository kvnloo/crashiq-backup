# Shared fixes found by the Alabama build (not applied; for Hermes to merge centrally)

1. **Trailing single-letter quadrant is dropped by `names.street_key`.**
   - Checked 2026-11-08: `street_key("3rd Ave N") == street_key("3RD AVE S") == StreetKey(core='3RD', suffix='AVE')`.
   - Birmingham, AL repeats its numbered avenues and streets north and south (3rd Ave N / 3rd Ave S,
     11th St N / 11th St S). A name pair then "meets in more than one place", or lands on the twin intersection.
     In the Jefferson County sample, "4th Ave S & 15th St S" was auto-placed 11,594 ft off; auto-placed accuracy
     overall was 44%.
   - The #19 quadrant fix covers two-letter quadrants (NW/SE). Keep N/S/E/W as part of the key when the street is
     numbered (`^\d+(ST|ND|RD|TH)`) or when the network has both variants.
   - Test: `assert street_key("3rd Ave N") != street_key("3rd Ave S")` and
     `assert street_key("3rd Ave N") == street_key("3rd Avenue North")`.
2. **Interstate pairs written as one field** ("I-20/59 Northbound", "INTERSTATE 20/59 NORTH 114"): the key keeps only
   `I 20`. That's acceptable, but "I-20/59 & 115 EXIT RAMP" comes back as "missing street name". Ramp text in the
   cross street is the same issue as Kentucky's shared-fixes #2.
