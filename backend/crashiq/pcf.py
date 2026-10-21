"""Primary collision factor category from CCRS's violation text (#52, user decision 1A).

CCRS publishes only the Vehicle Code section, written many ways ('VC 22350', '22350', 'VC 21658(A)', '21453A',
'22107 CVC', 'VC 21651(A1)'), sometimes words ('UNSAFE BACKING') or nothing. The section -> category table is CHP's
own, rebuilt from SWITRS records (data/reference/pcf_categories.csv, method in its .md): a key is mapped only when
>= 99% of its records agree. Everything else stays visible as its own row; nothing is guessed."""

from __future__ import annotations

import csv
import re
from functools import lru_cache

from .settings import ROOT

FILE = ROOT / "data" / "reference" / "pcf_categories.csv"

_SECTION = re.compile(r"^(?:C?VC\s*)?(\d{2,5})\s*(?:[.(]?\s*([A-Z0-9])[A-Z0-9]*\s*\)?)?\s*$")
_SUFFIX = re.compile(r"\s+C?VC\.?$")             # '22107 CVC', '22350 VC': the code written after the section

# Rows that aren't a category, in the order they're listed after the categories
OTHER = {
    "blank": "Not stated (no violation on the report)",
    "words": "Written in words, not a code section",
    "unknown": "Unknown (CHP's own table gives 00)",
    "split": "Category changed by year, none in 2024",
    "unlisted": "Section not in CHP's table",
}


def parse(text) -> tuple[str, str] | str:
    """(section, subsection letter) | 'blank' | 'words'."""
    t = re.sub(r"\s+", " ", str(text or "").strip().upper())
    if not t:
        return "blank"
    m = _SECTION.match(_SUFFIX.sub("", t))
    return (m.group(1), m.group(2) or "") if m else "words"


# CHP extended its own table in 2024: 18 keys it gave 00 (or another category) in 2021-23 have a real category in
# 2024. User decision 2026-10-20 (docs/03): use the 2024 category for every year, so one violation counts the same
# way across a study. A split key whose 2024 category is 00 is unknown; one with no 2024 records stays split.
SPLIT_YEAR = "2024"


def _year_category(split_by_year: str, year: str) -> str | None:
    """'2021 00:56; 2024 10:39' -> '10' for 2024."""
    for part in (split_by_year or "").split(";"):
        bits = part.split()
        if len(bits) == 2 and bits[0] == year:
            return bits[1].split(":")[0]
    return None


@lru_cache(maxsize=1)
def table() -> dict[tuple[str, str], tuple[str, str, str]]:
    """(section, subsection) -> (status, category code, category label), section keys only."""
    with FILE.open(newline="") as f:
        rows = list(csv.DictReader(f))
    names = {r["category"]: r["category_label"] for r in rows if r["status"] == "mapped"}
    out = {}
    for r in rows:
        if r["key_type"] != "section":
            continue
        status, code = r["status"], r["category"]
        if status == "split":
            y = _year_category(r["split_by_year"], SPLIT_YEAR)
            if y is not None:
                status, code = ("unknown", "00") if y == "00" else ("mapped", y)
        out[(r["section"], r["subsection"])] = (status, code, names.get(code, r["category_label"]))
    return out


def category(text) -> str:
    """'03' (a mapped category code) or one of OTHER's keys."""
    p = parse(text)
    if isinstance(p, str):
        return p
    hit = table().get(p)
    if hit is None:
        return "unlisted"
    status, code, _ = hit
    return code if status == "mapped" else status


@lru_cache(maxsize=1)
def labels() -> dict[str, str]:
    """Category code -> official SWITRS label, for every mapped category in the table."""
    return {code: label for status, code, label in table().values() if status == "mapped"}
