"""Compat shim — ré-exporte eco_sentinel.config."""

from eco_sentinel.config.settings import Settings, get_settings

__all__ = ["Settings", "get_settings"]
