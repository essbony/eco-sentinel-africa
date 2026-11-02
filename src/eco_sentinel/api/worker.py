"""Worker asynchrone — pipeline: queue → Vision → Detector → Router → Alert → Store → Broadcast."""

import asyncio

from eco_sentinel.alerts.engine import evaluate as alert_evaluate
from eco_sentinel.api.broadcast import broadcast_event
from eco_sentinel.config import get_settings
from eco_sentinel.core.logging import get_logger
from eco_sentinel.events.detector import build_event, should_create_event
from eco_sentinel.ingestion.service import ingestion_service
from eco_sentinel.orchestration.router import orchestrate
from eco_sentinel.persistence.store import store
from eco_sentinel.vision import VisionInput, get_vision_adapter

logger = get_logger("eco_sentinel.worker")
_task: asyncio.Task | None = None


async def _loop() -> None:
    settings = get_settings()
    vision = get_vision_adapter(settings.vision_provider)
    categories = [c.strip() for c in settings.vision_categories.split(",") if c.strip()]
    logger.info("worker démarré vision=%s catégories=%s", vision.model_id, categories)

    while True:
        try:
            item = await ingestion_service.consume()
            source_id = item["source_id"]
            image_bytes: bytes = item["image_bytes"]
            ts: float = item["timestamp"]

            # Vision
            v_input = VisionInput(
                source_id=source_id, image_bytes=image_bytes, categories=categories, timestamp=ts
            )
            v_out = await vision.detect(v_input)

            create, reason = should_create_event(
                source_id,
                v_out,
                dedup_window_s=settings.event_dedup_window_s,
                persistence_threshold=settings.event_persistence_threshold,
                confidence_threshold=settings.vision_confidence_threshold,
            )
            if not create:
                logger.info("événement ignoré source=%s raison=%s", source_id, reason)
                continue

            event = build_event(source_id, v_out, timestamp=ts)

            # Orchestration multi-agents
            orchestration = await orchestrate(event)

            # Mise à jour event avec résultats
            analysis = orchestration.get("analysis", {})
            risk = analysis.get("risk_level", "low")
            from eco_sentinel.models.events import RiskLevel

            try:
                event.risk_level = RiskLevel(risk)
            except ValueError:
                event.risk_level = RiskLevel.low

            from eco_sentinel.models.events import AnalysisStatus

            event.analysis_status = AnalysisStatus.completed
            event.metadata["orchestration"] = orchestration

            # Moteur d'alerte
            alert, alert_reason = alert_evaluate(
                event,
                analysis,
                min_risk=settings.alert_min_risk,
                min_confidence=settings.alert_min_confidence,
            )
            if alert:
                await store.save_alert(alert)
                event.alert_status = event.alert_status  # keep triggered via transition
                try:
                    from eco_sentinel.models.events import AlertStatus

                    event.transition_alert(AlertStatus.triggered)
                except ValueError:
                    pass
                logger.info("alerte %s pour event %s", alert.alert_id, event.event_id)
            else:
                try:
                    from eco_sentinel.models.events import AlertStatus

                    event.transition_alert(AlertStatus.suppressed)
                except ValueError:
                    pass
                logger.info("pas d'alerte: %s", alert_reason)

            await store.save_event(event)
            await broadcast_event(event, alert, orchestration)

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.exception("worker error: %s", e)
            await asyncio.sleep(1)


async def start_worker() -> None:
    global _task
    if _task is None or _task.done():
        _task = asyncio.create_task(_loop())


async def stop_worker() -> None:
    global _task
    if _task and not _task.done():
        _task.cancel()
        try:
            await _task
        except asyncio.CancelledError:
            pass
