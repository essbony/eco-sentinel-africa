"""Détection d'événements — logique testable indépendante des modèles."""

import time
from collections import defaultdict

from eco_sentinel.core.logging import get_logger
from eco_sentinel.models.events import DetectionStatus, EcoEvent
from eco_sentinel.vision.base import VisionOutput

logger = get_logger("eco_sentinel.events")

# Mémoire simple pour persistance / déduplication
_recent: dict[str, float] = {}
_counts: dict[str, int] = defaultdict(int)


def should_create_event(
    source_id: str,
    vision_output: VisionOutput,
    dedup_window_s: int = 60,
    persistence_threshold: int = 2,
    confidence_threshold: float = 0.5,
) -> tuple[bool, str]:
    """Décide si un événement doit être créé. Retourne (oui/non, raison)."""
    if not vision_output.results:
        return False, "aucune détection"

    # Filtre confiance
    best = max((r.get("score") or 0 for r in vision_output.results), default=0)
    if best < confidence_threshold:
        return False, f"score {best:.2f} < seuil {confidence_threshold}"

    # Dedup par source+catégorie — bypass pour score très élevé (>=0.93) afin de ne jamais rater une alerte critique
    key = f"{source_id}:{vision_output.results[0].get('category', 'unknown')}"
    now = time.time()
    # Score critique → création immédiate, pas de dedup
    if best >= 0.93:
        _recent[key] = now
        _counts[key] = 1
        return True, f"score critique {best:.2f} — bypass dedup {key}"
    last = _recent.get(key, 0)
    if now - last < dedup_window_s:
        # Incrémente compteur de persistance
        _counts[key] += 1
        if _counts[key] < persistence_threshold:
            return (
                False,
                f"dedup window ({now - last:.0f}s < {dedup_window_s}s) — "
                f"persistance {_counts[key]}/{persistence_threshold}",
            )
        # Seuil atteint → on autorise l'événement malgré dedup
        _recent[key] = now
        _counts[key] = 0
        return True, f"persistance atteinte pour {key}"

    _recent[key] = now
    _counts[key] = 1
    return True, f"nouvelle détection {key} score={best:.2f}"


def build_event(
    source_id: str,
    vision_output: VisionOutput,
    timestamp: float | None = None,
    location: dict | None = None,
) -> EcoEvent:
    from datetime import UTC, datetime

    from eco_sentinel.models.events import BoundingBox, DetectionInfo, DetectionResult, Location

    ts = datetime.fromtimestamp(timestamp or time.time(), tz=UTC)
    loc = Location(**location) if location else None

    results = []
    for r in vision_output.results:
        bbox = None
        if r.get("bbox"):
            try:
                bbox = BoundingBox(**r["bbox"])
            except Exception:
                bbox = None
        results.append(
            DetectionResult(
                category=r.get("category", "unknown"),
                score=r.get("score"),
                bbox=bbox,
                mask_ref=r.get("mask_ref"),
                tracking_id=r.get("tracking_id"),
            )
        )

    detection = DetectionInfo(
        model=vision_output.model,
        status=DetectionStatus.detected if results else DetectionStatus.not_detected,
        results=results,
        raw_ref=vision_output.raw_ref,
    )

    # ne pas re-dédupliquer ici — le worker a déjà validé
    reason = f"détection {len(results)} objet(s) — segmentation SAM"

    event = EcoEvent(
        source_id=source_id,
        timestamp=ts,
        asset_reference=vision_output.raw_ref,
        location=loc,
        observations=[f"vision:{len(results)} détections"],
        detection=detection,
        trigger_reason=reason,
        confidence=max((r.score or 0 for r in results), default=None),
        simulated=vision_output.simulated,
    )
    return event


def reset_state() -> None:
    _recent.clear()
    _counts.clear()
