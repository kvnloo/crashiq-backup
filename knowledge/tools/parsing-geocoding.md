# Public address-parsing and geocoding tools (issue #20, 2026-10-18)

Full report: `reports/Public parsing and geocoding tools.md`. Sources: `research_notes/tools-2026-10-18/`.
Accuracy on crash strings comes from Claude Code's bake-off (hidden-GPS, Long Beach + SF), not from here.
This file records knowledge only. Every choice below is still the user's decision.

| Tool | Licence | Use in CrashIQ | Cost / footprint | Watch out |
|---|---|---|---|---|
| usaddress | MIT | Parse street strings; has intersection labels (`IntersectionSeparator`, `SecondStreetName*`) | Few MB, pure Python | No published accuracy; retrainable with parserator on our own labels (needs user approval) |
| usaddress-scourgify | MIT | USPS Pub 28 normalizing of house addresses | Pure Python | Raises `AmbiguousAddressError` on anything usaddress tags "Ambiguous"; built for mailing addresses |
| libpostal (+ `postal`) | MIT code; model trained on ODbL/CC-BY data, model licence not stated | Parse/normalize | Model 1.8 GB (Senzing 2.2 GB), ~4 GB RAM: Render 4 GB instance $85/mo vs $25 | 99.45% claim is for postal addresses; retraining needs a 100 GB+ pipeline |
| PostGIS TIGER geocoder | GPL-2.0 (fine hosted; on-prem distribution brings GPL duties) | `Geocode_Intersection(street1, street2, state, city, zip)` | Needs Postgres (Render $19–55/mo + $0.30/GB); Render supports the extension | PostGIS 3.6 loader stops at TIGER 2025 |
| Census TIGER/Line | No copyright (17 USC 105); trademark limits product naming | Nationwide street network + alternate names + address ranges | TIGER 2026 zipped (EDGES+FACES+ADDR+FEATNAMES): CA 1.22 GB, TX 1.90, PA 0.64, FL 0.63, NY 0.46, WA 0.43, MA 0.19, US 21.8 | No accuracy warranty |
| Census Geocoder API | Free federal service | House addresses only | $0; batch ≤10,000 | No intersection mode; rate limits unpublished |
| Nominatim | GPL-3.0 + OSM ODbL | Not for the core | Public server max 1 req/s, so self-host | Can't search intersections (issue #123, open since 2014) |
| Pelias | MIT + OSM/OA/WOF data | Not for the core | 8 GB RAM, 50 GB disk, Elasticsearch | Intersection layer confirmed only on paid geocode.earth |
| OSM via public Overpass (our `osm.py`) | ODbL | Current street network | ~10,000 requests/day, 1 GB/day guideline | Production: Geofabrik extracts (CA 1.26 GB, US 11.4 GB) + "© OpenStreetMap contributors" |

## Lessons (dated, with evidence)
- 2026-10-18 · Licences don't block any of these tools in a hosted paid product; cost and fit decide. (GitHub API licence check, all eight tools)
- 2026-10-18 · Nominatim can't geocode street intersections, so it is no use for crash records that are "street & street". (Nominatim issue #123, open since 2014)
- 2026-10-18 · The Census Geocoder is address-only. Its user guide never mentions intersections.
- 2026-10-18 · Parsers and TIGER are nationwide, but crash *locations* aren't: NY public tables use reference markers (no lat/long), WA uses state-route mileposts. Street-pair geocoding is a CA-type-state problem. Milepost conversion belongs in the state pack (#19).
- 2026-10-18 · TIGER is the only street network built to one schema in every state, with no copyright and no attribution duty.
- 2026-10-18 · The public Overpass server is for development only (≈10k requests/day); a paid product needs local OSM extracts.
