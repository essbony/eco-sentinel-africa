"""Service de health-check."""

from meta_ai_dev.config.settings import get_settings
from meta_ai_dev.models.health import HealthResponse


class HealthService:
    def check(self) -> HealthResponse:
        settings = get_settings()
        return HealthResponse(app=settings.app_name)
