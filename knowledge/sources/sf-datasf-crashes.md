# San Francisco: DataSF "Traffic Crashes Resulting in Injury" (ubvf-ztfx)

**Where:** `https://data.sf.gov/resource/ubvf-ztfx.json` (Socrata; the old data.sfgov.org host redirects).
2005 to ~2 months ago, ~3,000 injury crashes/yr, 66k rows total. Injury crashes only (no PDO).
**Fields we use:** `case_id_pkey`, `tb_latitude`, `tb_longitude`, `primary_rd`, `secondary_rd`, `distance`,
`direction`, `cnn_intrsctn_fkey`, `geocode_source` ("SFPD-INTERIM DB").

## Why it matters
- **Joins to CCRS exactly:** CCRS `Report Number` == DataSF `case_id_pkey` for SFPD reports (NCIC 3801).
  5,309 unique linked crashes for 2023–24 after hygiene. This is the ground truth for city-street placement.
- **It's also a cheaper placement method:** for SF injury crashes we can take SFPD's own coordinates by report
  number and skip name-matching. Check other cities for the same (LA's open data has LAPD collisions with
  coordinates; to verify). → generic tier: "agency open-data join, before name-matching".

## Quirks
- **Default/parking points.** Some records sit at a shared point with street names unrelated to the CCRS record
  (e.g. many at "07TH ST / TOWNSEND ST"). Drop truth whose streets don't resemble the CCRS streets
  (similarity < 0.75 on every pair). 14–15 of ~5,300 dropped.
- **Address crashes are approximated:** "1677 Geneva Ave" becomes "Geneva Ave & Prague St, 630 ft East". So
  DataSF is NOT exact truth for address-based reports; our OSM address point can be more accurate than it.
- Some `primary_rd == secondary_rd` rows (e.g. BAY ST / BAY ST): weak truth.
- Street names are zero-padded (`07TH ST`) and use full forms (`BAY SHORE BLVD`).
