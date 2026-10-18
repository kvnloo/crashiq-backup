# Client pain points (crash data)

The user's rule (2026-10-18): every data problem we find is a pain point our clients (agencies, consultants)
live with today. Keep each one here with **evidence**, **what it costs the client**, and **how CrashIQ addresses
it**. This is the source for client conversations, pitch material and the product roadmap. Add to it every time
a test or analysis turns up a new discrepancy.

| # | Pain point | Evidence (our measurements) | What it costs the client | How CrashIQ addresses it | Status |
|---|---|---|---|---|---|
| 1 | **Most city-street crashes have no coordinates** | CCRS 2024: SF 35%, Sacramento 33%, LA City 56% have lat/long. SFPD ~1%, LAPD ~1% of their own reports | Engineers geocode by hand from street names, or drop crashes from the study | Automatic placement from the report's own clues (streets, distance, direction, address): 90% auto-placed at 98.8% in SF, the rest in a one-click review list | Built (PR #16) |
| 2 | **Officer GPS is not reliable either** | Long Beach PD: only 73% of records have GPS on the streets the officer wrote; some 446 km and 1,223 km away | Crashes plotted in the wrong place, hot spots shifted or missed, nobody notices | Self-consistency check: GPS vs the record's own street names; inconsistent points flagged for review | Measured; flag to build |
| 3 | **Street names written dozens of ways** | Real SF/LB records: `ALEMANY BL`, `07TH ST`, `MISSINO ST`, `CAN NESS AV`, `147TH ST (3100 BLOCK)`, `RT 101`, house addresses in the cross-street field | Pivot tables split one intersection into many rows; counts per location are wrong | Name normalization + matching to the real street network; every crash keeps its original text | Built |
| 4 | **The distance from the intersection gets lost** | ~9% of SFPD crashes: SF's own record has the distance, CCRS doesn't | Mid-block crashes counted as intersection crashes (wrong 250 ft assignment) | Use the distance when present (median error 2 m vs 38 m without); flag when missing | Built (flag to add) |
| 5 | **Sources disagree on how many crashes there were** | LA 2024: CCRS has 12,851 LAPD crashes, LAPD's own data has 16,720 (~23% gap) | Studies under-count without knowing it; results differ by source | State-level source validity check and consensus (issue #18); report which source and its known gaps | Research (Hermes #18) |
| 6 | **Public maps of crashes are not exact** | LAPD's points are snapped to the intersection (median 6 m from it even when the crash was 87 m away), and some are km off (Canoga & Burbank: 1.6 km) | Maps look precise but aren't; mid-block patterns disappear | Place from the report itself; show location source and confidence per crash | Measured |
| 7 | **Duplicate and blank report numbers** | SFPD 2023–25: 25 blank/duplicate; one number used 4× for different crashes | Joins between tables or sources silently attach the wrong record | Uniqueness checks before any join; duplicates listed | Built |
| 8 | **Unit errors** | "Miles" offsets of 33–233 inside a city (feet typed as miles): 5 in SF, 146 in Long Beach | Crashes placed miles away, or dropped | Automatic fix with a flag on the record | Built |
| 9 | **Deleted reports still in the data** | CCRS has an `IsDeleted` flag (found by Hermes) | Counting reports CHP has withdrawn | Dropped on every pull, count reported | Built |
| 10 | **Property-damage crashes missing from common tools** | CCRS: 59% of 2024 rows are PDO; TIMS lacks most PDO | Patterns in non-injury crashes (rear-ends, sideswipes) invisible; EPDO weights incomplete | CCRS pulled directly, PDO included | Built |
| 12 | **Location clues buried in the parties table and narratives** | CCRS Parties has each driver's street, direction and movement; narratives are only in the PDF reports | Hand geocoders read them one crash at a time | Weighted-clue locator uses every structured clue; report upload reads narratives (planned) | Designed (#17) |
| 11 | **Each city writes reports differently** | Long Beach drops directionals (`7TH ST` for East/West 7th), so the "relaxed" tier carries 44% of crashes vs ~2% in SF | One-size tools work in one city and fail in the next | Per-city validation before claiming accuracy; per-agency rules where needed | Ongoing (#17) |

## How to use this with clients
- Lead with the client's own city: run the coordinate-coverage and GPS-consistency checks on their agency first.
  The numbers (rows 1, 2, 5) are usually the opening.
- Every claim above has a reproducible script or query in this repo; keep it that way.
