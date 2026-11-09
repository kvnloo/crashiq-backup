# Rhode Island crash data: gated (bucket D), verified 2026-11-08

**Verdict:** no pack. RIDOT's statewide crash data became a public record in June 2026, but it still comes only by records request. There is no portal, open layer or download.

## What changed in 2026
- **RIGL 38-2-17** (2026-H 7576 / 2026-S 2480, passed 2026-06-11, "This act shall take effect upon passage"). It says records protected by 23 U.S.C. 407 "shall nonetheless be deemed public records; provided, however, the records may not be used for purposes prohibited by that federal statute". Bill text: https://webserver.rilegislature.gov/BillText/BillText26/HouseText26/H7576.pdf (saved `~/.hermes/state-manuals/ri/RI_H7576_2026.pdf`, sha256 ce77b1ba…). Press release: https://www.rilegislature.gov/pressrelease/_layouts/15/ril.pressrelease.inputform/DisplayForm.aspx?ID=376702&List=c8baae31-3c10-431c-8dcd-9dbbe21ce3e9
- The law gives a right to the records. It doesn't make RIDOT publish them.

## Checked live on 2026-11-08
| Where | Result |
|---|---|
| RIDOT Safety page https://www.dot.ri.gov/safety/ | The "Crash Data 2023/2024/2025" links are **Crash Facts PDFs** (summaries). The 2024 link points to the 2025 PDF. |
| Crash Facts 2025 PDF | 36,850 crashes, 41 fatal crashes, 238 serious-injury crashes. Severity split: K 0.1%, A 0.6%, B 2.5%, C 15.7%, O 75.6%, unknown 5.5%. |
| Crash Facts 2026 Jan 1-Sep 30 | 29,776 crashes, 32 fatal, 175 serious-injury. |
| ArcGIS Online, `owner:DOT_AGOL.Admin` (RIDOT's org, services5.arcgis.com/JfTJE9T2RFfUZzVx) | 65 items, 44 services. No crash layer: sweeping, litter, bridges, potholes, and `Wrong_Way_Driver_System` (not a crash layer). `orgid:JfTJE9T2RFfUZzVx crash` finds 0 crash items. |
| ArcGIS Online `crash RIDOT`, `crash "Rhode Island"`, `collisions Rhode Island` | No agency crash layer. The RIDOH alcohol-surveillance hub is a health summary. |
| RIGIS hosting server https://risegis.ri.gov/hosting/rest/services | 86 services, no crash layer. |
| RIDOT Traffic Design Manual 2025, 7.1.1 p. 7-1 | "For all RIDOT Projects, crash data must be requested from the RIDOT Office of Safety". Non-RIDOT projects get it from the town police. At least 5 years. KABCO per crash (p. 7-2). |
| Public records | RIDOT APRA portal https://www.dot.ri.gov/business/publicrecordsrequest.php |

## Cities
- **Providence:** the PVD Crash Map (Providence Streets Coalition, Tableau Public) comes from Providence PD records. It's a community project with no licence, and the user rule is statewide first. Not used.
- roadway.report's RI map is FARS (fatal only).

## Bring-your-export column map
`ri-column-map.json`. It's built from the 2006 Uniform Crash Report form and the TDM 2025 crash-summary fields. No database dictionary is published, so it hasn't been checked against a real export. GPS isn't documented: ask for it.

## Methods (RI's own manuals)
- **Severity:** KABCO by the most severe injury (TDM 2025 p. 7-2).
- **Study window:** latest 5 years, at least (TDM 2025 p. 7-1).
- **Crash costs, crash rates, critical rate:** `missing`. The RIDOT HSIP 2025 report (https://www.dot.ri.gov/Safety/reports/docs/Highway_Safety_Improvement_Program.pdf, saved, sha256 5c0289d6…) describes network screening (roadway departure, ped/bike, intersections; an HSM-based systemic tool), but its text gives no unit crash costs or base rates.
- Manuals saved in `~/.hermes/state-manuals/ri/`: TDM 2025, HSIP 2025, Crash Facts 2025 and 2026 Jan-Sep, H 7576. The NHTSA copy of the crash form 403s scripted downloads; it was read with web_extract only.

## User actions
1. File an APRA request with RIDOT for the 2021-2025 statewide crash repository plus 2026 to date. Ask for the crash, vehicle and person tables, the field dictionary, lat/lon, and CSV.
2. In the same request, ask whether RIDOT will publish the data online, and whether a paid tool may use it, beyond the 407 limit.
3. Send one delivered file. A reader (bucket D "upload your export") then follows the column map.

## Not checked
- The repository's GPS share and street-name share.
- Whether the current form (MMUCC 4) differs from the 2006 form.
- Town police exports.
