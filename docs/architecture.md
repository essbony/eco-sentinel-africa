# Architecture

- `src/meta_ai_dev/config` — settings 12-factor (pydantic-settings)
- `src/meta_ai_dev/core` — logging, exceptions transverses
- `src/meta_ai_dev/models` — schémas Pydantic
- `src/meta_ai_dev/services` — logique métier
- `src/meta_ai_dev/api` — FastAPI (extra `api`)
- `src/meta_ai_dev/utils` — helpers purs

Principes : `src` layout, `.venv` local via `uv`, `pyproject.toml` unique source de vérité.
