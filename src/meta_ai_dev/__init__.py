"""Compat shim — ré-exporte eco_sentinel (conservé pour compatibilité)."""

from eco_sentinel.config.settings import get_settings

__all__ = ["get_settings", "main"]
__version__ = "0.1.0"


def main() -> None:
    from eco_sentinel.main import main as eco_main

    eco_main()
