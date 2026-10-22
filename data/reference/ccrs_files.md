# CCRS file cache (#196)

**What:** some CCRS tables are published on data.ca.gov as a CSV file but are not loaded into the portal's query
service (`datastore_active = False`), so the app's SQL queries can't read them. Parties_2025 is the case today
(pain point 30). For a Parties or InjuredWitnessPassengers year in that state, the server downloads CHP's file once
and reads that year's rows from a local copy (user decision 2026-10-22, docs/03; proposal on #188). Crash tables are
always read from the datastore, because the pull's location filters need SQL.

**Where:** `data/cache/ccrs_files/<resource id>.sqlite` (gitignored; set `CRASHIQ_FILES_DIR` to move it). One file
per resource, holding only the columns CrashIQ reads (Collision Id, party number and type, at fault, movement, both
vehicle types, age, direction of travel), indexed by Collision Id, plus a `meta` table with the resource id, URL,
`last_modified`, download date and row count.

**Size (measured 2026-10-22):** Parties_2025 is a 211 MB download that takes under a minute. The copy holds 784,793
rows in 70 MB, including the index.

**When it downloads:**
- The first pull that needs the year starts the download in the background. That pull finishes without the year:
  the profile caveat says the file is being downloaded. Once the copy is there the cached pull counts as out of date,
  so the next view pulls again and the caveat clears. The pull log shows `parties_source` per year (`datastore` or
  `file_cache (date)`).
- CHP re-dates every file daily, so a copy is replaced only when it is a week old and the file's `last_modified` has
  changed. The old copy keeps answering until the new one is complete.
- If the download fails, the year stays missing with the caveat, the error is logged in the pull (`file_errors`),
  and the download is retried after an hour. A pull never fails because of it.
- Live data.ca.gov only. Tests and the offline demo never download. A harness that wants the fallback sets
  `app.state.ccrs_files` to a `FileCache`.
