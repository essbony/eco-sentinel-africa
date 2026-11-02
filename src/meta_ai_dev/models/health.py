"""Modèles de santé / statut — fonctionne avec ou sans pydantic."""

from datetime import UTC, datetime

try:
    from pydantic import BaseModel, Field

    class HealthResponse(BaseModel):
        status: str = Field(default="ok")
        app: str = Field(default="meta-ai-dev")
        version: str = Field(default="0.1.0")
        timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

except ImportError:
    from dataclasses import dataclass, field

    @dataclass
    class HealthResponse:  # type: ignore[no-redef]
        status: str = "ok"
        app: str = "meta-ai-dev"
        version: str = "0.1.0"
        timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
