"""Jev (TypeSafe System One) for the one judgment code can't make: which candidate intersection a messy
pair of street names means. Jev only selects among code-generated candidates (or "none of these");
coordinates are computed by code. Calls are cached per street pair and capped per run.

Key: TYPESAFE_API_KEY in the environment (or ~/.typesafe/credentials), server-side only.
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path

NONE = "none of these"
INSTRUCTIONS = (
    "A police officer wrote the two street names below on a crash report in `report.city`. Officers abbreviate, "
    "misspell, swap the order, use old or informal names, write a route number for a freeway, or write the wrong "
    "suffix (St for Blvd). Which listed intersection is the officer describing? If none of them fits, answer "
    "'none of these'. Do not guess between two that fit equally."
)


def _api_key() -> str | None:
    if os.environ.get("TYPESAFE_API_KEY"):
        return os.environ["TYPESAFE_API_KEY"]
    f = Path.home() / ".typesafe" / "credentials"
    if f.is_file():
        for line in f.read_text().splitlines():
            if line.strip().startswith("TYPESAFE_API_KEY="):
                return line.split("=", 1)[1].strip().strip("'\"")
    return None


class JevPicker:
    def __init__(self, cache_path: Path, max_calls: int = 3000):
        self.cache_path, self.max_calls = cache_path, max_calls
        self.cache: dict = json.loads(cache_path.read_text()) if cache_path.exists() else {}
        self.calls = self.input_tokens = self.output_tokens = 0
        self.lock = threading.Lock()

    def pick(self, city: str, primary: str, secondary: str, labels: list[str]) -> tuple[str | None, float]:
        """Return (chosen label or None, probability). None also when over budget or the service fails."""
        key = json.dumps([city, primary, secondary, labels])
        if key in self.cache:
            return tuple(self.cache[key])
        with self.lock:
            if self.calls >= self.max_calls:
                return None, 0.0
            self.calls += 1
        from typesafe_sdk import Choice, TypeSafeClient
        try:
            with TypeSafeClient(api_key=_api_key()) as client:
                r = client.system_one(
                    state={"report": {"city": city, "primary_road": primary, "secondary_road": secondary}},
                    questions={"pick": Choice(instructions=INSTRUCTIONS, criteria={**{l: None for l in labels}, NONE: None})},
                )
        except Exception:
            return None, 0.0
        a = r.answers["pick"]
        choice = a.choice if a.choice != NONE else None
        p = float(a.probabilities.get(a.choice, 0.0)) if a.probabilities else float(a.confidence or 0.0)
        with self.lock:
            self.input_tokens += r.usage.input_tokens or 0
            self.output_tokens += r.usage.output_tokens or 0
            self.cache[key] = [choice, p]
        return choice, p

    def save(self) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_path.write_text(json.dumps(self.cache))
