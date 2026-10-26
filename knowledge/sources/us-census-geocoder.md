# US: Census Geocoder (batch address matching), US Census Bureau

**Where:** https://geocoding.geo.census.gov/geocoder/locations/addressbatch, benchmark `Public_AR_Current`. It's an
HTTP batch upload: a CSV of `id, street, city, state, zip`, at most 10,000 lines per file, no key, no login. It
returns `Match` (Exact / Non_Exact), `No_Match` or `Tie`, with a point interpolated along TIGER address ranges and
the TIGER line id and side.
**Licence:** US Government work, public domain. Commercial use OK. Terms: no guarantee of availability or accuracy.
**Used by:** Tester, #264 (2026-10-25; user-approved in the Tester session). Only address strings were sent; each
line's id was a sequence number made locally, never a crash record id.

## Quirks (with evidence)
- **Needs a city or a ZIP.** CCRS outside cities has the city "Unincorporated" and no ZIP, so those addresses mostly
  don't match. With the city blank, 62.6% of the accuracy pool outside cities matched; with "Unincorporated" it was
  0.1%. (#264)
- **Fast.** About 9,000 addresses a minute in one batch (2026-10-25).
