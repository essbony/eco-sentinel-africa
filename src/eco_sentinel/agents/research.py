"""Agent recherche & contexte — Muse Spark via Meta, n'invente pas de sources."""

import json
from typing import Any

from eco_sentinel.a2a.protocol import A2ARequest
from eco_sentinel.config import get_settings
from eco_sentinel.core.logging import get_logger
from eco_sentinel.core.meta_client import call_meta_json

logger = get_logger("eco_sentinel.research")


def _mock_research(payload: dict) -> dict:
    classification = payload.get("classification", {})
    cat = classification.get("classification", "unknown")
    knowledge = {
        "waste": {
            "context": "Accumulation de déchets — risque sanitaire si persistance >48h",
            "references": ["OMS — Gestion des déchets solides en milieu urbain"],
            "verified": True,
        },
        "plastic_bottle": {
            "context": "Plastique — persistance environnementale 100-500 ans",
            "references": ["PNUE — Pollution plastique"],
            "verified": True,
        },
    }
    entry = knowledge.get(
        cat,
        {"context": f"Pas de référence vérifiée pour {cat}", "references": [], "verified": False},
    )
    return {
        "category": cat,
        "context": entry["context"],
        "references": entry["references"],
        "verified": entry["verified"],
        "note": "Aucune source inventée — seules les références listées sont vérifiables",
        "provider": "mock",
    }


async def research_handler(req: A2ARequest) -> dict:
    payload = req.payload
    settings = get_settings()
    provider = getattr(settings, "spark_provider", "mock")
    if provider.strip().lower() != "meta" or not settings.is_meta_configured():  # type: ignore[attr-defined]
        result = _mock_research(payload)
        result["simulated"] = True
        return result

    model = getattr(settings, "spark_model", "muse-spark-1.3")
    timeout = float(getattr(settings, "spark_timeout_s", 15.0))
    classification = payload.get("classification", {})
    cat = classification.get("classification", "unknown")
    instructions = (
        "Tu es l'agent Recherche Eco Sentinel. Tu fournis contexte documentaire vérifiable, "
        "tu n'inventes JAMAIS de sources, réglementations ou chiffres. "
        "Si tu n'as pas de référence vérifiée, dis-le. Réponds UNIQUEMENT en JSON."
    )
    input_text = (  # noqa: E501
        f"Catégorie détectée: {cat}\n"
        f"Payload: {json.dumps(classification, ensure_ascii=False)}\n"
        'Produis JSON: {"category": "...", "context": "...", "references": ["..."], "verified": true/false, "note": "..."}\n'  # noqa: E501
        "References doit contenir uniquement des sources réelles ou rester vide si incertain. Ne fournis que le JSON."  # noqa: E501
    )
    meta_result: dict[str, Any] | None = await call_meta_json(
        model=model,
        instructions=instructions,
        input_text=input_text,
        timeout_s=timeout,
        fallback=None,
    )
    if meta_result and "context" in meta_result:
        meta_result["provider"] = "meta"
        meta_result["model"] = model
        meta_result["simulated"] = False
        meta_result.setdefault("references", [])
        meta_result.setdefault("verified", False)
        return meta_result

    logger.warning("Research Meta échouée — fallback mock")
    mock = _mock_research(payload)
    mock["simulated"] = True
    mock["model"] = model
    return mock
