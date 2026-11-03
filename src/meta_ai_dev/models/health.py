"""Compat shim — modèle HealthResponse (conservé pour compatibilité tests)."""

from datetime import UTC, datetime

try:
    from pydantic import BaseModel, Field

    class HealthResponse(BaseModel):  # type: ignore[no-redef]
        status: str = Field(default="ok")
        app: str = Field(default="eco-sentinel-africa")
        version: str = Field(default="0.1.0")
        timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

except ImportError:
    from dataclasses import dataclass, field

    @dataclass
    class HealthResponse:  # type: ignore[no-redef]
        status: str = "ok"
        app: str = "eco-sentinel-africa"
        version: str = "0.1.0"
        timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
