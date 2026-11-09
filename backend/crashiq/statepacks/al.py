"""Alabama state pack (#19 plug-in): the CARE eCrash map layer (University of Alabama CAPS, every Alabama eCrash
report 2020 on), placed by GPS, or by street names where CARE has no point."""

from crashiq.packs import REF, StatePack


def _fetch(box, county_fips, years, cache_dir):
    from crashiq.sources import al_care
    return al_care.fetch_contract(box, county_fips, years, cache_dir)


PACK = StatePack(
    code="AL", name="Alabama", fips="01",
    # not offered: ALDOT's own guidebook says these data "are not to be shared with the public" (al-import.md § Licence);
    # the open layer works end to end, but needs ALDOT/CAPS permission first
    status="reader_only",
    source="Crash data: CARE eCrash layer, University of Alabama Center for Advanced Public Safety (Alabama eCrash "
           "police reports; public map service, no published reuse licence).",
    source_short="CARE eCrash layer", bounds=(30.1, -88.6, 35.1, -84.8), first_year=2020,
    methods=REF / "methods_al.json", fetch=_fetch, county_boxes=REF / "county_boxes_al.json",
    # ALDOT's suggested admonition, quoted (Safety Data Access Guidebook, p. 20)
    legal=("ALDOT: \"This document is exempt from open records, discovery or admission under Alabama Law and 23 U.S.C. "
           "§§ 148(h)(4) and 409.\""),
    data_notes=("CARE's public crash layer has no person or vehicle table, only the causal unit and a second "
                "vehicle on the crash row: road-user movements and collision diagrams are empty.",
                "About 14% of crashes have no point; CrashIQ places those from the officer's street and cross street "
                "and lists the rest as unplaced.",
                "Since April 2025, CARE loaded most text columns two places to the left; CrashIQ reads each value "
                "from where it landed. The 2% of crashes CARE marks 'Unknown' severity aren't counted.",
                "Primary collision factor, DUI and speed rows are blank: CrashIQ doesn't read CARE's cause codes as "
                "violation codes.",
                "Crashes count as freeway crashes only when CARE files them under Interstate.",
                "Birmingham's street grid repeats names north and south (3rd Ave N, 3rd Ave S): CrashIQ's street "
                "names drop that last letter, so a crash with no point can be placed on the wrong one; check "
                "name-placed crashes by hand (research_notes/al-2026-11-08/shared-fixes.md)."))
