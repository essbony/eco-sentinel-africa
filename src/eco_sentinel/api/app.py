"""FastAPI Eco Sentinel Africa — factory avec pipeline complet (SDK A2A)."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from eco_sentinel.api.routes import router
from eco_sentinel.core.logging import get_logger

logger = get_logger("eco_sentinel.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Eco Sentinel Africa starting — pipeline autonome prêt")
    from eco_sentinel.api.worker import start_worker, stop_worker

    # Initialise les agents A2A (enregistre classification/geo/research/analysis/report)
    from eco_sentinel.orchestration.router import _ensure_agents

    _ensure_agents()
    # Monte les endpoints SDK A2A (/.well-known/agent-card.json + JSON-RPC)
    try:
        from eco_sentinel.a2a.sdk import mount_a2a_routes

        mount_a2a_routes(app)
    except Exception as e:
        logger.warning("Montage A2A SDK échoué (mode bus seul): %s", e)

    await start_worker()
    yield
    await stop_worker()
    logger.info("Eco Sentinel Africa stopping")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Eco Sentinel Africa",
        version="0.1.0",
        description=(
            "Système autonome de surveillance environnementale — "  # noqa: E501
            "Vision SAM 3.1 + Router Wonder + Agents Spark via Meta API (Responses) — "  # noqa: E501
            "A2A SDK 0.3.26"
        ),
        lifespan=lifespan,
    )
    # CORS : étoile en dev, origines explicites en prod (via CORS_ORIGINS)
    from eco_sentinel.config.settings import get_settings

    settings = get_settings()
    cors_origins = ["*"] if settings.env != "production" else settings.cors_origins_list
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,  # nosemgrep
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)
    return app


app = create_app()
