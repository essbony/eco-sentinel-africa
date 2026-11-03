"""Service health-check Eco Sentinel Africa."""

from eco_sentinel.config.settings import get_settings


class HealthService:
    def check(self) -> dict[str, str]:
        s = get_settings()
        return {"status": "ok", "app": s.app_name, "env": s.env}
