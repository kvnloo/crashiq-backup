# Public tools tested for CrashIQ (bake-off 2026-10-18)

User's goal: use proven public tools so the agent spends fewer tokens figuring things out. Every tool ran through
the same hidden-truth tests (`backend/scripts/validate_geocode.py`, dev halves): SF (truth = SF's geocode, 4,028
crashes) and Long Beach (truth = the record's own GPS, raw, 6,326 crashes; noisier). A = exact matches only;
B = all code tiers. Cells: placed automatically / accuracy within 250 ft.

| Normalizer / network | SF A | SF B | Long Beach A | Long Beach B |
|---|---|---|---|---|
| **Ours** on OSM (baseline) | **91.4% / 98.8%** | **94.4% / 98.5%** | 44.8% / 88.6% | **88.0% / 85.6%** |
| Ours + USPS Pub 28 suffix table (usaddress-scourgify) | 91.3% / 98.8% | 94.4% / 98.4% | 44.8% / 88.6% | 88.0% / 85.5% |
| usaddress parser + USPS table | 89.0% / 98.9% | 93.8% / 98.5% | 44.8% / 88.4% | 87.4% / 85.2% |
| libpostal (prefers street-type expansions) | 89.4% / 98.9% | 92.6% / 98.7% | 45.0% / 88.7% | 86.4% / 85.9% |
| Ours on **Census TIGER 2024 roads** (instead of OSM) | 91.4% / 98.5% | 93.9% / 98.4% | 36.2% / 89.6% | 87.7% / 85.1% |

## What we learned
- **No library beats our rules on coverage.** They are built for mailing addresses, not police shorthand:
  `HY` (highway) is not in USPS Pub 28; usaddress reads `E PACIFIC COAST HY` as "East Pacific"; libpostal's top
  reading of `MISSION ST` is "Mission Saint" and of `ALEMANY BL` includes "block" and "bowl". libpostal is slightly
  more accurate but places fewer crashes. Street-name cleanup is **not** the bottleneck.
- **TIGER roads ≈ OSM roads** for placement (SF 91.4% either way; accuracy 98.5% vs 98.8%). TIGER is public
  domain and uniform for every US county, so it is a good base network for the nationwide rollout. Idea to test:
  use both networks and require agreement (a consensus of sources, the user's approach).
- **PostGIS TIGER geocoder (`Geocode_Intersection`) could not be installed** on this Intel Mac (Homebrew: Tier 3,
  "unsatisfied requirement"). Testing TIGER *data* in our own locator answered the same question without it.
- **CHP's CCRS data dictionary** is extracted to `data/reference/ccrs_dictionary.json` (127 fields, 32 code lists,
  e.g. TrafficControlDeviceCode A–D, movement codes). Decoding codes needs no model calls.

## Keep / try next
- Keep our normalizer; add police shorthand it misses as alias rows (user-approved), not a new library.
- Try: ours first, libpostal as a fallback only for crashes ours can't place.
- Try: OSM + TIGER consensus.
- Licences and hosting cost per tool: Hermes, issue #20.
