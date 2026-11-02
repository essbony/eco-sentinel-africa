"""Modèles d'alerte Eco Sentinel."""

from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, Field


class AlertSeverity(StrEnum):
    info = "info"
    warning = "warning"
    critical = "critical"


class Alert(BaseModel):
    alert_id: str = Field(default_factory=lambda: str(uuid4()))
    event_id: str
    source_id: str
    severity: AlertSeverity
    risk_level: str
    title: str
    description: str
    rule_id: str
    confidence: float | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    deduplication_key: str
    simulated: bool = False
