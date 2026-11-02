"""Agent rapport — synthèse structurée pour dashboard."""

from datetime import UTC, datetime

from eco_sentinel.a2a.protocol import A2ARequest


async def report_handler(req: A2ARequest) -> dict:
    payload = req.payload
    event_id = payload.get("event_id", "unknown")
    classification = payload.get("classification", {})
    geo = payload.get("geo", {})
    research = payload.get("research", {})
    analysis = payload.get("analysis", {})

    return {
        "event_id": event_id,
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": f"Événement {event_id} — {classification.get('label', 'non classifié')}",
        "sections": {
            "observations": classification.get("facts", []),
            "hypotheses": classification.get("hypotheses", []),
            "uncertainties": classification.get("uncertainties", []),
            "geography": geo,
            "context": research,
            "analysis": analysis,
        },
        "dashboard_hints": {
            "show_map": geo.get("resolved", False),
            "show_references": bool(research.get("references")),
            "confidence": classification.get("confidence"),
        },
    }
