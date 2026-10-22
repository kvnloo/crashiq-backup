"""Screen-test fixtures: the app's offline Crenshaw data (tests/fixtures), plus three crashes the review list must show.

Three Crenshaw crashes lose their GPS and their cross street, so the pull keeps them for review ("no cross street",
#82/#94); one of them becomes fatal, for the fatal-first section (#175). Everything else is the app's own fixture, unchanged. Run: python tests/screen/make_fixtures.py
"""

import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE.parents[0] / "fixtures"
OUT = HERE / "fixtures"
REVIEW_IDS = (9200001, 9200002, 9200003)
FATAL_ID = 9200001          # one of them is fatal, so the review list's fatal-first section has a crash (#175)


def main() -> None:
    OUT.mkdir(exist_ok=True)
    shutil.copy(SRC / "overpass_crenshaw.json", OUT / "overpass_crenshaw.json")
    d = json.loads((SRC / "ckan_crenshaw.json").read_text())
    hit = 0
    for rid, t in d["tables"].items():
        if rid.startswith("cra-"):
            for r in t["rows"]:
                if r["Collision Id"] in REVIEW_IDS:
                    r["Latitude"], r["Longitude"], r["SecondaryRoad"] = "", "", ""
                    if r["Collision Id"] == FATAL_ID:
                        r["NumberKilled"] = 1
                    hit += 1
    assert hit == len(REVIEW_IDS), hit
    (OUT / "ckan_crenshaw.json").write_text(json.dumps(d))
    print(f"wrote {OUT} ({hit} crashes set up for review)")


if __name__ == "__main__":
    main()
