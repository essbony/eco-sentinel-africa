"""Exceptions métier Eco Sentinel."""


class AppError(Exception):
    """Erreur applicative de base."""


class NotFoundError(AppError):
    """Ressource introuvable."""


class ValidationError(AppError):
    """Données invalides."""


class VisionError(AppError):
    """Erreur du service Vision."""


class OrchestrationError(AppError):
    """Erreur d'orchestration A2A / Router."""


class IngestionError(AppError):
    """Erreur ingestion vidéo."""


class RateLimitError(AppError):
    """Limite de débit atteinte."""
