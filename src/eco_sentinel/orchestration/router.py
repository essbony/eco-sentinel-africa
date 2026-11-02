"""Router Wonder — orchestre les agents via A2A (Meta Muse Wonder quand configuré)."""

import asyncio
import json

from eco_sentinel.a2a.protocol import A2ARequest, a2a_bus
from eco_sentinel.agents.classification import classification_handler
from eco_sentinel.agents.geo import geo_handler
from eco_sentinel.agents.report import report_handler
from eco_sentinel.agents.research import research_handler
from eco_sentinel.analysis.openai_agent import analysis_handler
from eco_sentinel.config import get_settings
from eco_sentinel.core.logging import get_logger, set_correlation_id
from eco_sentinel.core.meta_client import call_meta_json
from eco_sentinel.models.events import EcoEvent

logger = get_logger("eco_sentinel.router")


def _ensure_agents() -> None:
    from eco_sentinel.a2a.protocol import AgentCard

    if not a2a_bus.list_cards():
        a2a_bus.register(
            AgentCard("classification", "Classification", "Classifie les détections", ["classify"]),
            classification_handler,
        )
        a2a_bus.register(AgentCard("geo", "Geo", "Contexte géographique", ["geo"]), geo_handler)
        a2a_bus.register(
            AgentCard("research", "Research", "Contexte documentaire", ["research"]),
            research_handler,
        )
        a2a_bus.register(
            AgentCard("analysis", "Analysis", "Analyse Meta/mock", ["analyze"]), analysis_handler
        )
        a2a_bus.register(
            AgentCard("report", "Report", "Rapport dashboard", ["report"]), report_handler
        )


async def _wonder_plan(event: EcoEvent) -> dict | None:
    """Interroge Muse Wonder pour décider du plan d'orchestration (optionnel, non-bloquant)."""
    settings = get_settings()
    provider = getattr(settings, "router_provider", "mock")
    if provider.strip().lower() != "meta" or not settings.is_meta_configured():  # type: ignore[attr-defined]
        return None
    model = getattr(settings, "router_model", "muse-wonder-1.0")
    timeout = float(getattr(settings, "router_timeout_s", 15.0))
    instructions = (
        "Tu es Muse Wonder, routeur Eco Sentinel. "
        "Tu décides l'ordre d'exécution des agents pour un événement environnemental. "
        "Réponds UNIQUEMENT en JSON."
    )
    payload = {
        "event_id": event.event_id,
        "source_id": event.source_id,
        "detection": event.detection.model_dump(),
    }
    input_text = (
        f"Événement: {json.dumps(payload, ensure_ascii=False)}\n"
        'Décide workflow. JSON: {"workflow": "standard"|"fast"|"deep", '
        '"priority": "low"|"medium"|"high", "reason": "..."}. '
        "Standard = classification+geo -> research -> analysis -> report. Ne fournis que le JSON."
    )
    plan = await call_meta_json(
        model=model,
        instructions=instructions,
        input_text=input_text,
        timeout_s=timeout,
        fallback=None,
    )
    if plan and "workflow" in plan:
        logger.info("Wonder plan: %s", plan)
        return plan
    return None


async def orchestrate(event: EcoEvent) -> dict:
    """Orchestre le workflow complet pour un événement."""
    _ensure_agents()
    set_correlation_id(event.correlation_id)
    logger.info("router orchestrate event=%s source=%s", event.event_id, event.source_id)

    # Optionnel : Wonder décide du workflow (ne bloque pas si échec)
    try:
        wonder_plan = await _wonder_plan(event)
    except Exception as e:
        logger.warning("Wonder indisponible: %s", e)
        wonder_plan = None

    payload_base = {
        "event_id": event.event_id,
        "source_id": event.source_id,
        "detection": event.detection.model_dump(),
        "location": event.location.model_dump() if event.location else None,
        "timestamp": event.timestamp.isoformat(),
    }

    # Étape 1 : classification + geo en parallèle
    req_class = A2ARequest(
        target="classification",
        capability="classify",
        payload=payload_base,
        correlation_id=event.correlation_id,
    )
    req_geo = A2ARequest(
        target="geo", capability="geo", payload=payload_base, correlation_id=event.correlation_id
    )

    res_class, res_geo = await asyncio.gather(a2a_bus.call(req_class), a2a_bus.call(req_geo))

    classification = res_class.result if res_class.status == "ok" else {"error": res_class.error}
    geo = res_geo.result if res_geo.status == "ok" else {"error": res_geo.error}

    # Étape 2 : research (dépend de classification)
    req_research = A2ARequest(
        target="research",
        capability="research",
        payload={**payload_base, "classification": classification},
        correlation_id=event.correlation_id,
    )
    res_research = await a2a_bus.call(req_research)
    research = res_research.result if res_research.status == "ok" else {"error": res_research.error}

    # Étape 3 : analysis (consolide tout)
    analysis_payload = {
        **payload_base,
        "classification": classification,
        "geo": geo,
        "research": research,
    }
    req_analysis = A2ARequest(
        target="analysis",
        capability="analyze",
        payload=analysis_payload,
        correlation_id=event.correlation_id,
    )
    res_analysis = await a2a_bus.call(req_analysis)
    analysis = (
        res_analysis.result
        if res_analysis.status == "ok"
        else {"error": res_analysis.error, "risk_level": "low"}
    )

    # Étape 4 : report
    report_payload = {**analysis_payload, "analysis": analysis}
    req_report = A2ARequest(
        target="report",
        capability="report",
        payload=report_payload,
        correlation_id=event.correlation_id,
    )
    res_report = await a2a_bus.call(req_report)
    report = res_report.result if res_report.status == "ok" else {"error": res_report.error}

    return {
        "event_id": event.event_id,
        "correlation_id": event.correlation_id,
        "classification": classification,
        "geo": geo,
        "research": research,
        "analysis": analysis,
        "report": report,
        "wonder_plan": wonder_plan,
        "a2a_latencies": {
            "classification": res_class.latency_ms,
            "geo": res_geo.latency_ms,
            "research": res_research.latency_ms,
            "analysis": res_analysis.latency_ms,
            "report": res_report.latency_ms,
        },
    }
