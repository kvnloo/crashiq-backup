"""#383: the hosted container fails closed, starts on an empty disk, and every route but /health needs the password.
The image and blueprint files are checked here too; `docker build` itself runs outside `make test` (docs/runbook)."""

import re

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from crashiq.server import create_app
from crashiq.settings import ROOT

from conftest import make_settings


def test_a_hosted_app_refuses_to_start_without_a_password(tmp_path):
    with pytest.raises(RuntimeError, match="APP_PASSWORD"):
        create_app(make_settings(tmp_path, hosted=True))
    assert not (tmp_path / "test.sqlite").exists()                      # stopped before touching the disk


def _api_routes(routes):
    """Every APIRoute, including those inside included routers (no router here has a prefix)."""
    for r in routes:
        if isinstance(r, APIRoute):
            yield r
        elif hasattr(r, "original_router"):
            yield from _api_routes(r.original_router.routes)


def test_on_an_empty_disk_health_is_open_and_every_other_route_needs_the_password(tmp_path):
    disk = tmp_path / "var" / "data"                                    # nothing there yet, not even the folder
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<div id=root></div>")
    s = make_settings(tmp_path, hosted=True, app_password="pw", db_path=disk / "crashiq.sqlite", dist_dir=dist)
    app = create_app(s)
    with TestClient(app) as c:
        assert (disk / "crashiq.sqlite").exists()                       # the app made its database
        assert c.get("/api/health").json()["ok"] is True
        routes = [r for r in _api_routes(app.routes) if r.path != "/health"]
        assert len(routes) > 30
        for r in routes:
            path = "/api" + re.sub(r"\{[^}]+\}", "x", r.path)
            for m in r.methods - {"HEAD"}:
                assert c.request(m, path).status_code == 401, (m, path)
        assert c.get("/").status_code == 401 and c.get("/s/abc/corridor").status_code == 401   # the app itself
        for p in ("/openapi.json", "/docs", "/redoc"):          # the route list isn't public either
            assert c.get(p).status_code in (401, 404), p
        assert c.get("/api/config", auth=("u", "pw")).status_code == 200
        assert "root" in c.get("/", auth=("u", "pw")).text


def test_the_image_writes_only_to_the_disk_and_ships_no_data_or_secrets():
    docker = (ROOT / "Dockerfile").read_text()
    assert "CRASHIQ_HOSTED=1" in docker
    envs = set(re.findall(r'getenv\("(CRASHIQ_\w+)"', (ROOT / "backend/crashiq/settings.py").read_text()))
    for name in envs - {"CRASHIQ_HOSTED", "CRASHIQ_FIXTURES_DIR"}:          # every path the app writes: on /var/data
        assert re.search(rf"{name}=/var/data/", docker), name
    assert "CRASHIQ_FIXTURES_DIR" not in docker
    ignore = [ln for ln in (ROOT / ".dockerignore").read_text().split("\n") if ln and not ln.startswith("#")]
    assert ignore[0] == "**" and "!data/" not in ignore                  # deny by default; only data/reference, aliases
    assert {"!data/reference/", "!data/aliases/", "**/.env", "**/*.sqlite*"} <= set(ignore)


def test_render_blueprint_keeps_the_password_out_of_the_repo_and_ai_off():
    y = "\n".join(ln for ln in (ROOT / "render.yaml").read_text().split("\n") if not ln.startswith("#"))
    assert re.search(r"- key: APP_PASSWORD\n\s+sync: false", y)
    assert "ANTHROPIC_API_KEY" not in y and "TYPESAFE_API_KEY" not in y
    assert "healthCheckPath: /api/health" in y and "mountPath: /var/data" in y


def test_osm_attribution_is_in_both_exports():
    import dataclasses
    from crashiq import packs
    from crashiq.export import CREDITS, credits
    assert "© OpenStreetMap contributors (ODbL)" in CREDITS
    other = dataclasses.replace(packs.get("CA"), code="ZZ", caltrans=False, source="Crash data: test.")
    assert credits(packs.get("CA")) == CREDITS and "© OpenStreetMap contributors (ODbL)" in credits(other)   # #19
    src = (ROOT / "backend/crashiq/export.py").read_text()
    assert '("Sources", credits(pack))' in src and "Paragraph(escape(credits(pack))" in src  # XLSX notes, PDF last page
