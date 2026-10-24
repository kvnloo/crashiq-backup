"""Settings from the environment. Read once per app instance; tests pass their own.

Secrets (APP_PASSWORD, ANTHROPIC_API_KEY, TYPESAFE_API_KEY) stay server-side: they are never
returned by an endpoint, logged, or sent to the frontend. Only their presence is exposed.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # repo root


def _float(name: str, default: float) -> float:
    raw = os.getenv(name)
    return float(raw) if raw not in (None, "") else default


@dataclass(frozen=True)
class Settings:
    db_path: Path = field(default_factory=lambda: Path(os.getenv("CRASHIQ_DB", ROOT / "data" / "crashiq.sqlite")))
    app_password: str | None = field(default_factory=lambda: os.getenv("APP_PASSWORD") or None)
    anthropic_api_key: str | None = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY") or None, repr=False)
    typesafe_api_key: str | None = field(default_factory=lambda: os.getenv("TYPESAFE_API_KEY") or None, repr=False)
    # Per-study AI spend cap in USD (C15). Default proposed in PR #14, for the user to confirm.
    study_ai_cap_usd: float = field(default_factory=lambda: _float("STUDY_AI_CAP_USD", 1.00))
    # Offline demo: answer Overpass/CKAN from recorded files in this folder instead of the network.
    # Never set in production. Used for screenshots in the build sandbox, which can't reach those hosts.
    fixtures_dir: Path | None = field(default_factory=lambda: Path(os.environ["CRASHIQ_FIXTURES_DIR"])
                                      if os.getenv("CRASHIQ_FIXTURES_DIR") else None)
    # CHP files for CCRS tables not in the data.ca.gov datastore (#196): ~50 MB each, never committed
    ccrs_files_dir: Path = field(default_factory=lambda: Path(os.getenv("CRASHIQ_FILES_DIR",
                                                                        ROOT / "data" / "cache" / "ccrs_files")))
    # Census TIGER/Line roads per county (#229): a few MB each (Los Angeles ~60 MB), never committed
    tiger_dir: Path = field(default_factory=lambda: Path(os.getenv("CRASHIQ_TIGER_DIR", ROOT / "data" / "cache" / "tiger")))
    # Caltrans SHN Postmiles Tenth (#248): ~30 MB, never committed
    postmile_dir: Path = field(default_factory=lambda: Path(os.getenv("CRASHIQ_POSTMILE_DIR",
                                                                        ROOT / "data" / "cache" / "postmiles")))
    # Frontend build served by the same process in production (single service, DemandIQ pattern).
    dist_dir: Path = field(default_factory=lambda: ROOT / "frontend" / "dist")

    def __repr__(self) -> str:  # never print secrets
        return f"Settings(db_path={self.db_path!s}, auth={'on' if self.app_password else 'off'})"
