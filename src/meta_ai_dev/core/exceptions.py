"""Exceptions métier."""


class AppError(Exception):
    """Erreur applicative de base."""


class NotFoundError(AppError):
    """Ressource introuvable."""


class ValidationError(AppError):
    """Données invalides."""
