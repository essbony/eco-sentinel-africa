"""API layer."""

try:
    from meta_ai_dev.api.app import app

    __all__ = ["app"]  # type: ignore[no-redef]
except ImportError:
    __all__ = []  # type: ignore[no-redef,assignment]
