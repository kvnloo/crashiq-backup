"""Build data/reference/county_boxes_<st>.json for a non-California state pack: each county's bounding box from the
Census cartographic boundary file (cb_<year>_us_county_500k.zip, public domain), padded 5 km, keyed by 5-digit FIPS.
TIGER downloads and the corridor's county list read it (California keeps ca_county_boxes.json, built from CCRS).

    python backend/scripts/build_state_county_boxes.py ~/.hermes/cache/scratch/statepack/cb_2024_us_county_500k.zip VA MA
"""

from __future__ import annotations

import io
import json
import sys
import zipfile
from pathlib import Path

import shapefile

ROOT = Path(__file__).resolve().parents[2]
STATE_FIPS = {"VA": "51", "MA": "25", "WA": "53", "OR": "41", "DC": "11", "NY": "36"}
PAD = 5 / 111.0          # 5 km in degrees of latitude (longitude padded the same: a little over, never under)


def main(zpath: str, states: list[str]) -> None:
    z = zipfile.ZipFile(zpath)
    stem = Path(zpath).stem
    r = shapefile.Reader(shp=io.BytesIO(z.read(f"{stem}.shp")), dbf=io.BytesIO(z.read(f"{stem}.dbf")))
    fields = [f[0] for f in r.fields[1:]]
    for st in states:
        out = {}
        for sr in r.iterShapeRecords():
            a = dict(zip(fields, sr.record))
            if a["STATEFP"] != STATE_FIPS[st]:
                continue
            w, s, e, n = sr.shape.bbox
            out[a["GEOID"]] = {"name": a["NAMELSAD"], "box": [round(s - PAD, 4), round(w - PAD, 4),
                                                             round(n + PAD, 4), round(e + PAD, 4)]}
        doc = {"source": f"Census {stem} (public domain), county bounding box + 5 km", "box":
               "[min lat, min lon, max lat, max lon]", "counties": dict(sorted(out.items()))}
        (ROOT / "data" / "reference" / f"county_boxes_{st.lower()}.json").write_text(json.dumps(doc, indent=1) + "\n")
        print(st, len(out), "counties")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
