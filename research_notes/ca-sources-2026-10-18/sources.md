# Sources for issue #18 (California source matrix), read 2026-10-18

Live queries (script: `queries.py`, output: `evidence.json`)
- CCRS, data.ca.gov CKAN package `ccrs`, `datastore_search_sql` on Crashes_2016…2026 (resource ids resolved at run time).
- LAPD "Traffic Collision Data from 2010 to Present", https://data.lacity.org/resource/d5tf-ez2w.json (Socrata).
- DataSF "Traffic Crashes Resulting in Injury", https://data.sf.gov/resource/ubvf-ztfx.json (Socrata).

Documents
- TIMS SWITRS overview (97% geocoded, provisional vs final, 12–18 month CHP lag): https://tims.berkeley.edu/help/crashdata/switrs.php
- TIMS geocoding method (Esri StreetMap Premium locator on PRIMARY/SECONDARY ROAD + offset; Caltrans TSN postmiles for state highways; "Since 2015 … CCRS … does not return highway attributes to SWITRS"): https://tims.berkeley.edu/help/crashdata/switrs-geocoding.php
- TIMS Query & Map FAQ ("TIMS excludes property-damage-only crashes"): https://tims.berkeley.edu/help/tools/analysis/query-and-map.php
- TIMS codebook (COLLISION_SEVERITY 0 = PDO "not included on TIMS"; POINT_X/POINT_Y vs LATITUDE/LONGITUDE; local_report_number): https://tims.berkeley.edu/help/crashdata/switrs-codebook.php
- TIMS terms of use, licence agreement, §409 and CPRA litigation text, Caltrans note: https://tims.berkeley.edu/about.php#terms
- TIMS FAQ (free account, approved instantly; quarterly updates): https://tims.berkeley.edu/help/general/faqs.php
- LAPD dataset page (no longer updated, new RMS dataset pending; data last updated 2025-03-11; CC0 1.0; addresses to the nearest hundred block; missing locations as 0,0): https://data.lacity.org/Public-Safety/Traffic-Collision-Data-from-2010-to-Present/d5tf-ez2w/about_data
- DataSF licence: ODC PDDL 1.0, quarterly (Socrata view metadata https://data.sf.gov/api/views/ubvf-ztfx.json)
- Caltrans 2024 Crash Data on California State Highways, prepared 03/18/2026 (statewide table p.10, 5-year freeway trend p.9; excludes crashes "associated with" state highways, suicides and beat 902): https://dot.ca.gov/-/media/dot-media/programs/research-innovation-system-information/documents/annual-collision-data/2024-crash-data-on-cshwy-book-v3-a11y.pdf
- Caltrans SHS crash data request form (PDF output only; CPRA for non-Caltrans projects; 10 years + current): https://dot.ca.gov/-/media/dot-media/programs/safety-programs/documents/caltrans-crash-data-request-form-a11y.pdf
- Caltrans OHSIP / TASAS branch (TSN database, postmile coding of SHS crashes): https://dot.ca.gov/programs/research-innovation-system-information/about-research-innovation-system-information/highway-system-information-and-performance
- FARS Encyclopedia, fatalities by state 2024 (1st release) vs 2023, CA 3,876 / 4,169; CA 2024 fatal crashes 3,583: https://www-fars.nhtsa.dot.gov/states/statescrashesandallvictims.aspx
- Secondary, not verified: TIMS 2023 fatal+injury crashes = 163,848 (quoted by a law-firm page citing a TIMS snapshot of 2026-06-08): https://gjel.com/car-accident-lawyers/california-car-accident-statistics

For #19 (state pack outline)
- WSDOT crash data dictionary (Collision Report Type by trafficway jurisdiction; Primary Trafficway → State Route ID or County Road #; Block Number; Milepost; Intersecting Trafficway; County Road MP): https://wsdot.wa.gov/sites/default/files/2022-01/NHFP-crash-data-dictionary.pdf
- WSDOT crash data page (15 years + current retained; final each July; public requests via Public Disclosure Request Center): https://www.wsdot.wa.gov/mapsdata/crash/crashdata.htm
- WSDOT portal, WSDOT vs FARS fatality criteria (WSDOT keeps deaths beyond 30 days if on the PTCR): https://remoteapps.wsdot.wa.gov/highwaysafety/collision/data/portal/public/mobile.html
- Austin crash dataset sourced from CRIS (columns rpt_block_num, rpt_street_name, onsys_fl, latitude/longitude, crash_sev_id): https://data.austintexas.gov/api/views/y2wy-tgr5.json
- NY, MA, TX, WA access/licence/severity facts: `research_notes/state-research-2026-10-18/` (issue #4).
