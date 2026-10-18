# Sources: public parsing/geocoding tools (issue #20), read 2026-10-18

Repo facts via `gh api repos/<owner>/<repo>` (licence, stars, open issues) and tags/commits; PyPI JSON API.
- libpostal https://github.com/openvenues/libpostal — MIT; tag v1.1.4 2025-10-18; last commit 2025-12-06 (Senzing data v1.2.0); README: 99.45% full parses, model 1.8 GB / Senzing 2.2 GB, training data licences (ODbL / CC-BY), REST server "~4Gb memory"
- Senzing model https://github.com/Senzing/libpostal-data — Apache-2.0
- postal (Python binding) PyPI 1.1.11, 2025-10-29, MIT
- usaddress https://github.com/datamade/usaddress — MIT; PyPI 0.5.16 2025-08-07; labels https://parserator.datamade.us/api-docs/
- usaddress-scourgify https://github.com/GreenBuildingRegistry/usaddress-scourgify — MIT; v0.7.1 2026-08-07; `scourgify/normalize.py` parse_address_string raises AmbiguousAddressError
- PostGIS https://postgis.net/source/ (3.6.4 current); Geocode_Intersection https://postgis.net/docs/manual-3.6/Geocode_Intersection.html; loaders in extras/tiger_geocoder on branch stable-3.6 up to tiger_loader_2025.sql; GPL-2.0
- TIGER legal text https://www2.census.gov/geo/pdfs/maps-data/data/tiger/tgrshp2026/TGRSHP2026_TechDoc_Ch1.pdf
- TIGER sizes: `tsize.py` here → `tiger2026_sizes.json` (from https://www2.census.gov/geo/tiger/TIGER2026/{EDGES,FACES,ADDR,FEATNAMES}/)
- Whole-US PostGIS TIGER DB ~105 GB: user report, 2015 (r-bloggers "Geocoding 18 million addresses with PostGIS Tiger Geocoder"), search snippet only, not re-verified
- Census Geocoder guide https://www2.census.gov/geo/pdfs/maps-data/data/Census_Geocoder_User_Guide.pdf (10,000 batch; zero mentions of "intersection")
- Nominatim https://github.com/osm-search/Nominatim (GPL-3.0, v5.3.3 2026-10-14); hardware https://nominatim.org/release-docs/latest/admin/Installation/; policy https://operations.osmfoundation.org/policies/nominatim/; intersections issue #123 (open), #3581 closed as duplicate
- OSMF geocoding guideline https://osmfoundation.org/wiki/Licence/Community_Guidelines/Geocoding_-_Guideline
- Pelias https://github.com/pelias (MIT; api v7.11.0 2026-09-25; parser v5.0.0); hardware https://github.com/pelias/documentation/blob/master/pelias_from_scratch.md; geocode.earth intersection layer https://geocode.earth/docs/reference/data_layers/
- Overpass usage https://dev.overpass-api.de/overpass-doc/en/preface/commons.html
- Geofabrik https://download.geofabrik.de/north-america.html (US 11.4 GB), California NorCal 623 MB + SoCal 640 MB
- Render pricing https://render.com/pricing (web 512 MB $7, 2 GB $25, 4 GB $85, 8 GB $135; Postgres 1 GB $19, 4 GB $55, storage $0.30/GB; disk $0.25/GB); extensions https://render.com/docs/postgresql-extensions
- ARNOLD/HPMS https://catalog.data.gov/dataset/hpms-spatial-all-sections-2024
