"""Compat shim."""

try:
    from eco_sentinel.api.app import app, create_app

    __all__ = ["app", "create_app"]
except ImportError:
    __all__ = []  # type: ignore[assignment]
