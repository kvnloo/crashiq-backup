"""Fetch and cache the San Francisco validation inputs: CCRS SFPD crashes, DataSF truth, OSM network."""
import json, sys, urllib.request
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from crashiq.sources import ca_ccrs
from crashiq import osm

CACHE = Path(__file__).resolve().parents[2] / "data" / "cache"
SF_WIKIDATA = "Q62"

def datasf(years):
    out = CACHE / f"datasf_{'_'.join(map(str, years))}.json"
    if out.exists():
        return json.loads(out.read_text())
    rows, off = [], 0
    yrs = ",".join(f"'{y}'" for y in years)
    while True:
        url = ("https://data.sf.gov/resource/ubvf-ztfx.json?$select=case_id_pkey,tb_latitude,tb_longitude,geocode_source,"
               f"cnn_intrsctn_fkey,primary_rd,secondary_rd,distance,direction&$where=accident_year%20in({yrs})&$limit=50000&$offset={off}")
        with urllib.request.urlopen(url.replace("'", "%27"), timeout=120) as r:
            batch = json.load(r)
        rows += batch
        if len(batch) < 50000: break
        off += 50000
    out.write_text(json.dumps(rows))
    return rows

if __name__ == "__main__":
    for y in (2023, 2024):
        rows = ca_ccrs.fetch(y, "\"NCIC Code\"='3801'", CACHE)
        print("ccrs", y, len(rows))
    print("datasf", len(datasf((2023, 2024))))
    net = osm.Network(osm.fetch(SF_WIKIDATA, CACHE))
    print("osm streets", len(net.streets), "intersections", len(net.intersections))
