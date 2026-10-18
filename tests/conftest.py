"""Shared fixtures: an app on a throwaway SQLite file, no network, no secrets from the real env."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from crashiq.db import Database
from crashiq.server import create_app
from crashiq.settings import Settings

FIXTURES = Path(__file__).parent / "fixtures"


def make_settings(tmp_path: Path, **kw) -> Settings:
    base = dict(db_path=tmp_path / "test.sqlite", app_password=None, anthropic_api_key=None,
                typesafe_api_key=None, study_ai_cap_usd=1.0, dist_dir=tmp_path / "no-dist",
                fixtures_dir=None)
    base.update(kw)
    return Settings(**base)


@pytest.fixture
def settings(tmp_path):
    return make_settings(tmp_path)


@pytest.fixture
def db(settings):
    d = Database(settings.db_path)
    yield d
    d.close()


@pytest.fixture
def client(settings, db):
    with TestClient(create_app(settings, db)) as c:
        yield c
