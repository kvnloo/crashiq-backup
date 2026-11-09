"""Records tests/fixtures/or_odot/: 40 real Multnomah 2024 crashes from ODOT's decode DB (CRASH + PARTIC rows, all
columns, as exported to CSV) and the same crashes from ODOT's public ArcGIS layer (the two query responses).

Run: PYTHONPATH=backend python tests/fixtures/make_or_odot.py <dir with mdb2024/CRASH.csv and PARTIC.csv>
"""

import csv
import json
import sys
from pathlib import Path

import httpx

from crashiq.sources import or_odot

OUT = Path(__file__).parent / "or_odot"


def main(src: Path) -> None:
    OUT.mkdir(exist_ok=True)
    rows = [r for r in csv.DictReader(open(src / "mdb2024/CRASH.csv", newline="")) if r["CNTY_NM"].strip() == "Multnomah"]
    pick, seen = [], set()
    # every severity, an unlocated crash, a freeway crash, an offset with a compass direction
    wants = [lambda r: r["CRASH_SVRTY_SHORT_DESC"].strip() == "FAT", lambda r: r["UNLOCT_FLG"] == "True",
             lambda r: r["FC_CD"] == "11", lambda r: r["CMPSS_DIR_CD"] in ("1", "3", "5", "7") and r["FROM_ISECT_DSTNC_QTY"]]
    for want in wants:
        pick += [r for r in rows if want(r) and r["CRASH_ID"] not in seen][:5]
        seen |= {r["CRASH_ID"] for r in pick}
    pick += [r for r in rows if r["CRASH_ID"] not in seen][:40 - len(pick)]
    ids = {r["CRASH_ID"] for r in pick}
    for name, keep in (("CRASH", pick), ("PARTIC", None)):
        with open(src / f"mdb2024/{name}.csv", newline="") as f:
            rd = csv.DictReader(f)
            keep = keep if keep is not None else [r for r in rd if r["CRASH_ID"] in ids]
            with open(OUT / f"{name}.csv", "w", newline="") as g:
                w = csv.DictWriter(g, rd.fieldnames)
                w.writeheader()
                w.writerows(keep)
    where = f"CRASH_ID IN ({','.join(sorted(ids))})"
    calls = []

    def get(url, params):
        body = httpx.post(url, data=params, headers={"User-Agent": "CrashIQ/0.1"}, timeout=120).json()
        calls.append({"params": params, "body": body})
        return body
    or_odot.fetch_layer(where, get=get)
    (OUT / "layer.json").write_text(json.dumps({"where": where, "calls": calls}))


if __name__ == "__main__":
    main(Path(sys.argv[1]))
