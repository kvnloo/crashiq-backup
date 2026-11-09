# State pack design (#19): the smallest seam for a second state

Hermes · 2026-11-07 · docs only, nothing built. Extended 2026-11-07 (user): state picker as the first step,
and each state's manuals, rates and costs as cited data (§ State picker, § Methods). User, 2026-11-07: "start the other states". #19 has been parked since
2026-11-02 ("finish, test, ship"), so building any step below needs the PM to reopen it. Inputs: #19, #18, #4,
`reports/State pack outline CA NY TX WA MA.md`, `reports/Crash data and study methods by state.md`, docs/03
("Market DECIDED", 2026-10-18), docs/04, and the code at `87c2ad4`.

## The problem in one paragraph

California code isn't in one place. The CCRS adapter (`sources/ca_ccrs.py`) is clean, but `crashes.pull()` talks
CKAN SQL to data.ca.gov directly, and California facts sit in about 20 other modules: CHP placeholder words, the CCRS
county code (alphabetical 1–58, turned into FIPS by `2n-1`), California's lat/lon box, Caltrans postmiles, AADT, rate
groups and LRSM costs, the "CA" route prefix, and file names such as `ca_cities.csv`. A second state needs three
things: a place for these facts (the **pack**), one entry point where a state's reader plugs in, and a crash-dict
contract the readers fill. California keeps its current code path.

## The seam

```python
# backend/crashiq/packs.py  (new; the only registry)
@dataclass(frozen=True)
class StatePack:
    code: str                    # "CA"
    fips: str                    # "06"
    status: str                  # "active" (offered to users) | "reader_only" (tests and Tester runs only)
    reader: ModuleType           # sources.ca_ccrs, sources.tx_cris, ...
    source: str                  # credit line on exports, spine and the pull summary
    legal: str                   # export notice (§407/§409, state confidentiality text)
    bounds: tuple                # ((lat_lo, lat_hi), (lon_lo, lon_hi)); a point outside is a bad coordinate
    first_year: int              # first year the reader has
    final_lag_months: int        # when a year counts as final
    severity_note: str | None    # set when the state's scale isn't KABCO (NY): KSI outputs carry it
    placeholders: frozenset      # squeezed "no street" words: NOTSTATED, UNK, PRIVATEPROPERTY ...
    route_prefixes: tuple        # the state's state-route spellings: ("CA",), ("SH", "FM", "RM", "IH", "LOOP", "SPUR")
    special_areas: re.Pattern | None  # report "cities" that are campuses, park districts, ports (never judged)
    ref: dict                    # data/reference files: cities, county_boxes, address_points, aliases, gps_piles, pcf
    name: str                    # "California": the Setup dropdown and every "in <state>" sentence
    methods: Path                # data/reference/methods_ca.json: cited manuals, rates, costs, screening (§ Methods)
    postmiles: Callable | None   # factory(settings) -> object with .at(route, county, pm, prefix) and .for_crash(c)
    aadt: Callable | None        # factory(settings) -> AadtCache-like; None = no state-highway rates (T22-T25)
    tiers: dict[str, tuple]      # location methods per road type, e.g. {"freeway": (...), "street": (...)}

PACKS = {"CA": StatePack(code="CA", reader=ca_ccrs, ...)}   # one line per state, added when it's activated
COMING = {"TX": "Texas", ...}   # researched, no pack yet: listed greyed out on Setup (§ State picker)
def get(code: str) -> StatePack: ...   # no default: CA comes only from the study column's DB default
```

In five lines:

1. A study belongs to one state (`study.state`, picked first on Setup, default `CA` for existing studies);
   `packs.get(study["state"])` is the one lookup. `get()` has no default, so nothing falls back to California.
2. `crashes.ensure()` line 1117 is the one dispatch: CA calls today's `pull()`; any other state calls
   `pull_reader(pack, ...)`, which calls `pack.reader.fetch(...)` and then the same cleaning California uses.
3. A reader only returns CCRS-shaped crash dicts (contract below), with `severity`, `county_fips` and the mode flags
   already set. It never sees the network, the locator or the profile.
4. Every California constant becomes a pack field with California's value, so CA behaviour (and every test) is
   unchanged.
5. Caltrans-only services (postmiles, AADT, ramps, rate groups) are optional pack fields. `None` reuses the "not
   available" path the code already has for fake/recorded CKAN (`postmile_for`/`aadt_for` return `None` today).

Skipped on purpose: auto-discovery of readers (it would pick up half-built ones), a plugin system, a `route_milepost`
locator (built with the first state that needs it, outline Q2), and study-mode formats (HSIP etc. are still CA-only
P2+ work).

## Reader contract (what tonight's `sources/<st>_<source>.py` should match)

Module constants: `STATE` ("TX"), `SOURCE` (credit line), `LICENCE` (terms + URL, and whether a paid app may use it),
`FIRST_YEAR`, `BOUNDS`. One function:

```python
def fetch(box, county_fips: list[str], years: list[int], cache_dir: Path) -> dict:
    """box = (s, w, n, e). Returns {"crashes": [...], "cleaning": {step: count}, "years_missing": [...]}.
    Crashes = every crash in the box with GPS, plus every crash without usable GPS in those counties.
    The core filters the no-GPS ones by street name; the reader does no name matching."""
```

If a reader already has another entry point, its pack entry wraps it (`reader=SimpleNamespace(fetch=lambda ...: ...)`);
no reader is rewritten.

Each crash is the dict `ca_ccrs.crash_record()` builds, after the pull adds severity and party details:

| Key | Required | Rule |
|---|---|---|
| `crash_id` | yes | string, unique within the state source |
| `report_version` | yes | int; `0` when the source has no versions. Highest wins |
| `deleted`, `preliminary` | yes | bool; `False` when unknown |
| `date`, `year`, `hour` | yes | ISO date, int, 0–23 or `None` |
| `lat`, `lon` | yes | floats, or `None` when missing or outside `BOUNDS`; then `bad_coords=True` if a point was given |
| `primary_road`, `secondary_road` | yes | raw text as reported (the core normalizes). Block number + street (TX, WA) goes in as `"1200 MAIN ST"` with `secondary_road` blank: the D5 house-address path picks it up |
| `offset_ft`, `offset_dir` | yes | feet and N/S/E/W from the secondary road, or `None` |
| `city` | yes | city name as reported; `"UNINCORPORATED"` outside cities |
| `county_fips` | yes | 5-digit string ("48453"). **New** (CA adds it too). `county_code` stays the state's own code |
| `state` | yes | "TX" |
| `is_freeway` | yes | bool, from the state's road class (access-controlled mainline and its ramps). See risk 1 |
| `killed`, `injured` | yes | ints |
| `severity` | yes | one of `K A B C U O` (U = injured, level not reported). The state's severity map lives in the reader |
| `ped`, `bike`, `ebike`, `escooter`, `motorcycle`, `heavy_truck` | yes | bool (CA: `ca_ccrs.mode_flags`) |
| `parties` | yes | list of `ca_ccrs.party_record()` dicts, `[]` if none: `party_type` (DRIVER, PEDESTRIAN, BICYCLIST, PARKEDVEHICLE...), `at_fault`, `movement`, `vehicle_type`, `direction` |
| `collision_type` | yes | CCRS words: REAR END, BROADSIDE, HEAD-ON, SIDE SWIPE, HIT OBJECT, OVERTURNED, VEHICLE/PEDESTRIAN, OTHER, or `None` (`diagram.py`, `profile.py:211` match these words) |
| `agency`, `report_number`, `lighting`, `weather`, `surface`, `hit_run`, `day_of_week` | no | text or `None` |
| `pcf`, `pcf_category`, `pcf_class` | no | California Vehicle Code only; leave out (T5 shows "blank") |

## Inventory of California assumptions (code at 87c2ad4)

Paths are under `backend/crashiq/` unless they start with `data/`.

| # | What | Where | Pack field / change |
|---|---|---|---|
| 1 | CKAN package `ccrs`, table prefixes, column candidates, required columns | `sources/ca_ccrs.py:22-23, 130-186` | stays in the CA reader |
| 2 | CCRS injury codes → KABCO (+ retired SWITRS levels), U/O rule | `sources/ca_ccrs.py:199-212, 419-436` | stays in the CA reader; others set `severity` |
| 3 | CHP code-letter prefixes, spellings (PEDESTRAIN), surface and PCF codes | `sources/ca_ccrs.py:188-192, 264-287` | stays in the CA reader |
| 4 | CA vehicle types for heavy truck, e-bike, e-scooter, motorcycle | `sources/ca_ccrs.py:219-229, 439-473` | stays in the CA reader; others set the flags |
| 5 | Feet-typed-as-miles fix, unit codes F/M/Y | `sources/ca_ccrs.py:40, 75-78, 362-366` | CA reader |
| 6 | California lat/lon box | `sources/ca_ccrs.py:291`, `fars.py:27,151`, `review.py:159`, `crashes.py:843` | `bounds` |
| 7 | Pull talks CKAN SQL to data.ca.gov (box, DMS box, area by street names, URL limit, ID chunks) | `crashes.py:37-45, 86-334, 639-1003` | CA path stays; new `pull_reader` (step 6) |
| 8 | Area for no-GPS reports = CCRS county code / city code column | `crashes.py:828-864` | generic path: `county_fips` from the county boxes |
| 9 | DMS repair by NCIC agency share (San Jose PD) | `crashes.py:432-481, 796-824` | CA path only (needs per-agency SQL) |
| 10 | CHP placeholders NOT STATED, UNK, NO STREET, PRIVATE PROPERTY | `crashes.py:185-188, 208-209, 585` | `placeholders` |
| 11 | Campus / park-district / port "cities" | `crashes.py:392-393` | `special_areas` |
| 12 | Incorporated cities list | `crashes.py:409-413`, `data/reference/ca_cities.csv` | `ref["cities"]` |
| 13 | "CA" as a state-route prefix | `names.py:37, 53, 79, 81-82`, `ramps.py:30` | `route_prefixes` (union of active packs, step 5) |
| 14 | CHP abbreviations in street names | `names.py:27-33` | shared (general English abbreviations); add a state's own only if measured |
| 15 | Mile-marker text → Caltrans postmile | `crashes.py:588-594, 707-712`, `mile_marker.py:1, 54`, `placement.py:186-212` | `postmiles` + tier in `tiers` |
| 16 | Caltrans county abbreviation by CCRS code (LA-405) | `postmile.py:45` | inside the CA postmile service |
| 17 | Caltrans SHN postmile layer (URL) | `postmile.py:34`, `crashes.py:1276-1295`, `export.py:50, 264` | `postmiles` |
| 18 | Caltrans Traffic Census AADT, Oct–Sep count year, ramp ADT | `aadt.py:1-46`, `config/aadt.json`, `shs.py:1-8, 77`, `ramps.py:1-17`, `crashes.py:1301-1311` | `aadt` |
| 19 | Caltrans rate groups + statewide expected rate | `rate_groups.py:17, 24`, `data/reference/caltrans_rate_groups.csv`, `network.py:665`, `profile.py:399-427`, db migration 15 | `methods` → `statewide_rates` (M4-M6) |
| 20 | LRSM v1.8 crash costs by KABCO and location type | `crash_cost.py:3-19`, `data/reference/crash_costs_ca.csv`, `profile.py:782, 827` | `methods` → `crash_costs` (M1-M3) |
| 21 | California Vehicle Code → 24 SWITRS PCF categories | `pcf.py:1-27`, `data/reference/pcf_categories.csv`, `profile.py:100-105`, `findings.py:413` | `ref["pcf"]` (None elsewhere) |
| 22 | CCRS county code → FIPS (`2n-1`) and → county name | `fars.py:30-33, 110`, `addrfeat.py:32-35, 131`, `nad.py:39-42, 126`, `data/reference/caltrans_districts.csv` | `county_fips` on every crash |
| 23 | FARS store: California rows only (STATE 6) | `fars.py:26, 58-70`, `db.py:167` | `fips` |
| 24 | TIGER county boxes and URL with `06` | `sources/tiger_files.py:34-36`, `data/reference/ca_county_boxes.json` | `fips`, `ref["county_boxes"]` |
| 25 | NAD California rows; county address layers | `nad.py:9, 47`, `settings.py:40`, `data/reference/address_points.json` | `ref["address_points"]` (add `state` per source) |
| 26 | Street aliases scoped by city + CCRS county code | `aliases.py:20-65`, `data/reference/street_aliases.csv` | `ref["aliases"]` |
| 27 | Listed CA police default GPS points | `gps_rules.py:25, 56`, `data/reference/gps_piles.json` | `ref["gps_piles"]` (empty is fine) |
| 28 | Freeway corridor counts only CHP `IsFreeway`; arterial drops it | `assign.py:83-88`, `grade.py:8, 80-84` | shared rule; reader must set `is_freeway` |
| 29 | Freeway text parsing (direction + "N OF" reference street, CHP style) | `freeway.py:4, 39-41, 65` | shared; other wordings fall to review (safe) |
| 30 | First year 2016, 18-month final lag, LRSM 3-year warning | `study.py:20-26, 63-64, 195` | `first_year`, `final_lag_months` |
| 31 | Re-pull TTLs tied to CHP revisions | `crashes.py:1050-1054` | shared for now |
| 32 | Credit and method lines, CHP field names in export legends | `export.py:30, 292-302, 326, 367, 377` | `source`, `legal` |
| 33 | Profile caveats naming CCRS, CHP, Caltrans | `profile.py:860, 899, 905-927, 977-999` | `source` + optional-service wording |
| 34 | Spine data holding kind "CCRS" | `spine.py:130-171` | `source` |
| 35 | Citations (Caltrans, CCRS, TIGER CA) | `config/references.json:37-82, 244, 394` | add a `state` key per reference |
| 36 | Frontend copy (Setup "CCRS", profile labels, fixtures) | `frontend/src/` (56 mentions, 10 files) | read labels from `/meta`; separate issue |

Not California-specific (reused as is): KABCO colours and labels (`severity.py`), assignment radii, the locator tiers
and the OSM + TIGER network, the profile tables, the findings validator, exports, the FARS fatal check (once
`county_fips` exists), NAD (national; needs that state's rows).

## State picker: the first step (user, 2026-11-07)

The user picks the state before anything else; everything after it (data source, location methods, rates, crash
costs, screening method, wording, legal notices) comes from that state's pack.

**Study record.** DB migration 16: `ALTER TABLE study ADD COLUMN state TEXT NOT NULL DEFAULT 'CA'`. Every existing
study reads as California with no data rewrite, and that column default is the only place "CA" is assumed.
`study.create(..., state)` (`study.py:104`) accepts only a code in `PACKS` with `status == "active"`; a `COMING` or
`reader_only` code fails with "Texas isn't ready yet." `StudyIn` (`study.py:165`) gets `state: str = "CA"`, so old
clients and tests keep working. `StudyPatch` (`study.py:172`) does **not** get it: the state is fixed once the study
exists, because the pull cache, rate groups, aliases and hand-placed crashes all belong to that state's data. Another
state means a new study. `validate_window` and `window_options` take `pack.first_year`/`pack.final_lag_months`
instead of `CCRS_FIRST_YEAR`/`FINAL_LAG_MONTHS` (`study.py:20, 23, 63-64`).

**API.** `GET /studies/meta?state=CA` (`study.py:188`) adds `states: [{code, name, ready}]` (`PACKS` active =
ready; `reader_only` and `COMING` = not ready), and returns the window options, first year and wording of the state
asked for: `source_short` ("CCRS") and `short_window_note` (with its cite, from the methods file). No state param
means the first ready state.

**Setup screen** (`frontend/src/screens/Setup.jsx`). One new field, first in the start bar, before "Study":

```jsx
<label htmlFor="state">State</label>
<select id="state" className="input" value={state} onChange={...} disabled={!meta || !!study}>
  {meta.states.map((s) => <option key={s.code} value={s.code} disabled={!s.ready}>
    {s.ready ? s.name : `${s.name} (coming)`}</option>)}
</select>
```

Native disabled options are greyed and skipped by the keyboard, so no custom widget. Ready states first, then
coming ones, both alphabetical. Changing the state refetches `meta?state=` and resets the years dropdown. An existing
study shows its state disabled, with one muted line: "A study's state is fixed. Start a new study for another
state." The POST body carries `state`. Copy that names California comes from meta: line 26 "(CCRS)" →
`source_short`, line 136 → `short_window_note`. Setup.test.jsx: CA selected by default, a "Texas (coming)" option
that's disabled, the POST body has `state`, an existing study's select is disabled.

The list is `PACKS` plus `COMING` (CA + tonight's 9 researched states), not all 50: a state with no research isn't
promised. Adding all 50 later is one dict.

**A corridor that isn't in the chosen state.** Two checks, both from data CrashIQ already fetches:

1. **Hard stop, offline.** `put_corridor` (`network.py:725`) already checks every point is a valid lat/lon. It adds:
   if no point lies inside `pack.bounds`, reply 400 "This line isn't in California. Start a new study and pick the
   state it's in." No crash pull, no Overpass call. `bounds` is a box, so it only catches lines clearly elsewhere.
2. **Border corridors, named.** `corridor_cities` (`network.py:118-148`, run at pull time from `crashes.py:1111`)
   already asks Overpass for the admin areas at sample points along the line. Widen its level filter from
   `^(6|8)$` to `^(4|6|8)$` and return `states` (the level-4 `ISO3166-2` tag, "US-NV") with the share of sample
   points in each. If any point is in another state, the corridor is kept (border corridors are real: Stateline at
   Lake Tahoe, US-95 at Needles), and the profile and export carry a caveat: "About 30% of this corridor is in
   Nevada. This study has California crashes only, so that part shows none." One study never pulls two states. When
   Overpass can't answer, check 1 still holds and the caveat says the state line couldn't be checked.

## Methods: each state's manuals, rates and costs as cited data (user, 2026-11-07)

Each state has its own HSIP manual, crash analysis guidelines, statewide average crash rates by facility type,
crash costs per KABCO level, screening method and SPF calibration. The pack holds them as **cited data**: every value
names its manual, edition and page. Nothing is AI-derived: a value is copied from the downloaded document's text (or
extracted by a script, as `scripts/extract_caltrans_rate_groups.py` does), never typed from memory or a model's answer.

### Where California's are hard-coded today (code at 87c2ad4)

15 items in about 55 places, plus M16, which has none. Paths under `backend/crashiq/` unless they start with `data/` or `frontend/`.

| # | What | Where | Becomes |
|---|---|---|---|
| M1 | LRSM v1.8 crash-cost table, file and source line | `crash_cost.py:3-7, 17, 19-21`; `data/reference/crash_costs_ca.csv:1-2`; `crash_costs_ca.md` | `crash_costs` |
| M2 | LRSM location types (KA by roadway / signalized / non-signalized), U priced at C, unknown control at the signalized price | `crash_cost.py:18, 31-38, 40-44` | `crash_costs.rules` (CA only) |
| M3 | Cost column label and source note "Caltrans LRSM 2026" | `profile.py:782, 794, 827, 829`; `frontend/src/screens/Profile.jsx:364` | label from the cite |
| M4 | Caltrans rate groups: TASAS base rate + ADT factor, F+I and fatal shares | `rate_groups.py:1-6, 17, 24, 51-69`; `data/reference/caltrans_rate_groups.csv`, `.md` | `statewide_rates` |
| M5 | Statewide columns, "pp. 83–90" note, "Caltrans' statewide averages" caveat | `profile.py:399-427, 502-503, 605-607, 908-909` | text from `statewide_rates` |
| M6 | Rate group entered per location (the Caltrans picker) | `network.py:665-667`; `db.py:197-205` (migration 15); `Profile.jsx:393, 451, 966` | same table; label = `facility_label` |
| M7 | Critical rate: K = 1.645, 3-site minimum, own-corridor average (HSM Ch. 4) | `profile.py:287-288, 300-304, 801-813, 938-946`; `export.py:383-384` | `screening` |
| M8 | Caltrans citations: LRSM, HCCL, the critical-rate entry, "TASAS planned" | `config/references.json:35-43, 215-250` (+ `ct_lrsm` cites at 88-100, 103-120, 174-190, 302-310) | `manuals` + per-state method entries |
| M9 | Caltrans Traffic Census AADT (Oct–Sep count year), source label | `aadt.py:1-23, 46, 404`; `config/aadt.json`; `shs.py:1-8, 77`; `crashes.py:1301-1311` | `pack.aadt` + `aadt` cite |
| M10 | Truck AADT and ramp ADT (T24, T25) | `profile.py:453-513, 530-559, 567-613`; `ramps.py:1-17` | `pack.aadt` |
| M11 | "At least 3 years, preferably 5" (LRSM) | `study.py:26`; `Setup.jsx:136` | `min_years` |
| M12 | First CCRS year 2016, CHP 18-month lag | `study.py:20, 23, 63-64` | `first_year`, `final_lag_months` (row 30) |
| M13 | K factor 10% default, Caltrans K and D definition | `study.py:25`; `config/references.json:193-200` | `k_factor` |
| M14 | Intersection influence radius 250 ft "HSM / Caltrans" | `network.py:49` | `influence_radius_ft` |
| M15 | HSIP "< 500 ft" intersection rule (named, not built) | `assign.py:7` | none until built |
| M16 | SPF calibration | nowhere (0 hits for SPF/calibration) | `spf_calibration`, data only |

Inventory rows 19 and 20 above are M4 and M1. Not California-specific: the rate formulas (`profile.py:291-345`,
FHWA/HSM), KABCO, EPDO (planned, HSM). They stay shared.

### The methods file

One file per state, next to California's existing tables: `data/reference/methods_ca.json`, `methods_tx.json`.
California's CSVs and their `.md` source notes stay where they are; the methods file points at them.

```json
{
  "state": "CA",
  "manuals": {
    "lrsm":  {"title": "Local Roadway Safety Manual", "publisher": "Caltrans", "jurisdiction": "CA",
              "edition": "v1.8", "date": "2026-05", "url": "https://dot.ca.gov/.../lrsm2026final.pdf",
              "sha256": "d5ec1b7f...", "downloaded": "2026-11-01", "note": "knowledge/sources/ca-caltrans-lrsm.md"},
    "cshwy": {"title": "2024 Crash Data on California State Highways", "jurisdiction": "CA", "edition": "2024 (v3)", ...},
    "hsm":   {"title": "Highway Safety Manual", "publisher": "AASHTO", "jurisdiction": "US", "edition": "1st, 2010", ...}
  },
  "values": {
    "hsip_manual":     {"manual": "lrsm", "page": "cover"},
    "analysis_guide":  {"manual": "lrsm", "page": "Sec. 3.1, p. 24"},
    "min_years":       {"value": 3, "preferred": 5, "manual": "lrsm", "page": "..."},
    "crash_costs":     {"file": "crash_costs_ca.csv", "dollar_year": 2026, "manual": "lrsm",
                        "page": "App. D, p. 100 (PDF 106)",
                        "rules": [{"text": "U priced at C", "decided": "user 2026-11-01 #273"}]},
    "statewide_rates": {"file": "caltrans_rate_groups.csv", "facility_label": "Caltrans rate group",
                        "unit": {"segment": "per MVM", "intersection": "per MEV", "ramp": "per MV"},
                        "manual": "cshwy", "page": "pp. 83-90"},
    "screening":       {"engine": "critical_rate_own_sites", "k": 1.645, "min_sites": 3,
                        "manual": "hsm", "page": "Ch. 4, Sec. 4.2.3"},
    "aadt":            {"manual": "ct_census", "page": "workbook per count year (config/aadt.json)"},
    "k_factor":        {"value": 0.10, "manual": "ct_kd", "page": "...", "decided": "user (\"10% is typical\")"},
    "spf_calibration": {"missing": "not looked up for CA yet"}
  }
}
```

Rules, enforced by `packs.check_methods(pack)` at load (tests fail on a bad file):

- Each value is either **cited** (`manual` + `page`, the manual having `title`, `edition`, `url`) or **missing**
  (`"missing": "<why>"`). Nothing else.
- `"verified": false` marks a value from research that no one has matched against the document yet. The engine treats
  it as missing; the report says "found in research, not yet checked against <manual>".
- A manual's `jurisdiction` is the pack's state or `US`. A Texas pack citing a California manual fails to load:
  **the check is the rule "never silently borrow California's"**. A national manual (HSM, FHWA crash costs,
  `fhwa_costs` in references.json) is allowed only with a `decided` line naming the user's decision.
- `screening.engine` is one CrashIQ has built (`critical_rate_own_sites` today, plus `statewide_rate_group` for CA),
  or `null`: the state's own method is recorded with its cite but isn't run.
- `spf_calibration` is data only (calibration factor per facility type and cite). No SPF engine exists; none is built
  for this.

**Engine changes (small, reuse the code that's there).**
- `crash_cost.cost()` (`crash_cost.py:40`) looks up `(sev, loc)`, then `(sev, "any")`, then for K/A `("KA", loc)` and
  `("KA", "any")`. One reader serves CA's KA-by-location table and a plain K/A/B/C/O row per state. U is priced only
  when the state's `rules` say how; otherwise U crashes are left unpriced and counted in the caveat.
- `rate_groups.table()` takes the pack's file. A state's file has `group, kind, base_rate, pct_fatal, pct_fi,
  printed_page` with no `adt_factor`; a missing factor adds 0, so `expected()` is unchanged. The `rate_group` table
  (migration 15) already stores any string, so the per-location picker is reused, labelled with `facility_label`.
- `profile.py:287-288` read `k` and `min_sites` from `screening`; the labels at M3, M5 and `export.py:383` read the cite.

**Fallback: shown, never silent.** When a value is missing, unverified, or its engine is `null`, the part it feeds is
left out and a caveat says why, in the profile, the PDF and the workbook:

| Missing | What the report does |
|---|---|
| `crash_costs` | No cost column, no ranking by cost. "No Texas crash costs in CrashIQ yet (TxDOT HSIP manual not checked)." |
| `statewide_rates` | No statewide columns. "No Texas statewide average rates in CrashIQ; rates are compared with this corridor's own sites only." |
| `screening` engine `null` | "Texas screens with <method> (<manual>, p. N); CrashIQ hasn't built it. This report shows the HSM critical rate against the corridor's own sites (national method)." |
| `aadt` | Today's "no state traffic counts" path (step 7); no T22-T25. |
| `min_years` | No short-window warning. |

Every report gets one **"State methods and sources"** block (References screen, PDF method section, workbook Sources
sheet), built from the methods file: per value, what was used and its manual, edition and page, or "not available for
<state>" and what the report did instead. `config/references.json` keeps national sources and shared methods; its
Caltrans entries (M8) move into `methods_ca.json`, and `/references?state=` merges the two.

Test that guards it: a fixture TX pack with `crash_costs` and `statewide_rates` missing runs through profile and
export; the output has no `crash_cost` values, both caveats, and none of the strings "Caltrans", "LRSM", "TASAS",
"CCRS", "CHP" anywhere.

### Plugging in tonight's research (9 states)

Each session writes `research_notes/<st>-2026-11-07/<st>-summary.json` with a `methods` key. A converter
(`scripts/methods_from_summary.py <st>`, step 9) copies it **verbatim** into a draft `methods_<st>.json`, every value
`"verified": false`:

| `summary.methods` | Goes to |
|---|---|
| `manuals[{title, url, date}]` | `manuals.<slug>` with `jurisdiction: <ST>`; `edition`, `sha256`, `downloaded` left blank to fill |
| `crash_costs{K,A,B,C,O,year}` | `crash_costs_<st>.csv` rows `K,any,<$>` …; `crash_costs.dollar_year = year`; `page` blank |
| `rates_available`, `rates_unit` | true → `statewide_rates {unit, verified: false}` (the table itself is extracted later from the PDF by a script); false → `missing: "state publishes none (research 2026-11-07)"` |
| `screening_method` | `screening {engine: null, name: <text>, verified: false}` |
| `differences_from_ca[]` | not pack data: the checklist for that state's build issue |

Verifying a value means downloading the manual, recording its SHA-256, finding the number in its text (pdftotext) and
filling `page`; then `verified` goes to true. `check_methods` rejects `verified: true` with no page or no `sha256`.
Unverified values never reach a report as numbers, so a wrong research figure can't be printed as a state's cost.

## Migration order (draft GitHub issues, not filed)

Every step: full suite green (955 tests at 87c2ad4), and the Tester's California statewide numbers identical, except
step 3, which changes only the pull cache format.

**1. State pack registry with the California pack (no behaviour change).**
Add `packs.py` with `StatePack`, `PACKS = {"CA": ...}` and `get()`. Every field points at today's constant or file.
Add `packs.check_crash(c, pack)` that enforces the reader contract above, and one test running it over CA fixture
pulls. Accept: no other file changes; tests green; the contract checker rejects a crash with a bad severity, a
missing `county_fips` or a point outside the state box.

**2. A study belongs to a state.**
DB migration 16: `study.state TEXT NOT NULL DEFAULT 'CA'`. `study.create` takes `state`, accepting only `active`
packs. The study API returns it. Accept: existing studies read as CA; creating a TX study fails while TX is
`reader_only`.

**2b. State picker on Setup.** `/studies/meta?state=`, `states` list, the dropdown, the two copy lines from meta
(§ State picker). With only CA ready, the list shows California plus the 9 researched states as "(coming)". Accept:
Setup tests above; creating a study with no `state` still makes a CA study.

**2c. Corridor outside the state.** The `bounds` stop in `put_corridor` and the level-4 check in `corridor_cities`
with its caveat. Accept: a line in Reno is refused for a CA study; a Stateline (Lake Tahoe) line saves and the profile
names Nevada and its share; a CA line's Overpass query result is otherwise unchanged.

**3. `county_fips` and `state` on every crash.**
`ca_ccrs.crash_record` adds both (from `caltrans_districts.csv`); `PULL_FORMAT` 34. `fars.fips`, `addrfeat._fips` and
`nad._county_codes` read `county_fips` instead of converting the CCRS code. Accept: FARS links, ADDRFEAT downloads and
NAD matches identical on the Tester's corridors.

**4. California constants become pack fields.**
Mechanical swaps, CA values unchanged: `bounds` (rows 6), `first_year`/`final_lag_months` (30), the reference files
(12, 24-27), `methods` (19, 20; step 4b), `ref["pcf"]` (21), `source`/`legal` (32-35). The pack comes from
`packs.get(study["state"])` at the entry points (`ensure`, `place_unmatched`, profile, export) and is passed down.
Accept: grep finds no `ca_` file name or CA bound outside `packs.py` and the CA reader.

**4b. California's methods file.** Write `methods_ca.json` from the existing `.md` source notes (no new numbers),
add `check_methods`, and point M1-M14 at it. Accept: CA profile and export identical (costs, statewide columns,
critical rates, labels); the TX fixture test in § Methods passes.

**5. Text rules from the pack.**
`placeholders`, `special_areas`, and `route_prefixes` (rows 10, 11, 13). `names.py` regexes are module-level and used
everywhere, so they're built once from the union of active packs' prefixes rather than threaded through every
`street_key` call. Accept: CA output unchanged with only the CA pack; a test that adding TX prefixes (SH, FM, IH,
LOOP, SPUR) doesn't change any CA street key in the alias and locator fixtures.

**6. Split `pull()`: CA fetch + shared cleaning, and `pull_reader()`.**
Move the parts of `pull()` that don't touch CKAN (the `no_gps` sorting, pile detection, report versions, deleted,
window, outside corners, severity and party lookups, and the summary: about `crashes.py:681-743` and `905-1041`) into
one shared `finish()`. `pull()` keeps its signature and calls it. New `pull_reader(pack, study, net, deps)`: county
FIPS from the county boxes along the line → `pack.reader.fetch()` → drop GPS points beyond the margin → `finish()`,
skipping the IWP/Parties step when `severity` is already set. `ensure()` line 1117 picks one by `study.state`. Accept:
CA statewide numbers identical; a fake reader in `tests/` with about 20 crashes (GPS, street pair, house address,
placeholder, other city) runs through pull → place → assign → profile → export.

**7. Optional Caltrans services.**
`postmile_for`, `aadt_for`, ramps, rate groups and the mile-marker tier read `pack.postmiles`/`pack.aadt`. `None`
takes the existing "not available" path; the profile caveat says "no state traffic counts for <state>" instead of
"Loading Caltrans counts". Accept: a non-CA study shows no T22-T25 and no postmile column, with the caveat.

**8. Register the first state as `reader_only`.**
One `PACKS` line for the state the user picks (likely TX), its reference files (county boxes, cities, address
points, cost table or none), and golden cases. It stays `reader_only` until it meets California's bar
(`state-crash-data-onboarding`: golden cases, placement accuracy on hidden-truth crashes, coverage by road type, the
3-corridor click-through) and the paid-use licence is cleared. Then the user flips it to `active`; the
Setup dropdown (step 2b) enables it with no frontend change.

**9. Draft methods files from tonight's research.** The converter (§ Plugging in) for each state whose
`<st>-summary.json` exists; drafts stay `verified: false` and their states stay in `COMING`. Accept: each draft
loads through `check_methods`; no draft value is used by a report.

## Risks

1. **`is_freeway` decides counting.** On a freeway corridor only `is_freeway` crashes count (`grade.py:80`); on an
   arterial they're excluded (`assign.py:83`). A reader that leaves it `False` empties freeway studies; one that sets
   it too widely drops arterial crashes. Each reader needs a measured road-class → freeway map.
2. **Vocabulary drift is silent.** `collision_type`, `party_type` and `movement` are matched by CCRS words. A reader
   passing its own words gets no error, just "Other" in the profile and a wrong diagram. The step 1 checker should
   warn on unknown values.
3. **The `pull()` split (step 6) is the risky refactor.** It's 400 lines with closures and counters the Tester's runs
   depend on. Extract only, no rule changes, and compare statewide numbers before and after.
4. **Route prefixes are global.** TX's SH/FM/IH/LOOP/SPUR enter the same regexes California uses. Step 5's test must
   show CA street keys don't move.
5. **County code meaning.** CA's `county_code` is alphabetical 1-58 and turned into FIPS by arithmetic. A reader
   putting FIPS in `county_code` would quietly break FARS links and ADDRFEAT downloads; that's why `county_fips` is a
   separate field.
6. **Licence, not code, gates paid use** (TX, MA, WA terms UNVERIFIED in the outline). `reader_only` keeps a state
   out of the hosted app until it's cleared.
7. Step 3 bumps `PULL_FORMAT`, so every cached study re-pulls from data.ca.gov once.
8. Block numbers are not house numbers: "1200 MAIN ST" from a block field may match no NAD point, or the wrong one.
   Measure before letting it auto-place.
9. **The `bounds` box is coarse.** California's box covers parts of Nevada, Arizona and Oregon, so check 1 only stops
   lines that are clearly elsewhere; the Overpass state check is what names a border corridor, and it needs Overpass.
10. **Research figures look final but aren't.** A summary's `crash_costs` may be from a stale edition or a secondary
    page. That's why every converted value starts `verified: false` and is never printed until a page is filled.
11. **A fixed state on a study** means an engineer who picked the wrong state redraws in a new study. Cheap today
    (Setup is the first step); revisit only if users ask.
