"""Contrat d'événement versionné — cœur du pipeline Eco Sentinel."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class EventType(StrEnum):
    potential_environmental_incident = "potential_environmental_incident"
    waste_accumulation = "waste_accumulation"
    persistent_presence = "persistent_presence"
    recurrence = "recurrence"


class DetectionStatus(StrEnum):
    detected = "detected"
    not_detected = "not_detected"
    uncertain = "uncertain"


class AnalysisStatus(StrEnum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    failed = "failed"


class RiskLevel(StrEnum):
    unassessed = "unassessed"
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class AlertStatus(StrEnum):
    not_evaluated = "not_evaluated"
    pending = "pending"
    triggered = "triggered"
    suppressed = "suppressed"
    acknowledged = "acknowledged"


class BoundingBox(BaseModel):
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    width: float = Field(ge=0, le=1)
    height: float = Field(ge=0, le=1)


class DetectionResult(BaseModel):
    category: str
    score: float | None = Field(default=None, ge=0, le=1)
    bbox: BoundingBox | None = None
    mask_ref: str | None = None
    tracking_id: str | None = None


class DetectionInfo(BaseModel):
    model: str = Field(default="sam-3.1")
    status: DetectionStatus = DetectionStatus.not_detected
    results: list[DetectionResult] = Field(default_factory=list)
    raw_ref: str | None = None


class Location(BaseModel):
    latitude: float | None = None
    longitude: float | None = None
    zone: str | None = None

    @field_validator("latitude")
    @classmethod
    def validate_lat(cls, v: float | None) -> float | None:
        if v is not None and not (-90 <= v <= 90):
            raise ValueError("latitude hors bornes")
        return v

    @field_validator("longitude")
    @classmethod
    def validate_lon(cls, v: float | None) -> float | None:
        if v is not None and not (-180 <= v <= 180):
            raise ValueError("longitude hors bornes")
        return v


class EcoEvent(BaseModel):
    """Événement environnemental versionné et validé."""

    schema_version: str = Field(default="1.0", pattern=r"^\d+\.\d+$")
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: EventType = EventType.potential_environmental_incident
    source_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    asset_reference: str | None = None
    location: Location | None = None
    observations: list[str] = Field(default_factory=list)
    detection: DetectionInfo = Field(default_factory=DetectionInfo)
    analysis_status: AnalysisStatus = AnalysisStatus.pending
    risk_level: RiskLevel = RiskLevel.unassessed
    alert_status: AlertStatus = AlertStatus.not_evaluated
    correlation_id: str = Field(default_factory=lambda: str(uuid4()))
    trigger_reason: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    metadata: dict[str, Any] = Field(default_factory=dict)
    simulated: bool = False

    @field_validator("source_id")
    @classmethod
    def validate_source(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("source_id requis")
        if len(v) > 128:
            raise ValueError("source_id trop long")
        return v.strip()

    def transition_analysis(self, new: AnalysisStatus) -> None:
        allowed: dict[AnalysisStatus, set[AnalysisStatus]] = {
            AnalysisStatus.pending: {AnalysisStatus.in_progress, AnalysisStatus.failed},
            AnalysisStatus.in_progress: {AnalysisStatus.completed, AnalysisStatus.failed},
            AnalysisStatus.completed: set(),
            AnalysisStatus.failed: {AnalysisStatus.pending},
        }
        if new not in allowed.get(self.analysis_status, set()):
            raise ValueError(f"transition {self.analysis_status} -> {new} interdite")
        self.analysis_status = new

    def transition_alert(self, new: AlertStatus) -> None:
        allowed: dict[AlertStatus, set[AlertStatus]] = {
            AlertStatus.not_evaluated: {
                AlertStatus.pending,
                AlertStatus.triggered,
                AlertStatus.suppressed,
            },
            AlertStatus.pending: {AlertStatus.triggered, AlertStatus.suppressed},
            AlertStatus.triggered: {AlertStatus.acknowledged, AlertStatus.suppressed},
            AlertStatus.suppressed: {AlertStatus.pending},
            AlertStatus.acknowledged: set(),
        }
        if new not in allowed.get(self.alert_status, set()):
            raise ValueError(f"transition {self.alert_status} -> {new} interdite")
        self.alert_status = new
