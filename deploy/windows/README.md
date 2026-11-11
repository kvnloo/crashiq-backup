# Run CrashIQ on the home PC (free beta)

No Docker, no admin rights, no open router ports. The app runs as you on `127.0.0.1:8310`, starts when you log in and
restarts itself if it crashes. The public address `https://crash.aitransportationtools.com` comes from the one shared
Cloudflare Tunnel (trafficiq repo, `deploy/tunnel/README.md`). Same recipe as TrafficOpsIQ `deploy/windows`.

## Start or update
In PowerShell, in the checkout that serves the app:

```powershell
git pull
powershell -ExecutionPolicy Bypass -File deploy\windows\install.ps1
```

The first run asks you to **choose the beta password** (any user name works). It is kept in
`%LOCALAPPDATA%\crashiq\app.env`; to change it, edit that file and re-run the script.

## What's where
- Studies and caches: `%LOCALAPPDATA%\crashiq\data` (the same layout as `/var/data` in the Docker image, runbook-deploy.md).
  Caches download in the background the first time a study needs them. NAD address points: copy `nad_ca_r24.csv` to
  `data\cache\nad\` once.
- Log: `%LOCALAPPDATA%\crashiq\logs\server.log`. Task Scheduler → `CrashIQ`.
- Runtime AI stays off (#55): `run.py` drops `ANTHROPIC_API_KEY` and `TYPESAFE_API_KEY`, like the image.
- Second copy for testing: `install.ps1 -Port 8311 -TaskName CrashIQ_Test` (shares the data folder and password).
