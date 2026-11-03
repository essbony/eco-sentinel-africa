"""Compat shim — ré-exporte eco_sentinel.core.exceptions."""

from eco_sentinel.core.exceptions import AppError, NotFoundError, ValidationError

__all__ = ["AppError", "NotFoundError", "ValidationError"]
