"""Reproduce the #18 California source cross-checks (Hermes, 2026-10-18).

Run: python3 queries.py > out.json   (stdlib only; needs network)
Results of the 2026-10-18 run are in evidence.json next to this file.

1. CCRS (data.ca.gov) 2023-2024 crashes by road type: IsFreeway, CHP vs local agency
   (NCIC code starting with 9 = CHP), IsHighwayRelated, City Is Incorporated.
   PDO proxy = NumberKilled = 0 and NumberInjured = 0. Deleted reports dropped.
2. CCRS per-year counts for LAPD (NCIC 1942) and SFPD (NCIC 3801), 2019-2026.
3. LAPD open data (data.lacity.org d5tf-ez2w) and DataSF injury crashes (ubvf-ztfx) per year.
Caltrans SHS 2024 and FARS figures were read from the published documents (URLs in sources.md).
"""
import json
import subprocess
import urllib.parse

CKAN = "https://data.ca.gov/api/3/action/"


def get(url):
    # curl instead of urllib: the macOS python here lacks the CA bundle for some Socrata hosts
    return json.loads(subprocess.run(["curl", "-s", "-m", "300", url], capture_output=True, text=True).stdout)


def ccrs_ids():
    pkg = get(CKAN + "package_show?id=ccrs")["result"]
    return {r["name"]: r["id"] for r in pkg["resources"] if r.get("datastore_active")}


def sql(q):
    return get(CKAN + "datastore_search_sql?" + urllib.parse.urlencode({"sql": q}))["result"]["records"]


def main():
    ids = ccrs_ids()
    out = {"roadtype": {}, "agency_years": {}}
    for yr in (2023, 2024):
        rid = ids[f"Crashes_{yr}"]
        out["roadtype"][yr] = sql(f'''SELECT "IsFreeway" fwy, (LEFT("NCIC Code",1)='9') chp,
            "IsHighwayRelated" hwy, "City Is Incorporated" inc, COUNT(*) n,
            SUM(CASE WHEN "Latitude" IS NOT NULL AND "Latitude"<>0 THEN 1 ELSE 0 END) gps,
            SUM(CASE WHEN "NumberKilled"=0 AND "NumberInjured"=0 THEN 1 ELSE 0 END) pdo,
            SUM(CASE WHEN "NumberKilled">0 THEN 1 ELSE 0 END) fatal, SUM("NumberKilled") killed
            FROM "{rid}" WHERE "IsDeleted"<>'True' GROUP BY 1,2,3,4''')
    for yr in range(2019, 2027):
        rid = ids[f"Crashes_{yr}"]
        out["agency_years"][yr] = sql(f'''SELECT "NCIC Code" ncic, COUNT(*) n,
            SUM(CASE WHEN "NumberKilled"=0 AND "NumberInjured"=0 THEN 1 ELSE 0 END) pdo,
            SUM(CASE WHEN "Latitude" IS NOT NULL AND "Latitude"<>0 THEN 1 ELSE 0 END) gps
            FROM "{rid}" WHERE "IsDeleted"<>'True' AND "NCIC Code" IN ('1942','3801') GROUP BY 1''')
    q = urllib.parse.urlencode({"$select": "date_extract_y(date_occ) as y, count(*) as n", "$group": "y", "$order": "y"})
    out["lapd_open"] = get("https://data.lacity.org/resource/d5tf-ez2w.json?" + q)
    q = urllib.parse.urlencode({"$select": "date_extract_y(collision_datetime) as y, count(*) as n", "$group": "y", "$order": "y"})
    out["datasf_injury"] = get("https://data.sf.gov/resource/ubvf-ztfx.json?" + q)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
