"""Routes API."""

try:
    from fastapi import APIRouter

    from meta_ai_dev.models.health import HealthResponse
    from meta_ai_dev.services.health import HealthService

    router = APIRouter()
    _health = HealthService()

    @router.get("/health", response_model=HealthResponse, tags=["ops"])
    def health() -> HealthResponse:
        return _health.check()

    @router.get("/", tags=["ops"])
    def root() -> dict[str, str]:
        return {"message": "meta-ai-dev API — voir /docs"}

except ImportError:
    router = None  # type: ignore[assignment]
