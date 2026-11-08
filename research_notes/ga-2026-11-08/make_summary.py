"""Write ga-summary.json from the measured numbers (placement_sample.json + the 2026-11-08 ARC group-by counts)."""
import json
from pathlib import Path

H = Path(__file__).parent
p = json.loads((H / "placement_sample.json").read_text())
sev = {  # ARC Crashes 2020-2024, groupBy Crash_Year x KABCO_Severity, 2026-11-08
    2020: [3003, 12689, 36568, 630, 136820, 3112], 2021: [3619, 14534, 42872, 804, 166031, 1698],
    2022: [3375, 14080, 43610, 759, 156376, 1355], 2023: [3367, 13448, 43289, 679, 152251, 3424],
    2024: [3209, 13131, 42719, 611, 155319, 1306]}
rows = {str(y): sum(v) for y, v in sev.items()}
assert sum(rows.values()) == 1074688
out = {
    "state": "GA", "bucket": "D", "status": "gated",
    "bucket_note": "Verified 2026-11-08: GEARS is login-only; GDOT's dashboard is charts only; detailed data by request form "
                   "('not to be sold to anyone'). Open regional layer (ARC, 19 metro counties) has year only and no licence.",
    "sources": [
        {"name": "GDOT GEARS / AASHTOWare Safety", "url": "https://www.gearsportal.com/Pages/Public/Home.aspx",
         "access": "gated (authorized users; request form)", "licence_paid_use": "no",
         "licence_text": "The data provided is \"AS IS\" ... and is not to be sold to anyone. ... GDOT does not support business decisions based upon the use of this data.",
         "licence_urls": ["https://www.dot.ga.gov/PartnerSmart/permits/Documents/Request_for_Crash_Data.pdf"],
         "years": "last 5 years on the dashboard", "rows_per_year": None, "gps_share": None,
         "street_names_share": None, "kabco": "yes (GDOT-523)", "keys_linkable": None},
        {"name": "ARC Crashes 2020-2024 (GDOT AASHTOWare extract)",
         "url": "https://services1.arcgis.com/Ug5xGQbHsD8zuZzM/arcgis/rest/services/Crashes2020_2024/FeatureServer/0",
         "access": "open (ArcGIS REST, no login)", "licence_paid_use": "unclear",
         "licence_text": "none stated (item fea7cdf5c08d482783e7bdf7fad4424b: licenseInfo empty)",
         "years": "2020-2024 (Crash_Year only, no date/time)", "rows_per_year": rows,
         "gps_share": p["gps_share"], "street_names_share": p["street_pair_share"],
         "kabco": "yes, crash level; 'Unknown' -> U", "keys_linkable": False,
         "coverage": "19 Atlanta-region counties (+1 Meriwether row)"}],
    "placement_sample": {"area": p["area"], "n": p["n"], "gps_share": p["gps_share"],
                         "name_placed_share": p["name_placed_share"], "auto_share": p["auto_share"],
                         "tier_gate_share": p["tier_gate_share"],
                         "within_250ft": p["within_250ft_tier_gate"], "within_250ft_low": p["within_250ft_tier_gate_low"],
                         "house_address_share": 0.0, "address_points_source": None,
                         "note": "auto_share is 0 because the network is TIGER-only and tiger_only_auto is off; "
                                 "within_250ft is for the tier gate (exact/unique_pair), against the layer's own point"},
    "importer_built": False,
    "end_to_end": None,
    "blockers": ["statewide data gated (GEARS login / GDOT request form)",
                 "GDOT disclaimer: 'not to be sold to anyone'",
                 "ARC open layer: year only (no date/time), 19 of 159 counties, no licence"],
    "user_actions": ["Ask GDOT (Crash Reporting Unit / GEARS 866-495-4206, or Office of Traffic Safety & Design) for a "
                     "statewide AASHTOWare Safety export (crash + vehicle + person) and written permission for use in a paid tool",
                     "Or ask ARC for a licence on 'Crashes 2020-2024' and for the crash date and time fields",
                     "Then map the export with research_notes/ga-2026-11-08/ga-column-map.json"],
    "cities": [{"city": "Atlanta region (ARC, 19 counties)", "source": "ARC Crashes 2020-2024",
                "url": "https://services1.arcgis.com/Ug5xGQbHsD8zuZzM/arcgis/rest/services/Crashes2020_2024/FeatureServer/0",
                "gps_share": p["gps_share"], "years": "2020-2024", "licence": "none stated"},
               {"city": "MARTA counties", "source": "ARC MARTACountyCrashes_2023",
                "url": "https://services1.arcgis.com/Ug5xGQbHsD8zuZzM/arcgis/rest/services/MARTACountyCrashes_2023/FeatureServer/0",
                "gps_share": None, "years": "2023", "licence": "none stated"}],
}
(H / "ga-summary.json").write_text(json.dumps(out, indent=1) + "\n")
print(json.dumps(out["placement_sample"], indent=1))
