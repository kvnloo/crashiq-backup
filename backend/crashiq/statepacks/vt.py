"""Vermont: VTrans' open crash layer (sources/vt_vtrans.py). Research: research_notes/vt-2026-11-08/."""

from crashiq.packs import REF, StatePack


def _fetch(box, county_fips, years, cache_dir):
    from crashiq.sources import vt_vtrans
    return vt_vtrans.fetch_contract(box, county_fips, years, cache_dir)


PACK = StatePack(
    code="VT", name="Vermont", fips="50", status="active",
    source="Crash data: VTrans Public Crash Data Query Tool data (CrashPQT, Vermont Agency of Transportation, open "
           "ArcGIS layer; no open licence, VTrans disclaimer).",
    source_short="VTrans crash data", bounds=(42.6, -73.5, 45.1, -71.4), first_year=2010,
    methods=REF / "methods_vt.json", fetch=_fetch, county_boxes=REF / "county_boxes_vt.json",
    # the Public Crash Data Query Tool's disclaimer, quoted (research_notes/vt-2026-11-08/vt-import.md § Licence)
    legal=("VTrans: \"Errors or Omissions may occur in the data or queries. Only non-personal data is included for "
           "analysis in this tool. Users assume responsibility for the queries they create. This data is exempt from "
           "discovery or admission under 23 U.S.C. 409.\""),
    severity_note=("Vermont's crash data doesn't report injury levels: a crash is fatal, injury or property damage "
                   "only. KSI here is fatal crashes only, and there is no A/B/C split; injury crashes are counted as "
                   "'injury, level not reported' (U)."),
    data_notes=("VTrans' public crash layer has no driver, vehicle or person records and no counts of people killed "
                "or injured: road-user movements and collision diagrams are empty, and people aren't counted.",
                "Crashes VTrans lists as non-reportable (no injury level, only an address) aren't read.",
                "Light is day or night only; night crashes count as dark with street lighting unknown.",
                "Primary collision factor, DUI and speed rows are blank: CrashIQ doesn't map VTrans' impairment "
                "field yet."))
