"""Kansas state pack (#19 plug-in): KDOT "Crashes in Kansas" open layer (sources/ks_kdot.py)."""

from crashiq.packs import REF, StatePack


def _fetch(box, county_fips, years, cache_dir):
    from crashiq.sources import ks_kdot
    return ks_kdot.fetch_contract(box, county_fips, years, cache_dir)


PACK = StatePack(
    code="KS", name="Kansas", fips="20", status="active",
    source="Crash data: KDOT Crashes in Kansas (KanPlan open ArcGIS layer, from law-enforcement crash reports; no open "
           "licence, KDOT terms, 23 USC 407).",
    source_short="KDOT Crashes in Kansas", bounds=(36.9, -102.1, 40.1, -94.5), first_year=2016,
    methods=REF / "methods_ks.json", fetch=_fetch, county_boxes=REF / "county_boxes_ks.json",
    # KDOT's notice on the layer's item page, quoted (research_notes/ks-2026-11-08/ks-import.md § licence)
    legal=("KDOT: \"This material may be protected from discovery and admission into evidence in litigation pursuant "
           "to 23 USC 407. KDOT is not responsible for the accuracy of crash data contained in crash reports.\""),
    data_notes=("KDOT's public crash layer gives each crash's point and severity but no street names and no driver or "
                "vehicle records: road-user movements and collision diagrams are empty, and the report's street "
                "wording can't be checked.",
                "KDOT publishes only the crashes it could locate (about 91% of the 61,495 crashes reported in 2024); "
                "the rest are in KDOT's full system, by open-records request.",
                "Only Interstate, ramp and Turnpike crashes count as freeway crashes: a US or K route built as a "
                "freeway (Kellogg, US-54, in Wichita) isn't flagged, so check such corridors by hand.",
                "Primary collision factor, DUI and speed rows are blank: CrashIQ doesn't read KDOT's circumstance "
                "flags yet."))
