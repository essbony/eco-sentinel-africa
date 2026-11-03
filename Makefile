.PHONY: install sync lint format type test cov run api docker-build docker-up docker-down docker-logs docker-shell eval eval-docker clean security security-bandit security-pip-audit security-semgrep security-all audit

UV := uv
PY := $(UV) run python

install sync:
	$(UV) sync --all-extras

lint:
	$(UV) run ruff check src tests

format:
	$(UV) run ruff format src tests
	$(UV) run ruff check --fix src tests

type:
	$(UV) run mypy src

test:
	$(UV) run pytest

cov:
	$(UV) run pytest --cov=src --cov-report=term-missing --cov-report=html

# ── Sécurité : bandit (SAST), pip-audit (CVE), semgrep (SAST) ──
security-bandit:
	$(UV) run bandit -c pyproject.toml -r src -x tests

security-pip-audit:
	XDG_CACHE_HOME=/tmp $(UV) run pip-audit --skip-editable --desc --cache-dir /tmp/pip-audit-cache || true

security-semgrep:
	HOME=/tmp XDG_CACHE_HOME=/tmp $(UV) run semgrep --config auto --error src

security: security-bandit security-pip-audit security-semgrep

security-all: lint type security-bandit security-pip-audit security-semgrep test

audit: security-all

run:
	$(UV) run eco-sentinel

api:
	$(UV) run uvicorn eco_sentinel.api.app:app --reload --host 0.0.0.0 --port 8000

docker-build:
	docker compose build

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f app

docker-shell:
	docker compose exec app bash

eval:
	$(UV) run --extra eval deepeval test run evals/ --verbose

eval-docker:
	docker compose --profile eval run --rm deepeval

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage coverage.xml dist build
	find . -type d -name "__pycache__" -exec rm -rf {} +
