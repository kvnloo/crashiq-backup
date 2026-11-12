# Runbook: the CrashIQ container (#383)

One Docker service (docs/03 R8): the API and the built app on `$PORT`, the same as `make serve`. **Render is dropped
(user, 2026-11-10, #395):** the free beta runs on the home PC (section "Free beta" below); the Render parts are kept
only as the container reference.

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

## Free beta: the home PC + Cloudflare Tunnel (decided 2026-11-10, #395)
The beta runs on the user's always-on Windows PC. No Docker: the server runs straight from a checkout of `main`, with
its own data folder (never a dev session's `data/`, CLAUDE.md Isolation). Cloudflare Tunnel gives it
`https://crash.aitransportationtools.com` with no open ports.
1. A checkout only the beta uses: `git worktree add C:/Users/aksha/Workspace/repos/Crash-beta origin/main`, then in it
   `make setup && make build`. To update: `git -C .../Crash-beta pull --ff-only origin main && make build`, then restart.
2. Start it (Git Bash; the user types the password, it isn't written in any file):
   ```bash
   cd C:/Users/aksha/Workspace/repos/Crash-beta
   D=C:/Users/aksha/Workspace/data/crashiq-beta
   read -s -p 'Password: ' APP_PASSWORD; export APP_PASSWORD
   CRASHIQ_HOSTED=1 HOST=127.0.0.1 PORT=8090 CRASHIQ_DB=$D/crashiq.sqlite \
     CRASHIQ_FILES_DIR=$D/cache/ccrs_files CRASHIQ_TIGER_DIR=$D/cache/tiger CRASHIQ_NAD_DIR=$D/cache/nad \
     CRASHIQ_ADDRFEAT_DIR=$D/cache/tiger_addrfeat CRASHIQ_POSTMILE_DIR=$D/cache/postmiles CRASHIQ_AADT_DIR=$D/cache/aadt \
     PYTHONPATH=backend .venv/Scripts/python -m crashiq.server
   ```
   `HOST=127.0.0.1` keeps it off the home network: only the tunnel reaches it. Copy the NAD extract to
   `$D/cache/nad/nad_ca_r24.csv` once (the PC already has it locally, so no upload).
3. Tunnel (once): `winget install --id Cloudflare.cloudflared -e`, then `cloudflared tunnel login` (the user clicks
   Allow in the browser and picks `aitransportationtools.com`), `cloudflared tunnel create crashiq-beta`,
   `cloudflared tunnel route dns crashiq-beta crash.aitransportationtools.com`, and run it with
   `cloudflared tunnel run --url http://127.0.0.1:8090 crashiq-beta`. `cloudflared service install` makes it start
   with Windows.
4. Check from a phone off Wi-Fi: `https://crash.aitransportationtools.com/api/health` answers, every other page asks
   for the password. Then the userflow check below with `CRASHIQ_URL=https://crash.aitransportationtools.com`.
5. Limits: the beta is down when the PC sleeps, restarts or loses power; set Windows power to never sleep. Back up
   `$D/crashiq.sqlite` with the `sqlite3 backup` line under "Back up the disk".

## One server (option 2: CrashIQ + our own Overpass + HTTPS)
**Decided as the move once people pay (#395).** Until then the beta runs on the home PC (above).

`deploy/docker-compose.yml` runs three containers on one Linux server with Docker (e.g. Hetzner CX33: 4 CPU, 8 GB,
80 GB disk). Sizes measured 2026-11-03 on Southern California: Overpass load 27 min, 5.1 GB disk, 2.6 GB peak RAM;
CrashIQ peaked at 1.4 GB over three studies. All of California should be roughly twice the Overpass load and disk.
1. On the server, as a non-root user with Docker: `git clone https://github.com/redhawkliger/crashiq.git && cd crashiq`.
2. Create `deploy/.env` **on the server only** (it's in `.gitignore`):
   ```
   APP_PASSWORD=<chosen by the user, typed on the server>
   CRASHIQ_DOMAIN=<your domain, or the server IP with dashes + .sslip.io, e.g. 203-0-113-7.sslip.io>
   ```
3. `docker compose -f deploy/docker-compose.yml up -d --build`. CrashIQ is up at once on `https://$CRASHIQ_DOMAIN`
   (Caddy gets the certificate). Until Overpass finishes its first load (estimated about an hour for California; Southern California took 27 min), corridors use
   the public Overpass as before.
4. Check: `docker compose -f deploy/docker-compose.yml logs overpass | tail` shows the dispatcher started; then
   `docker compose -f deploy/docker-compose.yml exec crashiq python -c "import urllib.request,urllib.parse;print(urllib.request.urlopen('http://overpass/api/interpreter',urllib.parse.urlencode({'data':'[out:json];node(34,-118.3,34.001,-118.299);out 1;'}).encode()).read()[:80])"`.
5. Update: `git pull && docker compose -f deploy/docker-compose.yml up -d --build crashiq`. Overpass applies
   Geofabrik's daily changes by itself.
6. Firewall: open 22, 80, 443 only. Overpass has no public port.

End-to-end check with our Overpass (`tests/screen/userflow.mjs`, see Checks), 2026-11-03: Crenshaw (drawn on the
map), Sherman Way and Camino Capistrano all pass; corridor step 1 s, profile 51–88 s on an empty disk, both files download.

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
