"""Fields sheet (#73, PR #76 follow-up): every coded CCRS field the app reads, its live distinct values against the
CHP data dictionary (data/reference/ccrs_dictionary.json), and whether the app's own code maps each value.

"In dictionary" compares letters and digits only, against the field's listed values and its code keys and labels.
"App mapping" is read from the app module under test: an explicit map (KABCO, SURFACE_CODES) either knows the value
or not; other coded fields are cleaned and passed through as text (`clean_coded`), stated as such.
"""

from __future__ import annotations

import json
import re
import sqlite3
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from crashiq.sources import ca_ccrs as cc  # noqa: E402

DICT_TABLE = {"crashes": "crashes", "parties": "parties", "iwp": "injured_witness_passengers"}
CODED = {
    "crashes": ["collision_type", "lighting", "weather", "surface", "pcf", "pcf_category", "involved_with",
                "ped_action", "hit_run", "is_freeway", "is_preliminary", "is_deleted", "sec_direction", "sec_unit",
                "day_of_week"],
    "parties": ["party_type", "at_fault", "movement", "vehicle_type", "direction"],
    "iwp": ["extent", "person_type", "witness_only"],
}
COLS = {"crashes": cc.CRASH_COLS, "parties": cc.PARTY_COLS, "iwp": cc.IWP_COLS}


def _k(v) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(v or "").upper())


def _dict_values(entry: dict) -> set[str]:
    out = set()
    for v in entry.get("values") or []:
        for part in re.split(r"[/,;]", str(v)):
            out.add(_k(part))
    for code, label in (entry.get("codes") or {}).items():
        out |= {_k(code), _k(label), _k(f"{code} {label}")}
    return {x for x in out if x}


def _app_map(logical: str):
    """(map name, function value -> mapped?) for fields the app maps explicitly; else None."""
    if logical == "extent":
        known = {_k(x) for x in list(cc.KABCO) + list(getattr(cc, "NO_INJURY", []))}
        return "KABCO", lambda v: _k(v) in known or _k(v) == ""
    if logical == "surface":
        return "SURFACE_CODES", lambda v: str(v or "").strip().upper()[:1] in cc.SURFACE_CODES or not v
    return None


def check(mirror_db: Path, dictionary: Path, top: int = 60) -> list[dict]:
    d = json.loads(dictionary.read_text())["tables"]
    con = sqlite3.connect(mirror_db)
    meta = [(rid, t, json.loads(f)) for rid, t, f in con.execute("SELECT rid, tbl, fields FROM _meta")]
    rows = []
    for tbl, logicals in CODED.items():
        dentries = {_k(e["field"]): e for e in d[DICT_TABLE[tbl]]}
        for logical in logicals:
            counts: Counter = Counter()
            col = None
            for rid, t, fields in meta:
                if t != tbl:
                    continue
                got, _ = cc.resolve_columns(fields, {logical: COLS[tbl][logical]})
                if logical not in got:
                    continue
                col = got[logical]["id"]
                for v, n in con.execute(f'SELECT "{col}", COUNT(*) FROM "{rid}" GROUP BY 1'):
                    counts[v] += n
            if col is None:
                rows.append({"table": tbl, "field": "/".join(COLS[tbl][logical]), "logical": logical, "value": None,
                             "rows": None, "in_dictionary": None, "app_map": "column not in the live data",
                             "app_maps_value": None, "flag": "column missing"})
                continue
            entry = dentries.get(_k(col))
            allowed = _dict_values(entry) if entry else set()
            amap = _app_map(logical)
            total = sum(counts.values())
            for v, n in counts.most_common(top):
                in_dict = None if not allowed else (_k(v) in allowed or _k(v) == "" or
                                                    any(_k(v).startswith(a) for a in allowed if len(a) >= 3))
                maps = amap[1](v) if amap else None
                flag = []
                if in_dict is False:
                    flag.append("not in dictionary")
                if maps is False:
                    flag.append("app doesn't map it")
                rows.append({"table": tbl, "field": col, "logical": logical,
                             "value": "(blank)" if v in (None, "") else str(v), "rows": n,
                             "share_pct": round(100 * n / total, 2) if total else None,
                             "in_dictionary": "no dictionary list" if not allowed else ("yes" if in_dict else "no"),
                             "app_map": amap[0] if amap else "passed through as text (clean_coded)",
                             "app_maps_value": None if maps is None else ("yes" if maps else "no"),
                             "flag": "; ".join(flag)})
            if len(counts) > top:
                rows.append({"table": tbl, "field": col, "logical": logical,
                             "value": f"... {len(counts) - top} more values", "rows": sum(
                                 n for _, n in counts.most_common()[top:]), "in_dictionary": None,
                             "app_map": None, "app_maps_value": None, "flag": ""})
    con.close()
    return rows
