# A State Pack Must Describe Location per Road Type, Not per State: Outline for CA, NY, TX, WA and MA

Issue #19 (uses #4, #18, #20) · Hermes · researched 2026-10-18 · status: outline only. Per the user (2026-10-18), only the California pack is active; nothing here asks Claude Code to build another state.

The state pack keeps everything state-specific out of the core (docs/03, "Market DECIDED"). This outline says what a pack has to contain, filled in for California and the four states the user named. The main finding is that **location method varies inside a state, by road type**, so the pack can't carry one "location method" field. Washington uses three in one dataset: state-route milepost, county-road number plus milepost, and city block plus intersecting street. California uses two: CHP's GPS on freeways and county roads, and street pair plus offset on city streets. New York's public tables have only a reference marker and no coordinates. Texas CRIS has coordinates and street fields, with TxDOT's reference-marker system on state roads (field names UNVERIFIED until a CRIS extract is pulled). Massachusetts is already 93–97% geocoded. Severity mapping, reporting thresholds and legal notices differ the same way. The pack therefore needs one record per **road type**: which source, which location method, which cross-check. That's the shape #18 produced for California.

**Method.** Facts come from the #4 state research (`reports/Crash data and study methods by state.md` and `research_notes/state-research-2026-10-18/`), the #20 tools report, the #18 California work (`reports/California crash data sources by road type.md`), and three checks made 2026-10-18: the WSDOT crash data dictionary, the WSDOT portal's FARS-comparison notes, and the column list of Austin's CRIS-sourced open dataset. Anything not confirmed from a primary source is marked **UNVERIFIED**.

## What every pack contains

| # | Section | What it holds | Why it can't be shared |
|---|---|---|---|
| 1 | **Identity** | State, pack version, status (`active` / `outline`), golden-test status | Only a golden-tested pack may run studies |
| 2 | **Sources per road type** | For each road type: record source, location source, cross-check source, access type (`live_api` / `bulk_file` / `user_export`), freshness, licence status | #18: the right source and check differ by road type |
| 3 | **Field map** | Source columns → the canonical crash / party / person schema (MMUCC-style, `state` + `source` on every row) | Every state names fields differently |
| 4 | **Severity map** | Source codes → KABCO, with a documented rule and a caveat flag where it isn't one-to-one | NY and Seattle don't use KABCO; TX uses numeric codes |
| 5 | **Location methods per road type** | `coordinates` (validate and keep), `street_pair` (our locator), `route_milepost` / `reference_marker` (the state's linear referencing system), plus which street network (OSM / TIGER per #20) | WA has three methods in one dataset; NY public data has only reference markers |
| 6 | **Counting rules** | Reporting threshold, PDO caveats, death window (30 days or not), deleted/preliminary records, known reporting breaks per agency/year | Counts are only comparable under the same rules (#18: CCRS vs Caltrans +4.5%) |
| 7 | **Validity checks** | The cross-checks to run on each study (second source per road type, FARS fatal check), thresholds, known gaps | #18 consensus rule |
| 8 | **Method tables** | Crash costs, countermeasure/CRF list, average-rate tables, default data windows | Each state sets its own (#4) |
| 9 | **Study modes** | The state's formats (HSIP, ICE, TIS safety section, LRSP…) | Each state's formats differ (#4) |
| 10 | **Legal notices** | §407/§409, DPPA, state confidentiality text for exports | Wording differs by state |

## The five states

### California (active)

| Section | Content |
|---|---|
| Sources per road type | **Freeways, conventional highways outside cities, county roads (CHP):** CCRS records + GPS (100%); cross-check Caltrans TASAS (state highways), FARS (fatal). **City streets and state highways inside cities (city police):** CCRS records (with PDO), GPS on ~53%; cross-check agency open data (DataSF good; LAPD gap 23–33%) and TIMS points if the user supplies them. All `live_api`, public domain |
| Field map | Built in `ca_ccrs.py` (Crashes); Parties and InjuredWitnessPassengers to add |
| Severity map | CCRS person injury codes → KABCO; open item N3 in docs/06 |
| Location | `coordinates` (CHP, validated against the record's own streets) + `street_pair` (PR #16 locator: exact / address / relaxed / near). `IsFreeway` is blank on local-agency rows, so road type is derived from agency + highway + incorporated flags |
| Counting rules | Drop `IsDeleted`; flag `Is Preliminary`; feet-as-miles fix; non-unique report numbers; LAPD 2020–21 reporting break; Caltrans "on the highway" rule when comparing to Caltrans rates |
| Method tables | HSIP Analyzer crash costs; Caltrans CRF list (82 vs 86 to reconcile, #4 Q9); Caltrans rate-group averages (SHS only, D3) |
| Study modes | Profile/TIS (v1), HSIP, ISOAP, ATP, LRSP |
| Legal | §407/§409 on HSIP outputs; Veh. C. §20014 confidentiality of the underlying reports |

### New York (outline)

| Section | Content |
|---|---|
| Sources per road type | **Statewide public tables** (data.ny.gov, DMV): no coordinates, county / municipality / `dot_reference_marker_location` only, 4 rolling years, OPEN-NY terms allow private-sector use. **CLEAR** (NYSDOT): geocoded, agency-sponsored login per consultant contract → `user_export`. **NYC**: open data with lat/long (89%), feed paused since 2026-06-11 |
| Field map | Case / Individual / Vehicle tables; CLEAR export layout UNVERIFIED |
| Severity map | Public tables are **not KABCO** (crash: Fatal / Injury / PD; person: Killed / Severe / Moderate / Minor). #4 Q10 recommendation: CLEAR exports for KSI work, mapped public tables for counts only |
| Location | `reference_marker` on state highways (needs NYSDOT's reference-marker inventory); CLEAR's computed location as `coordinates`; NYC `coordinates` |
| Counting rules | $1,000 reporting threshold; non-reportable police-only crashes appear in CLEAR but not the public tables |
| Method tables | Red Book crash costs (K $18,186,968 … O $18,794); CMF Clearinghouse; BCR need not be ≥1.0 |
| Study modes | HSIP (PSI / LOSS / PIL), Yellow Book investigations, NYC Vision Zero priority locations |
| Legal | §407/§409; DPPA on DMV records |

### Texas (outline; named by the user as the likely next state)

| Section | Content |
|---|---|
| Sources per road type | **CRIS** public extract (free registration, password-protected daily zips) for all roads; CRIS Query for quick counts. Licence for redistribution: none stated (UNVERIFIED) |
| Field map | CRIS crash / unit / person extract; field list UNVERIFIED until a registered pull. Austin's CRIS-sourced data shows `rpt_block_num`, `rpt_street_name`, `onsys_fl` (on the state system), `latitude`/`longitude`, `crash_sev_id` |
| Severity map | CRIS codes: 4 killed, 1 incapacitating, 2 non-incapacitating, 3 possible, 5 not injured, 0 unknown → K, A, B, C, O, unknown |
| Location | `coordinates` where present (statewide share UNVERIFIED); `street_pair` / block number off-system; TxDOT reference markers on-system (CRIS field names UNVERIFIED) |
| Counting rules | $1,000 threshold; annual figures final by June |
| Method tables | NSC comprehensive costs set per HSIP call; Work Codes with reduction factors; statewide average rates |
| Study modes | TSP Manual §6.1.3.1 historical crash analysis (5 years, fixed minimum items), HSIP SII calculator, two-stage ICE on state routes |
| Legal | CRIS disclaimer ("conclusions are your own"); §409 |

### Washington (outline)

| Section | Content |
|---|---|
| Sources per road type | **WSDOT** record-level extracts by request (public requests via the Public Disclosure Request Center, ~10 days, Excel) → `user_export`; public portal is summary only. Seattle open data for Seattle streets |
| Field map | WSDOT layout: Collision Report Type (by trafficway jurisdiction), Primary Trafficway, Block Number, Milepost, Ahead/Back indicator, Intersecting Trafficway, County Road number + milepost |
| Severity map | WSDOT coding vs KABCO UNVERIFIED; Seattle uses 3 / 2b / 2 / 1 / 0 |
| Location | **Three methods by road type:** state routes → `route_milepost` (WSDOT LRS, with back-mileage equations); county roads → county road number + milepost (county LRS); city streets → `street_pair` from block number + intersecting trafficway |
| Counting rules | Final each July; **WSDOT keeps deaths beyond 30 days if on the police report, FARS doesn't**, so the FARS check needs a tolerance; 15 years retained |
| Method tables | Societal crash costs (values UNVERIFIED); HSM / CMFs |
| Study modes | LRSP 7-step systemic template, City Safety / County Safety calls, ICE (Memo 25-02, roundabouts preferred on state highways) |
| Legal | §409 notice on every release |

### Massachusetts (outline)

| Section | Content |
|---|---|
| Sources per road type | **MassDOT IMPACT** ArcGIS REST (crash / vehicle / person layers per year), all roads, near-real-time → `live_api`. No licence stated; ask MassDOT first (#4 Q4) |
| Field map | IMPACT fields incl. `MAX_INJR_SVRTY_CL`, `IS_GEOCODED`, joined road inventory (AADT, F_CLASS, lanes, speed limit, jurisdiction) |
| Severity map | Already KABCO |
| Location | `coordinates` (92.8% geocoded 2026, 97.3% 2025, uneven by police department); `street_pair` only for the residue |
| Counting rules | $1,000 threshold; operator-only reports mixed with police reports |
| Method tables | MassDOT CMF list; comprehensive crash costs (values UNVERIFIED); EPDO weights |
| Study modes | HSIP cluster eligibility (top 5% EPDO in region), Road Safety Audit packet, ICE Procedure, Safety Alternatives Analysis (SPF + EB) |
| Legal | MassDOT disclaimer ("not an official record"); §409 |

## What this means for the #19 interface (input for Claude Code's proposal)

1. **Location method is a list keyed by road type**, not one value per state. The core runs the method named for each crash's road type. `route_milepost` / `reference_marker` is a new method type, needed by NY, WA and TX state roads; CA doesn't need it in v1 because CHP's GPS covers its state highways.
2. **Access type is per source.** `user_export` is a first-class adapter type (NY CLEAR, WSDOT, possibly TX), not an edge case.
3. **Counting rules and validity checks are pack data**, so the #18 source check runs the same code in every state with each state's rules and second sources.
4. **Severity maps carry a caveat flag**, so a non-KABCO state can still produce counts while KSI outputs are blocked or labelled.
5. Nothing here changes the v1 build: only the CA pack is active (user, 2026-10-18).

## Questions for the user

Reply like `1Y 2Y…`. Recommendation in brackets.

1. **Road type inside the pack:** describe sources, location method and cross-checks per road type (as above), rather than one set per state? [Yes]
2. **Milepost / reference-marker locating:** keep it out of v1 (CA doesn't need it) and build it with the first state that does (NY, WA or TX)? [Yes]
3. **Texas groundwork:** when you say go on Texas, should Hermes first register for the CRIS extract (needs your email on the account) to confirm the location fields? [Yes, when you say go]

## Confirmed versus unverified

**Confirmed:** WSDOT data dictionary location fields and report types; WSDOT 15-year retention and July finalization; WSDOT's >30-day death rule vs FARS; Austin CRIS-sourced columns; all NY, MA, TX and WA facts carried over from #4 are confirmed there unless marked.

**UNVERIFIED:** CRIS statewide field names and coordinate share; WSDOT severity coding; MassDOT and WSDOT crash-cost values; CLEAR export layout; licence terms in TX, WA and MA.

## Conclusion

A pack is a source table, a location method and a set of counting rules per road type, plus the state's method tables and study formats. California's pack is the template: one record source, two location methods, three cross-checks. The four outlines show the interface has to allow linear-referencing locations and user-supplied exports from the start, even though v1 uses neither.
