"""Keeps the CrashIQ server up on this PC (started at logon by install.ps1).

Reads APP_PASSWORD from %LOCALAPPDATA%\\crashiq\\app.env, keeps studies and caches in ...\\data (the same layout as
/var/data in the Docker image) and the log in ...\\logs\\server.log, listens on 127.0.0.1 only: the Cloudflare
Tunnel is the one way in. Same recipe as TrafficOpsIQ deploy/windows.
"""

import os
import subprocess
import sys
import time
from pathlib import Path

home = Path(os.environ["LOCALAPPDATA"]) / "crashiq"
data = home / "data"
repo = Path(__file__).resolve().parents[2]
port = sys.argv[sys.argv.index("--port") + 1] if "--port" in sys.argv else "8310"

env = dict(os.environ, PYTHONUNBUFFERED="1", PYTHONPATH=str(repo / "backend"), CRASHIQ_HOSTED="1",
           CRASHIQ_DB=str(data / "crashiq.sqlite"),
           CRASHIQ_FILES_DIR=str(data / "cache" / "ccrs_files"),
           CRASHIQ_TIGER_DIR=str(data / "cache" / "tiger"),
           CRASHIQ_NAD_DIR=str(data / "cache" / "nad"),
           CRASHIQ_ADDRFEAT_DIR=str(data / "cache" / "tiger_addrfeat"),
           CRASHIQ_POSTMILE_DIR=str(data / "cache" / "postmiles"),
           CRASHIQ_AADT_DIR=str(data / "cache" / "aadt"))
for line in (home / "app.env").read_text(encoding="utf-8-sig").splitlines():
    key, sep, value = line.partition("=")
    if sep:
        env[key.strip()] = value
if not env.get("APP_PASSWORD"):
    sys.exit("APP_PASSWORD is empty in app.env; refusing to serve the app with no password")
# Runtime AI stays off on the hosted copy (#55), the same as the Docker image.
for key in ("ANTHROPIC_API_KEY", "TYPESAFE_API_KEY", "CRASHIQ_FIXTURES_DIR"):
    env.pop(key, None)

cmd = [sys.executable, "-m", "uvicorn", "crashiq.server:_default_app", "--factory",
       "--app-dir", str(repo / "backend"), "--host", "127.0.0.1", "--port", port]

# shortcut: server.log grows forever (a few KB a day of access lines); rotate if it ever matters.
with open(home / "logs" / "server.log", "a", buffering=1, encoding="utf-8") as log:
    while True:  # restart a crashed server; the task's own restart covers this script dying
        log.write(f"--- start {time.ctime()} port {port}\n")
        code = subprocess.call(cmd, cwd=repo, env=env, stdout=log, stderr=subprocess.STDOUT)
        log.write(f"--- exited {code} {time.ctime()}, restarting in 5 s\n")
        time.sleep(5)
