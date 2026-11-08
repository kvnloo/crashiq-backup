# New Hampshire crash data: verified 2026-11-08 (Hermes)

**Verdict: gated (bucket D), no pack.** The 2026-11-02 screen holds: New Hampshire publishes no record-level crash
data. Crash reports live in NH DMV's VISION crash records system (Department of Safety, "the official repository of
all crash records"); NHDOT gets a redacted file, locates crashes on its LRS, and shares snapshots with the regional
planning commissions (RPCs). Release is governed by the Driver Privacy Act, RSA 260:14. What *is* online is re-hosts
of NHDOT's crash layer by an RPC and a consultant: not sources, but they show the export's layout, and one of them
let us run the placement test.

## 1. Agency sources checked (2026-11-08)

- **ArcGIS Online, NH state org** (`22pI3HyqMrW5cmOh`, owners `*_nh`, `NH_Publish`): query
  `orgid:22pI3HyqMrW5cmOh (crash OR crashes OR accident OR collision OR fatal OR safety)` returns 1 item, a comment
  form. No crash layer.
- **ArcGIS Online, all owners**, `crash "New Hampshire"` / `NHDOT` / `NH DOT`: only re-hosts (below) and a 2015 511
  layer (`NH_DOT_511`, service gone: "Invalid URL").
- **NHDOT GIS quarterly snapshots on GRANIT** (https://ftp.granit.unh.edu/NHDOT/GIS%20Data%20Quarterly%20Snapshots/,
  2022-2026, file geodatabases 115 MB-1.5 GB): the published layer lists
  (`NHDOT_GIS_Quarterly_Snapshot_Layers_List_20251013.txt`, 55 layers) hold roads, LRS routes, MIRE intersections,
  signals, guardrail... **no crash layer**.
- **NHDOT GIS Data Catalog**
  (https://www.dot.nh.gov/about-nh-dot/divisions-bureaus-districts/planning-community-assistance/gis-data-catalog):
  maps and road data only; "Email address for Data Questions & Requests to: GISMaps@dot.nh.gov".
- **NH DHHS WISDOM** (https://wisdom.dhhs.nh.gov/wisdom/topics.html?topic=motor-vehicle-crash-injuries): injury
  statistics, aggregate only.

## 2. Access and licence

- RSA 260:14 (https://gc.nh.gov/rsa/html/xxi/260/260-14.htm): motor vehicle records are released only "upon proof of
  the identity of the person requesting the records and representation ... that the use of the records will be
  strictly limited to" listed uses, one of which is "use by a legitimate business in research activities, and ... in
  statistical reports, so long as personal information is not disclosed".
- Bulk records: Saf-C 5602 (https://www.gc.nh.gov/rules/state_agencies/saf-c5600.html): form DSMV 494, a data
  privacy policy, a SOC 2 Type II report, and a list of all users. Crash reports themselves go to involved parties.
- Paid-use licence: **no grant found** (`unclear`); any release comes with RSA 260:14 conditions.
- NH OHS says an integrated crash data system with a public portal is "60% complete", "full operational status
  anticipated by FFY 2027" (NH FY25 Annual Report, https://www.nhtsa.gov/sites/nhtsa.gov/files/2026-07/NH_FY25_AnnualReport-tag.pdf).
  Re-check in 2027.

## 3. Re-hosts: the export's layout, not sources

| Layer | Owner | Rows | Years | Fields that matter |
|---|---|---|---|---|
| Crash History, https://services1.arcgis.com/Lxx6ZzbB9K8v0kCg/arcgis/rest/services/Crash_History/FeatureServer/0 | UVLSRPC (Upper Valley Lake Sunapee RPC) | 30,793 | Jan 2002 - Jun 2017 | CRASH_DATE, ACDTIME, TOWN_NAME, ACDSTREET, INTERSTREE, MILESFTFRO, NSEW_TO_IN, SRI, MP_ACCIDEN, SEVERITY, TOTALFATAL, TOTALINJUR, point |
| NHDOT_Crash_Data_RT114, https://services8.arcgis.com/M2LuFXYoyXAAOrnN/arcgis/rest/services/NHDOT_Crash_Data_RT114/FeatureServer/0 | HSHuser1 (consultant, NH 114 project) | 1,169 | 2017-2023 | ACCIDENTNUMBER, CRASHDATE, CRASHTIME, TOWN, ROUTENO_STREETNAME, SEVERITY, FATALINDICATOR, TOTALINJURED, DECIMALLATITUDE/LONGITUDE, DOT_LATITUDE/LONGITUDE, SRI, MP_ACCIDENT, node fields |
| New Hampshire 2019 Crash Data, https://services3.arcgis.com/iuNbZYJOrAYBrPyC/arcgis/rest/services/New_Hmapshire_2019_Crash_Data/FeatureServer/0 | Tufts student | 498 | 2019 | summary fields only |

UVLSRPC's item says: "Crash Data collected by NH DOT in the UVLS region ... The complete set of data can be found on
the NH DOT GIS Data Catalog". It isn't there any more (section 1).

**Severity is KABCO** in the newer layout (RT114, 1,000 rows read): Fatal Injury 4, Suspected Serious Injury 14,
Suspected Minor Injury 111, Possible Injury 52, No Apparent Injury 767, Unknown 48, blank 4. Older layout (UVLSRPC):
Killed / Incapacitating / Non_Incapacitating / Possible / No Apparent Injury / Unknown (the KABCO levels under their
pre-MMUCC-4 names). Every RT114 row has a point (DOT_LATITUDE/LONGITUDE, NHDOT's located point).

## 4. Placement, the California way (`placement_sample.py`, `placement_sample.json`)

Sample: UVLSRPC re-host, Grafton County (33009), 2015-2016, all 1,773 crashes (every one has a point). Point hidden;
crash placed from ACDSTREET + INTERSTREE on a TIGER/Line 2024 Grafton network; MILESFTFRO read as feet, NSEW_TO_IN as
the direction ("AT" = at the intersection).

| Measure | Value |
|---|---|
| Street pair present | 84.1% |
| House number in front of the street ("2345 RT 25A") | 52.3% |
| Placed from names | 43.0% of all (51.2% of pairs) |
| Auto-placed, default Gate() | 0% (TIGER-only network: every placement is `tiger_road`) |
| Auto-placed, Gate(tiger_only_auto=True) | 37.9% |
| Within 250 ft of the layer's point | 34.9% (Wilson low 31.6%), n = 763 |
| Same, offset 250 ft or less | 36.7% (low 32.8%), n = 562 |

**The low score is mostly the "truth", not the locator.** 39% of these crashes sit on a point shared by 5 or more
crashes (976 distinct points for 1,773 crashes): NHDOT locates crashes on its LRS by node and milepoint, not GPS. For
at-intersection crashes, the locator agrees with NHDOT's point 57% of the time where the point is unique, and 5% where
it is shared. The newer export carries DECIMALLATITUDE (officer GPS) next to DOT_LATITUDE: score against that when a
sample arrives.

What fails (fixes for the reader, none needed in shared code yet):
- 642 "no intersection of the two named streets": state routes written many ways (`RT 4`, `USHY 4`, `ROUTE 4-A`,
  `STHY 120`, `89 N`, a bare route code `00118` with a blank street); TIGER spells them `US Hwy 4`, `State Rte 120`.
  The sample's `forms()` tries NH/US/I- spellings; a reader must do the same and strip the house number.
- 282 with no cross street; ramps written as `EXIT 17 & RAMP`.
- Typos the locator's fuzzy tier catches only partly (`INTERCANGE DR`, `INERHANGE DR`).

## 5. Methods (see nh-methods.md)

NHDOT's HSIP Implementation Plan 2025 gives FHWA-assisted NH crash costs (2021 dollars): fatal $13.6 million,
suspected serious injury $737,900, KABC average $582,125, PDO $8,623. NHDOT uses HSM Part D and wants an initial B/C
of at least 2.0 (2021 HSIP report). Not verified against the PDF (dot.nh.gov returns 403 to scripted downloads).

## What you need to do

1. Ask NHDOT for one sample export in its GIS crash layout (the RT114 columns above), one county and one year, with
   written permission for use in a paid product: Bureau of Planning, GISMaps@dot.nh.gov, or NHDOT's crash data analyst.
2. If NHDOT points to DMV: a bulk request under RSA 260:14 / Saf-C 5602 (form DSMV 494) is heavy (SOC 2 report, user
   list). Ask for the research/statistical use with no personal information.
3. Re-check in 2027 for NH OHS's planned public crash portal.

## What we didn't check

- The full NHDOT export (person and vehicle tables, how they link).
- Accuracy against officer GPS (the re-hosts' points are NHDOT's LRS points).
- The HSIP Implementation Plan PDF itself (403 to scripts; values from its text via search).
