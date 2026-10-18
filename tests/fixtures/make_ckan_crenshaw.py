"""Writes ckan_crenshaw.json: an offline stand-in for the data.ca.gov CCRS datastore, Crenshaw Blvd 2021–2025.

Crash rows: the 121 REAL CCRS crashes in design/mockups/example-data.js (CHP, public domain): location,
date, hour, day, collision type, lighting, roads, PCF and injury/no-injury as recorded. Column layout follows
the CCRS export. Fields the mockup didn't keep are SYNTHETIC and deterministic:
  - injury level (IWP ExtentOfInjury) for injury crashes, number injured
  - Parties rows (drivers, pedestrians, vehicle types, movements)
  - weather, surface, collision time minutes, collision ids, report versions
Added edge cases for the cleaning log: a CHP-deleted report, a duplicate Collision Id with two report versions,
preliminary records, crashes without coordinates (some on the corridor street, one not, one in another city),
a crash far outside the corridor, and one injury crash with no IWP row (injury level unknown).

    python3 tests/fixtures/make_ckan_crenshaw.py
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
src = (ROOT / "design" / "mockups" / "example-data.js").read_text()
CRASHES = json.loads(re.search(r"window\.CRASHES\s*=\s*(\[.*\])\s*;?", src, re.S).group(1))

YEARS = range(2021, 2026)
RID = {(t, y): f"{t[:3]}-{y}-0000-0000" for t in ("crashes", "parties", "iwp") for y in YEARS}
CITY = ("HAWTHORNE", "1913", "19", "1904")   # name, city code, county code, NCIC (example values)

CRASH_FIELDS = [
    ("Collision Id", "int4"), ("Report Version", "int4"), ("Is Preliminary", "text"), ("IsDeleted", "text"),
    ("NCIC Code", "text"), ("Crash Date Time", "text"), ("Collision Time", "text"), ("Day of Week", "text"),
    ("City Code", "text"), ("City Name", "text"), ("County Code", "text"),
    ("Collision Type Description", "text"), ("NumberKilled", "int4"), ("NumberInjured", "int4"),
    ("Weather 1", "text"), ("LightingDescription", "text"), ("Latitude", "text"), ("Longitude", "text"),
    ("PrimaryCollisionFactorDescription", "text"), ("PrimaryCollisionFactorViolation", "text"),
    ("PrimaryRoad", "text"), ("SecondaryRoad", "text"), ("SecondaryDistance", "text"),
    ("SecondaryDirection", "text"), ("SecondaryUnitOfMeasure", "text"), ("RoadwaySurfaceCode", "text"),
    ("MotorVehicleInvolvedWithDesc", "text"), ("PedestrianActionDesc", "text"), ("HitRun", "text"),
    ("IsFreeway", "text"),
]
PARTY_FIELDS = [("CollisionId", "int4"), ("PartyNumber", "int4"), ("PartyType", "text"), ("IsAtFault", "text"),
                ("DirectionOfTravel", "text"), ("MovementPrecCollDescription", "text"), ("StatedAge", "text"),
                ("Vehicle1TypeDesc", "text")]
IWP_FIELDS = [("CollisionId", "int4"), ("InjuredWitPassId", "int4"), ("ExtentOfInjury", "text"),
              ("InjuredPersonType", "text"), ("IsWitnessOnly", "text")]

MOVES = {
    "REAR END": ["Proceeding Straight", "Stopped"], "BROADSIDE": ["Making Left Turn", "Proceeding Straight"],
    "SIDE SWIPE": ["Changing Lanes", "Proceeding Straight"], "HEAD-ON": ["Making Left Turn", "Proceeding Straight"],
    "HIT OBJECT": ["Ran Off Road"], "OVERTURNED": ["Ran Off Road"], "OTHER": ["Backing", "Parked"],
    "VEHICLE/PEDESTRIAN": ["Making Right Turn"],
}
WEATHER = ["Clear"] * 8 + ["Cloudy", "Raining"]
tables = {rid: {"fields": [], "rows": []} for rid in RID.values()}
for (t, y), rid in RID.items():
    tables[rid]["fields"] = [{"id": c, "type": ty} for c, ty in
                             {"crashes": CRASH_FIELDS, "parties": PARTY_FIELDS, "iwp": IWP_FIELDS}[t]]


def add_crash(cid, r, *, version=1, prelim=False, deleted=False, lat=None, lon=None, city=CITY, killed=0,
              injured=None, extents=None, parties=None):
    lat0, lon0, ctype, sev, light, dow, hour, _key, prim, sec, date, pcf = r
    year = int(date[:4])
    injured = (1 if sev == "I" else 0) if injured is None else injured
    row = {
        "Collision Id": cid, "Report Version": version, "Is Preliminary": str(prelim), "IsDeleted": str(deleted),
        "NCIC Code": city[3], "Crash Date Time": f"{date}T{hour:02d}:{(cid * 7) % 60:02d}:00",
        "Collision Time": f"{hour}{(cid * 7) % 60:02d}", "Day of Week": dow, "City Code": city[1],
        "City Name": city[0], "County Code": city[2], "Collision Type Description": ctype,
        "NumberKilled": killed, "NumberInjured": injured, "Weather 1": WEATHER[cid % len(WEATHER)],
        "LightingDescription": light,
        "Latitude": "" if lat == "" else str(lat if lat is not None else lat0),
        "Longitude": "" if lon == "" else str(lon if lon is not None else lon0),
        "PrimaryCollisionFactorDescription": "(Vehicle) Code Violation" if pcf.startswith("VC") else "Other Improper Driving",
        "PrimaryCollisionFactorViolation": pcf, "PrimaryRoad": prim, "SecondaryRoad": sec,
        "SecondaryDistance": str((cid * 37) % 300) if cid % 3 else "0", "SecondaryDirection": "NSEW"[cid % 4],
        "SecondaryUnitOfMeasure": "F", "RoadwaySurfaceCode": "B" if WEATHER[cid % len(WEATHER)] == "Raining" else "A",
        "MotorVehicleInvolvedWithDesc": "Pedestrian" if "PEDESTRIAN" in ctype else
        ("Fixed Object" if ctype == "HIT OBJECT" else "Other Motor Vehicle"),
        "PedestrianActionDesc": "Crossing in Crosswalk at Intersection" if "PEDESTRIAN" in ctype else "No Pedestrian Involved",
        "HitRun": "M" if cid % 11 == 0 else None, "IsFreeway": "False",
    }
    tables[RID[("crashes", year)]]["rows"].append(row)
    if deleted:
        return
    moves = MOVES.get(ctype, ["Proceeding Straight"])
    ps = parties or [("DRIVER", "MOTORCYCLE" if cid % 29 == 0 else "PASSENGER CAR", m) for m in moves]
    if "PEDESTRIAN" in ctype and parties is None:
        ps = [("DRIVER", "PASSENGER CAR", "Making Right Turn"), ("PEDESTRIAN", None, None)]
    for n, (ptype, veh, mv) in enumerate(ps, start=1):
        tables[RID[("parties", year)]]["rows"].append({
            "CollisionId": cid, "PartyNumber": n, "PartyType": ptype, "IsAtFault": str(n == 1),
            "DirectionOfTravel": "NSEW"[(cid + n) % 4], "MovementPrecCollDescription": mv,
            "StatedAge": str(20 + (cid * 13 + n * 7) % 60), "Vehicle1TypeDesc": veh})
    for k, ext in enumerate(extents if extents is not None else []):
        tables[RID[("iwp", year)]]["rows"].append({
            "CollisionId": cid, "InjuredWitPassId": cid * 10 + k, "ExtentOfInjury": ext,
            "InjuredPersonType": "Driver" if k == 0 else "Passenger", "IsWitnessOnly": "False"})


def injury_levels(i):
    if i % 7 == 0:
        return ["SUSPECTED SERIOUS INJURY"]
    return ["SUSPECTED MINOR INJURY"] if i % 2 else ["POSSIBLE INJURY", "POSSIBLE INJURY"]


cid = 9_000_000
inj_i = 0
for i, r in enumerate(CRASHES):
    cid += 1
    if r[3] == "I":
        inj_i += 1
        if inj_i == 5:                        # injury crash whose IWP rows are missing → level unknown (U)
            add_crash(cid, r, extents=[])
            continue
        ext = injury_levels(inj_i)
        add_crash(cid, r, injured=len(ext), extents=ext,
                  prelim=r[10] >= "2025-09-01")
    else:
        add_crash(cid, r, prelim=r[10] >= "2025-09-01")

base = CRASHES[10]
add_crash(9_100_001, base, deleted=True)                                              # CHP-deleted report
dup = list(CRASHES[20])
add_crash(9_100_002, dup, version=1)                                                  # duplicate id, v1 PDO ...
add_crash(9_100_002, dup, version=2, injured=1, extents=["SUSPECTED MINOR INJURY"])  # ... v2 injury: keep v2
def row(ctype, sev, light, dow, hour, prim, sec, date, pcf):
    return [0, 0, ctype, sev, light, dow, hour, "", prim, sec, date, pcf]


add_crash(9_200_001, row("SIDE SWIPE", "P", "DAYLIGHT", "Monday", 8, "CRENSHAW BL", "W 144TH ST", "2023-03-06", "VC 22107"),
          lat="", lon="")
add_crash(9_200_002, row("BROADSIDE", "P", "DAYLIGHT", "Wednesday", 12, "ROSECRANS AV", "CRENSHAW BOULEVARD", "2022-05-11",
                         "VC 21801(a)"), lat="", lon="")
add_crash(9_200_003, row("REAR END", "I", "DARK-STREET LIGHTS", "Friday", 21, "CRENSHAW BLVD", "MARINE AVE", "2024-11-15",
                         "VC 22350"), lat="", lon="", extents=["SUSPECTED SERIOUS INJURY"])
add_crash(9_200_004, row("SIDE SWIPE", "P", "DAYLIGHT", "Monday", 8, "MARINE AV", "AVIATION BL", "2023-03-06", "VC 22107"),
          lat="", lon="")                                                          # not the corridor street
add_crash(9_200_005, row("SIDE SWIPE", "P", "DAYLIGHT", "Monday", 8, "CRENSHAW BL", "W 135TH ST", "2023-03-06", "VC 22107"),
          lat="", lon="", city=("GARDENA", "1910", "19", "1910"))                  # another city: not pulled
add_crash(9_300_001, [33.95, -118.40] + list(CRASHES[3][2:]))                                 # far away: outside bbox

package = {"name": "ccrs", "resources": [
    {"id": rid, "name": {"crashes": "Crashes_", "parties": "Parties_", "iwp": "InjuredWitnessPassengers_"}[t] + str(y),
     "datastore_active": True} for (t, y), rid in RID.items()]}
out = ROOT / "tests" / "fixtures" / "ckan_crenshaw.json"
out.write_text(json.dumps({"package": package, "tables": tables}, indent=0))
n = sum(len(v["rows"]) for k, v in tables.items() if k.startswith("cra"))
print(f"{n} crash rows, {sum(len(v['rows']) for k, v in tables.items() if k.startswith('par'))} parties,"
      f" {sum(len(v['rows']) for k, v in tables.items() if k.startswith('iwp'))} IWP rows")
