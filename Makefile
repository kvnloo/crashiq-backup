# CrashIQ commands. First time: `make setup`.
PY := .venv/bin/python
export PYTHONPATH := backend

.PHONY: setup backend frontend test test-backend test-frontend lint build serve

setup:            ## install backend venv + frontend packages
	python3 -m venv .venv && .venv/bin/pip install -q -r backend/requirements.txt
	cd frontend && npm ci

backend:          ## API on :8000 (auto-reload)
	$(PY) -m uvicorn crashiq.server:_default_app --factory --reload --app-dir backend --port 8000

frontend:         ## app on :3000, proxies /api to :8000
	cd frontend && npm run dev

test: test-backend test-frontend   ## all tests (no network)

test-backend:
	$(PY) -m pytest -q

test-frontend:
	cd frontend && npm test

lint:             ## ruff (backend) + eslint (frontend)
	$(PY) -m ruff check backend tests
	cd frontend && npm run lint

build:            ## production frontend build into frontend/dist
	cd frontend && npm run build

serve: build      ## one process serves API + built app on :8000 (what Render runs)
	$(PY) -m crashiq.server
