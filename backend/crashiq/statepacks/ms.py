"""Mississippi: DPS eCrash public data workbooks, statewide (sources/ms_dps.py)."""

from crashiq.packs import REF, StatePack


def _fetch(box, county_fips, years, cache_dir):
    from crashiq.sources import ms_dps
    return ms_dps.fetch_contract(box, county_fips, years, cache_dir)


PACK = StatePack(
    code="MS", name="Mississippi", fips="28", status="active",
    source="Crash data: eCrash public data, Mississippi Department of Public Safety (publicdata.dps.ms.gov; police "
           "crash reports; no published reuse licence).",
    source_short="DPS eCrash public data", bounds=(30.0, -91.8, 35.1, -88.0), first_year=2020,
    methods=REF / "methods_ms.json", fetch=_fetch, county_boxes=REF / "county_boxes_ms.json",
    final_lag_months=14,                         # DPS posted the final 2024 file on 2026-02-05; 2025 is a DRAFT
    # DPS's public data page, quoted (research_notes/ms-2026-11-08/ms-import.md §2)
    legal=("Mississippi DPS: \"These data sets are typically used to respond to public records requests and made "
           "available to the public free of charge.\" Safety studies: 23 U.S.C. 407."),
    data_notes=("Mississippi's public crash file has no manner of collision and no driver movements: collision type "
                "is filled only for pedestrian crashes, and road-user movements and collision diagrams are empty.",
                "The first pull of a year downloads DPS's whole yearly workbook (about 100 MB) and takes a few "
                "minutes; later pulls read the saved copy.",
                "Primary collision factor rows are blank: CrashIQ doesn't map Mississippi's contributing "
                "circumstances to them yet."),
)
