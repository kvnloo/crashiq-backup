"""CrashIQ web app: FastAPI serves the JSON API and, in production, the React build (one service).

Run locally:  make backend   (uvicorn on :8000; the Vite dev server on :3000 proxies /api here)

Every route except /health sits behind `require_auth`, which is a no-op unless APP_PASSWORD is set
(DemandIQ pattern). Routers for each component (study, network, crashes, profile, …) are added in
`create_app` as their issues land.
"""

from __future__ import annotations

import os
import secrets
from pathlib import Path

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles

from .db import Database
from .settings import Settings

VERSION = "0.1.0"
_basic = HTTPBasic(auto_error=False)


def _strip_api_prefix(app):
    """ASGI middleware: `/api/x` → `/x`, so prod (one origin) and dev (Vite proxy strips /api) see the same paths."""

    async def middleware(scope, receive, send):
        if scope["type"] == "http":
            path = scope.get("path", "")
            if path == "/api" or path.startswith("/api/"):
                scope = dict(scope)
                scope["path"] = path[4:] or "/"
                raw = scope.get("raw_path")
                if raw and raw.startswith(b"/api"):
                    scope["raw_path"] = raw[4:] or b"/"
        await app(scope, receive, send)

    return middleware


def create_app(settings: Settings | None = None, db: Database | None = None) -> FastAPI:
    settings = settings or Settings()
    db = db or Database(settings.db_path)
    app = FastAPI(title="CrashIQ", version=VERSION, docs_url=None, redoc_url=None)
    app.state.settings = settings
    app.state.db = db

    def require_auth(creds: HTTPBasicCredentials | None = Depends(_basic)) -> None:
        if not settings.app_password:
            return
        ok = creds is not None and secrets.compare_digest(
            creds.password.encode("utf-8"), settings.app_password.encode("utf-8"))
        if not ok:
            raise HTTPException(401, "Wrong or missing password", headers={"WWW-Authenticate": "Basic"})

    @app.get("/health")
    def health() -> dict:
        return {"ok": True, "version": VERSION}

    api = APIRouter(dependencies=[Depends(require_auth)])

    @api.get("/config")
    def config() -> dict:
        """What the frontend may know about the server. Key *presence* only, never values."""
        return {
            "version": VERSION,
            "ai": {"claude_configured": bool(settings.anthropic_api_key),
                   "jev_configured": bool(settings.typesafe_api_key)},
        }

    if settings.fixtures_dir:
        _use_fixtures(app, settings.fixtures_dir)
    _mount_routers(api, app)
    app.include_router(api)

    @app.exception_handler(ValueError)
    async def bad_input(_: Request, exc: ValueError):
        return JSONResponse({"detail": str(exc)}, status_code=422)

    _mount_spa(app, settings.dist_dir, require_auth)
    app.router.add_event_handler("shutdown", db.close)
    return _AppWithPrefix(app)


def _mount_routers(api: APIRouter, app: FastAPI) -> None:
    """Component routers register here (one line per issue)."""
    from . import assign, crashes, network, profile, study

    api.include_router(study.router)
    api.include_router(network.router)
    api.include_router(crashes.router)
    api.include_router(assign.router)
    api.include_router(profile.router)


def _use_fixtures(app: FastAPI, folder: Path) -> None:
    """Offline demo mode: Overpass returns the recorded Crenshaw response; CKAN runs on the fixture datastore."""
    overpass = folder / "overpass_crenshaw.json"
    if overpass.exists():
        app.state.overpass = lambda url, data, timeout: overpass.read_bytes()
    ckan = folder / "ckan_crenshaw.json"
    if ckan.exists():
        from .sources.fake_ckan import FakeCkan

        app.state.ckan = FakeCkan(ckan)


def _mount_spa(app: FastAPI, dist: Path, require_auth) -> None:
    """Serve the Vite build at / with client-side routing. Skipped in dev (no build)."""
    index = dist / "index.html"
    if not index.exists():
        return
    if (dist / "assets").exists():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False, dependencies=[Depends(require_auth)])
    def spa(full_path: str):
        candidate = (dist / full_path).resolve()
        if full_path and candidate.is_file() and dist.resolve() in candidate.parents:
            return FileResponse(candidate)
        return FileResponse(index)


class _AppWithPrefix:
    """Wraps the FastAPI app with the /api prefix strip while keeping `.state` etc. reachable."""

    def __init__(self, app: FastAPI):
        self._app = app
        self._asgi = _strip_api_prefix(app)

    async def __call__(self, scope, receive, send):
        await self._asgi(scope, receive, send)

    def __getattr__(self, name):
        return getattr(self._app, name)


def _default_app():
    return create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("crashiq.server:_default_app", factory=True, host="0.0.0.0",
                port=int(os.getenv("PORT", "8000")))
