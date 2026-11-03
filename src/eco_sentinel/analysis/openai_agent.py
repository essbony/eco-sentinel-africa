"""Agent Analyse — Meta API (Responses, OpenAI compatible) avec fallback mock tracé."""

import json
from typing import Any

from eco_sentinel.a2a.protocol import A2ARequest
from eco_sentinel.config import get_settings
from eco_sentinel.core.logging import get_logger
from eco_sentinel.core.meta_client import call_meta_responses, get_meta_client

logger = get_logger("eco_sentinel.analysis")

RISK_GRID = {
    "low": "impact visuel mineur, surveillance",
    "medium": "accumulation à vérifier, intervention planifiable",
    "high": "pollution probable, intervention recommandée",
    "critical": "danger avéré, action immédiate requise",
}


async def _call_meta(payload: dict[str, Any]) -> dict[str, Any] | None:
    """Tous les Muse partagent le même base_url + client OpenAI."""  # noqa: E501
    settings = get_settings()
    # Unifié : même BASE_URL + MODEL_API_KEY via AsyncOpenAI (Meta Dev AI)
    model = getattr(settings, "spark_model", "muse-spark-1.3")
    timeout = float(getattr(settings, "spark_timeout_s", 15.0))
    client = get_meta_client()
    if client is None:
        return None
    instructions = (
        "Tu es l'agent Analyse Eco Sentinel Africa. "
        "Consolide les preuves sans inventer. Distingue observation / inférence / non vérifié. "
        "Réponds en français, concis, tracé. "
        "Ne jamais affirmer toxicité chimique sans preuve. Format: synthèse en 3-5 phrases."
    )
    prompt = (  # noqa: E501
        f"Payload événement:\n{json.dumps(payload, ensure_ascii=False, indent=2)}\n\n"
        "Consigne: fournis une synthèse + liste observations/inférences/non-vérifié."
    )
    text = await call_meta_responses(
        model=model,
        instructions=instructions,
        input_text=prompt,
        timeout_s=timeout,
        max_tokens=500,
    )
    if not text:
        return None
    return {"synthesis": text, "model": model, "provider": "meta"}


def _mock_analysis(payload: dict[str, Any]) -> dict[str, Any]:
    classification = payload.get("classification", {})
    detection = payload.get("detection", {})
    # score max parmi toutes les détections (pas seulement la 1ère) pour ne pas rater un 0.94
    det_scores = [
        r.get("score", 0) for r in detection.get("results", []) if r.get("score") is not None
    ]
    det_cats = [r.get("category", "") for r in detection.get("results", [])]
    best_score = max(det_scores + [classification.get("confidence", 0.5)])
    # catégorie la plus critique présente
    has_waste = any(
        c in ("waste", "dumping", "plastic_bottle", "container", "debris")
        for c in det_cats + [classification.get("classification", "")]
    )
    cat = classification.get("classification", det_cats[0] if det_cats else "unknown")
    score = best_score

    # Grille restaurée pour démo jury — high accessible à 0.78 mais garde NMS/filtrage
    if score >= 0.90:
        risk = "critical" if has_waste and score >= 0.93 else "high"
    elif score >= 0.78:
        risk = "high"
    elif score >= 0.55:
        risk = "medium"
    else:
        risk = "low"

    return {
        "risk_level": risk,
        "risk_rationale": RISK_GRID[risk],
        "confidence": score,
        "synthesis": f"Analyse mock — {cat} score {score:.2f} → risque {risk}",
        "observations_vs_inferences": {
            "observations": classification.get("facts", []),
            "inferences": classification.get("hypotheses", []),
            "unverified": classification.get("uncertainties", []),
        },
        "missing_info": ["analyse chimique terrain non disponible", "durée d'exposition exacte"],
        "recommendations": [
            "vérification terrain dans 24h"
            if risk in ("medium", "high")
            else "surveillance continue"
        ],
        "provider": "mock",
        "model": "mock-analysis-1.0",
    }


async def analysis_handler(req: A2ARequest) -> dict:
    payload = req.payload
    result = await _call_meta(payload)
    if result is not None:
        extra = _mock_analysis(payload)
        # La synthèse Meta prime, mais on complète avec grille risque
        result.update({k: v for k, v in extra.items() if k not in result})
        result["simulated"] = False
        return result
    mock = _mock_analysis(payload)
    mock["simulated"] = True
    return mock
