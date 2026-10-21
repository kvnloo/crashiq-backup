"""Latest screen-test run as a small CSV for the test tracker page (data/statewide/tracker/screen.csv).

Reads e2e's own report (.e2e/report.json) and writes one row per test: screen, what it checks, result, run date.
Run after `npm test`: python tests/screen/summary.py
"""

import csv
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[1] / "data" / "statewide" / "tracker" / "screen.csv"


def main() -> None:
    run = json.loads((HERE / ".e2e" / "report.json").read_text())["run"]
    rows = []
    for r in run["results"]:
        title = r["titlePath"][-1]
        screen, _, check = title.partition(": ")
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
