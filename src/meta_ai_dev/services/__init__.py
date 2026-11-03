"""Compat shim — ré-exporte eco_sentinel.services."""

from eco_sentinel.services.health import HealthService

__all__ = ["HealthService"]
