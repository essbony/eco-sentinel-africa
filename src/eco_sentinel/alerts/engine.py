"""Moteur de décision et d'alertes — règles explicites, déduplication."""

import hashlib
import time
from typing import Any

from eco_sentinel.core.logging import get_logger
from eco_sentinel.models.alerts import Alert, AlertSeverity
from eco_sentinel.models.events import EcoEvent

logger = get_logger("eco_sentinel.alerts")

RISK_ORDER = {"low": 1, "medium": 2, "high": 3, "critical": 4}
SEVERITY_MAP = {
    "low": AlertSeverity.info,
    "medium": AlertSeverity.warning,
    "high": AlertSeverity.critical,
    "critical": AlertSeverity.critical,
}

_recent_alerts: dict[str, float] = {}


def _deduplication_key(event: EcoEvent, rule_id: str) -> str:
    cat = event.detection.results[0].category if event.detection.results else "unknown"
    raw = f"{event.source_id}:{cat}:{rule_id}"
    return hashlib.md5(raw.encode(), usedforsecurity=False).hexdigest()[:12]


def evaluate(
    event: EcoEvent,
    analysis: dict[str, Any],
    min_risk: str = "medium",
    min_confidence: float = 0.6,
    dedup_window_s: int = 8,
    require_human_validation: bool = False,
) -> tuple[Alert | None, str]:
    """Applique les règles. Retourne (alerte ou None, raison)."""
    risk = analysis.get("risk_level", "low")
    confidence = analysis.get("confidence", event.confidence or 0)

    # Règle 1 : risque minimal
    if RISK_ORDER.get(risk, 0) < RISK_ORDER.get(min_risk, 2):
        return None, f"risque {risk} < seuil {min_risk}"

    # Règle 2 : confiance minimale
    if confidence is not None and confidence < min_confidence:
        return None, f"confiance {confidence:.2f} < seuil {min_confidence}"

    # Règle 3 : preuves suffisantes
    if not event.detection.results:
        return None, "pas de preuve visuelle"

    # Règle 4 : validation humaine si critique
    if require_human_validation and risk == "critical":
        return None, "validation humaine requise pour critical"

    # Déduplication
    rule_id = f"risk>={min_risk}_conf>={min_confidence}"
    key = _deduplication_key(event, rule_id)
    now = time.time()
    if key in _recent_alerts and now - _recent_alerts[key] < dedup_window_s:
        return None, f"alerte dédupliquée (clé {key}, {now - _recent_alerts[key]:.0f}s)"

    _recent_alerts[key] = now

    severity = SEVERITY_MAP.get(risk, AlertSeverity.info)
    alert = Alert(
        event_id=event.event_id,
        source_id=event.source_id,
        severity=severity,
        risk_level=risk,
        title=f"[{severity.value.upper()}] {event.source_id} — {risk}",
        description=analysis.get("synthesis", "")[:500],
        rule_id=rule_id,
        confidence=confidence,
        deduplication_key=key,
        simulated=event.simulated or analysis.get("simulated", False),
    )
    logger.info("alerte déclenchée %s risque=%s conf=%.2f", alert.alert_id, risk, confidence or 0)
    return alert, f"règle {rule_id} satisfaite"


def reset() -> None:
    _recent_alerts.clear()
