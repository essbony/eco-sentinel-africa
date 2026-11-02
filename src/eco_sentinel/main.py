"""Entrypoint Eco Sentinel Africa."""

from meta_ai_dev.config.settings import get_settings


def main() -> None:
    settings = get_settings()
    print(f"Eco Sentinel Africa v0.1.0 [{settings.env}] — {settings.app_name}")
    print(f"Vision: {settings.vision_model} via {settings.vision_provider}")
    print(f"Router: {settings.router_model} via {settings.router_provider}")
    print(f"API: http://{settings.api_host}:{settings.api_port} — /health /docs")


if __name__ == "__main__":
    main()
