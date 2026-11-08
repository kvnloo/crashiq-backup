# Oklahoma: shared-code notes (for Hermes to merge centrally; nothing changed here)

No reader was built (gated state), so nothing here blocks a PR. These are what the Tulsa County placement sample
(`placement_sample.json`) showed `names.street_key` / `locate.place` would need for Oklahoma officer text:

1. **Travel direction after a route, in words or slashes**: "I-244 WESTBOUND", "SH-20 E/B", "US 75 S/B OFF RAMP",
   "US HIGHWAY 64 (EASTBOUND)". The base already drops a direction *before* a route (5df876e); one *after* it, or
   in parentheses, should be dropped too. Test: `street_key("I-244 WESTBOUND") == street_key("I-244")` and
   `street_key("US HIGHWAY 64 (EASTBOUND)") == street_key("US 64")`.
2. **A parenthesised second name** ("E 151ST S (ST HWY 67)", "COUNTY ROAD (161ST W AVE)"): try both names. The
   sample script does this as a wrapper (35 placements).
3. **Tulsa grid suffixes**: "71 ST. S." / "E 71ST ST" / "E. 71ST STREET" are one street; "S 116TH EA" is
   "S 116th East Ave". Test: `street_key("71 ST. S.") == street_key("E 71st St S")` (direction letters before and
   after the number name the same street in Tulsa's grid). Check against TIGER's FEATNAMES for 40143 before
   changing anything: the N/S twins are real different streets elsewhere (Birmingham note on #451).
