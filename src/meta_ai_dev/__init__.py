"""Meta AI Dev — package racine."""

from meta_ai_dev.config.settings import get_settings

__all__ = ["get_settings", "main"]
__version__ = "0.1.0"


def main() -> None:
    settings = get_settings()
    print(f"Hello from {settings.app_name} v{__version__} [{settings.env}]")
