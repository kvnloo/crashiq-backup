from fastapi.testclient import TestClient

from crashiq.db import MIGRATIONS, Database
from crashiq.server import create_app

from conftest import make_settings


def test_health_is_open(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["ok"] is True


def test_api_prefix_is_stripped(client):
    assert client.get("/api/health").status_code == 200
    assert client.get("/api/config").status_code == 200


def test_auth_off_without_password(client):
    assert client.get("/config").status_code == 200


def test_password_required_when_set(tmp_path):
    s = make_settings(tmp_path, app_password="s3cret")
    with TestClient(create_app(s, Database(s.db_path))) as c:
        assert c.get("/health").status_code == 200  # health stays open for the host's probe
        assert c.get("/config").status_code == 401
        assert c.get("/config", auth=("any", "wrong")).status_code == 401
        assert c.get("/config", auth=("any", "s3cret")).status_code == 200


def test_config_reports_key_presence_not_values(tmp_path):
    s = make_settings(tmp_path, anthropic_api_key="sk-ant-SECRET", typesafe_api_key=None)
    with TestClient(create_app(s, Database(s.db_path))) as c:
        body = c.get("/config").text
    assert "SECRET" not in body
    assert '"claude_configured":true' in body.replace(" ", "")
    assert "SECRET" not in repr(s)


def test_migrations_run_once_and_upgrade_in_place(tmp_path):
    p = tmp_path / "m.sqlite"
    d = Database(p)
    v = d.one("SELECT MAX(version) AS v FROM schema_version")["v"]
    assert v == len(MIGRATIONS)
    d.close()
    d2 = Database(p)  # reopening must not re-run migrations
    assert d2.one("SELECT COUNT(*) AS n FROM schema_version")["n"] == len(MIGRATIONS)
    d2.close()


def test_spa_served_when_build_exists(tmp_path):
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<div id=root></div>")
    (dist / "assets" / "app.js").write_text("console.log(1)")
    s = make_settings(tmp_path, dist_dir=dist)
    with TestClient(create_app(s, Database(s.db_path))) as c:
        assert "root" in c.get("/").text
        assert "root" in c.get("/s/abc/corridor").text  # client-side route falls back to index
        assert c.get("/assets/app.js").status_code == 200
        assert c.get("/health").json()["ok"] is True  # API routes still win
