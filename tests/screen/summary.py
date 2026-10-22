"""Latest screen-test run as a small CSV for the test tracker page (data/statewide/tracker/screen.csv).

Reads e2e's own reports (.e2e/report.json, and .e2e/report-live.json from `npm run test:live`) and writes one row per test: screen, what it checks, result, run date.
Run after `npm test`: python tests/screen/summary.py
"""

import csv
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[1] / "data" / "statewide" / "tracker" / "screen.csv"


def main() -> None:
    runs = [json.loads(f.read_text())["run"] for f in (HERE / ".e2e" / "report.json", HERE / ".e2e" / "report-live.json")
            if f.exists()]
    rows = []
    for run, r in ((run, r) for run in runs for r in run["results"] if r.get("selected", True)):
        title = r["titlePath"][-1]
        screen, _, check = title.partition(": ")
        screen = "Review list (live Crenshaw data)" if screen == "Live" else screen
        rows.append({"test": title, "screen": screen, "check": check, "result": r["status"],
                     "target": r["targetId"], "run_at": run["startedAt"][:10]})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, ["test", "screen", "check", "result", "target", "run_at"])
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} tests ({sum(r['result'] == 'passed' for r in rows)} passed) -> {OUT}")


if __name__ == "__main__":
    main()
