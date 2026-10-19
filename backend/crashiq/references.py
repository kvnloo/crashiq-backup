"""Methods and their sources (config/references.json), shared by the References page and the PDF."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter

FILE = Path(__file__).parent / "config" / "references.json"


@lru_cache(maxsize=1)
def load() -> dict:
    data = json.loads(FILE.read_text())
    for m in data["methods"]:                      # every citation must point at a listed source
        for key, _ in m["cite"]:
            if key not in data["sources"]:
                raise ValueError(f"references.json: unknown source '{key}' in {m['topic']}")
    return data


def cited_sources() -> list[dict]:
    """Sources in first-cited order (for the PDF's reference list)."""
    data, seen, out = load(), set(), []
    for m in data["methods"]:
        for key, _ in m["cite"]:
            if key not in seen:
                seen.add(key)
                out.append({"key": key, **data["sources"][key]})
    return out


router = APIRouter()


@router.get("/references")
def get_references() -> dict:
    return load()
