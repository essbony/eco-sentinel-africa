# syntax=docker/dockerfile:1

# ── Stage 1 : builder ──────────────────────────────────────────────
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# uv pour une installation rapide et reproductible
RUN pip install --no-cache-dir uv

# Manifests d'abord (cache Docker optimal)
COPY pyproject.toml uv.lock README.md ./
COPY src/ src/

# Installe deps prod + extra api (FastAPI) + eval (deepeval).
# --frozen respecte uv.lock. `eval` est inclus pour que l'image serve aussi au service deepeval.
RUN uv sync --frozen --extra api --extra eval --no-dev 2>/dev/null \
    || uv sync --extra api --extra eval --no-dev \
    || pip install --no-cache-dir -e ".[api,eval]"

# ── Stage 2 : runtime ────────────────────────────────────────────
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_NAME=eco-sentinel-africa \
    ENV=production \
    API_HOST=0.0.0.0 \
    API_PORT=8000

WORKDIR /app

RUN groupadd --system app && useradd --system --gid app --create-home app \
    && apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Venv du builder (contient toutes les deps)
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/pyproject.toml /app/pyproject.toml
COPY --from=builder /app/README.md /app/README.md

# Code source + configs (prod : pas de hot-reload, copie figée)
COPY --chown=app:app src/ src/
COPY --chown=app:app configs/ configs/

ENV PATH="/app/.venv/bin:$PATH" \
    VIRTUAL_ENV="/app/.venv"

EXPOSE 8000
USER app

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -sf http://localhost:8000/health || curl -sf http://localhost:${API_PORT:-8000}/health || exit 1

CMD ["uvicorn", "eco_sentinel.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
