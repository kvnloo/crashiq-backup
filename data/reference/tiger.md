# TIGER/Line roads (#229)

**What:** US Census Bureau TIGER/Line Shapefiles, EDGES (road segments: geometry, MTFCC road class, FULLNAME,
topology node ids) and FEATNAMES (alternate names per segment), per California county. Public domain. Joined with
OpenStreetMap into the placement network (user decision and download approval 2026-10-22, docs/03).

**Where:** `data/cache/tiger/<vintage>/<county fips>.sqlite` (gitignored; `CRASHIQ_TIGER_DIR` moves it). Only named
road segments (MTFCC S...) are kept: points, bounding box, names. The two zips are not kept.

**Size:** Los Angeles County (06037) is ~50 MB EDGES + ~9 MB FEATNAMES to download; most counties are a few MB.

**When:** a county is downloaded the first time a study needs it (the counties whose padded box,
`ca_county_boxes.json`, holds a point of the corridor), in the background. Until it is there the network is OSM only,
the pull log says so (`network.tiger_pending`), and the next view pulls again. A failed download is retried after an
hour. The vintage is set in `backend/crashiq/config/tiger.json` (2026); a new vintage downloads into its own folder.

**Union rules** (`backend/crashiq/union.py`): a TIGER segment within 12 m of OSM ways along at least 80% of its length
(sampled every 10 m, the last 15 m at each end left out) adds its names to those ways (`tiger:name`, way source
`both`); otherwise it is added as a way (`tiger`), joined at an OSM node within 12 m or spliced into the OSM way there.
TIGER names for the corridor and for each study intersection are used by the pull's name filters, the GPS street
check and the FARS road check. A crash placed with a name or road only TIGER has is tagged `placed_on: tiger`.
A placement that needs a road only TIGER has (not just TIGER's name on an OSM way) goes to the review list as a
suggestion tagged TIGER while `tiger_only_auto` is false (`config/placement.json`, PM review of #232); the user
decides after run 9's statewide accuracy.

**County boxes:** `ca_county_boxes.json`, from CCRS crashes with GPS (0.5–99.5 percentile + 5 km), built by
`backend/scripts/build_county_boxes.py` from the Tester's CCRS mirror.
