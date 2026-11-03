"""Compat shim — ré-exporte eco_sentinel.api.app."""

from eco_sentinel.api.app import app, create_app

__all__ = ["app", "create_app"]
