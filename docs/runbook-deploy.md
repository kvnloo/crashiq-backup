# Runbook: the CrashIQ container (#383)

One Docker service (docs/03 R8): the API and the built app on `$PORT`, the same as `make serve`. Render runs it from
`render.yaml` with a persistent disk at `/var/data`. Deploying to Render (part B) waits for the user, who signs in and
approves the cost.

## Build and run locally
Needs a container tool: Colima on this Mac (decision #384, 2026-11-03): `brew install colima docker docker-buildx`,
then `colima start`.
```bash
docker build -t crashiq .
```
```bash
docker run --rm -p 8001:8000 -e APP_PASSWORD -v crashiq-data:/var/data crashiq
```
- `-e APP_PASSWORD` passes the password from your shell. Type it in the shell yourself: it isn't written in any file.
- Without `APP_PASSWORD` the container stops at once. The image sets `CRASHIQ_HOSTED=1`, so the app fails closed.
- `/api/health` answers without a password, for the host's health check. Everything else asks for it, including the
  app's pages (the browser shows a sign-in box; any user name works).
- A new named volume is an empty disk. The app creates `crashiq.sqlite` on first start.

## Environment variables
| Variable | Where | Value |
|---|---|---|
| `APP_PASSWORD` | Render dashboard (`sync: false`), or `-e` locally | Set by the user. Never committed. |
| `PORT` | Render sets it | The image defaults to 8000. |
| `CRASHIQ_HOSTED` | Image | `1`: refuse to start without `APP_PASSWORD`. |
| `CRASHIQ_DB`, `CRASHIQ_*_DIR` | Image | All under `/var/data` (the disk). |

Not set, so runtime AI stays off (#55): `ANTHROPIC_API_KEY`, `TYPESAFE_API_KEY`. `CRASHIQ_FIXTURES_DIR` is for offline
demos only and is never set in the image.

## What's on the disk
Everything the app writes is under `/var/data`:
- `crashiq.sqlite`: the studies.
- `cache/`: public data, downloaded in the background the first time a study needs it, each from its own source:
  - TIGER/Line roads (census.gov);
  - CCRS extra files (data.ca.gov);
  - Caltrans postmiles (Caltrans GIS);
  - Traffic Census AADT workbooks (dot.ca.gov).
  OpenStreetMap streets come from Overpass for each study.
- Address data for house-address crashes (decision #384 (b), 2026-11-03):
  - **TIGER ADDRFEAT** address ranges (census.gov) download per county, in the background, the first time a crash in
    that county needs one (Los Angeles, the largest, is 26 MB). Until a county's file lands, its house-address crashes go to review
    without the suggestion, and the next study uses it. A failed download is retried after an hour.
  - **NAD address points**: uploaded once by hand (426 MB). Copy the California extract `nad_ca_r24.csv` to
    `/var/data/cache/nad/nad_ca_r24.csv` on the disk (Render Shell / `render ssh` + `scp`). The app builds its index
    from it on first use. Without it, house-address crashes NAD would place go to review with the ADDRFEAT suggestion.

The image holds no data except the committed tables in `data/reference/` and `data/aliases/`. `.dockerignore` keeps out
`data/`, SQLite files, `.env`, `node_modules` and caches.

## Back up the disk
- Render takes daily snapshots of a persistent disk; restore one from the service's Disks tab.
- For your own copy, open the service's Shell and make a consistent copy of the database while the app runs. Then
  download it from the Shell, or with `render ssh` and `scp`:
  ```bash
  python -c "import sqlite3; s=sqlite3.connect('/var/data/crashiq.sqlite'); s.backup(sqlite3.connect('/var/data/backup.sqlite'))"
  ```
- The caches don't need a backup: they are downloaded again when needed.

## Checks
- `make test` covers, with no network (`tests/test_deploy.py`):
  - failing closed without a password;
  - an empty disk;
  - every route except `/api/health` needing the password;
  - the image and blueprint files;
  - OSM attribution.
- `docker build` from a fresh clone, and a container on an empty volume, are run by hand: the commands above, then
  `python backend/scripts/container_smoke.py` (auth, first study, both exports, with times).
- End-to-end check (Setup → draw on the map → profile → findings → PDF + XLSX), against any running copy:
  `cd tests/screen && npm ci && APP_PASSWORD=... node userflow.mjs` (`CRASHIQ_URL=https://...` for a server; default :8001).
