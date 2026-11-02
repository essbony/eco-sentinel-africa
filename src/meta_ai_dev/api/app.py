"""FastAPI factory (optionnel — extra `api`)."""

try:
    from fastapi import FastAPI

    from meta_ai_dev.api.routes import router

    def create_app() -> FastAPI:  # type: ignore[misc]
        app = FastAPI(title="meta-ai-dev", version="0.1.0")
        app.include_router(router)
        return app

    app = create_app()

except ImportError:

    def create_app() -> None:  # type: ignore[no-redef,misc]
        raise RuntimeError("Installe l'extra api : `uv sync --extra api`")

    app = None  # type: ignore[assignment]
