# CrashIQ: one service (#383, docs/03 R8). The API and the built app on $PORT, the same as `make serve`.
# Everything the app writes (SQLite, downloaded caches) goes under /var/data, the persistent disk on Render.

FROM node:22-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app/backend \
    CRASHIQ_HOSTED=1 PORT=8000 \
    CRASHIQ_DB=/var/data/crashiq.sqlite \
    CRASHIQ_FILES_DIR=/var/data/cache/ccrs_files \
    CRASHIQ_TIGER_DIR=/var/data/cache/tiger \
    CRASHIQ_NAD_DIR=/var/data/cache/nad \
    CRASHIQ_ADDRFEAT_DIR=/var/data/cache/tiger_addrfeat \
    CRASHIQ_POSTMILE_DIR=/var/data/cache/postmiles \
    CRASHIQ_AADT_DIR=/var/data/cache/aadt
WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend/ backend/
COPY data/reference/ data/reference/
COPY data/aliases/ data/aliases/
COPY --from=frontend /app/frontend/dist frontend/dist
RUN useradd --create-home crashiq && mkdir -p /var/data && chown crashiq /var/data
USER crashiq
EXPOSE 8000
CMD ["python", "-m", "crashiq.server"]
