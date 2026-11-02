"""Agent classification environnementale — Muse Spark 1.3 via Meta."""

import json
from typing import Any

from eco_sentinel.a2a.protocol import A2ARequest
from eco_sentinel.config import get_settings
from eco_sentinel.core.logging import get_logger
from eco_sentinel.core.meta_client import call_meta_json

logger = get_logger("eco_sentinel.classification")


def _mock_classify(payload: dict) -> dict:
    detection = payload.get("detection", {})
    results = detection.get("results", [])
    if not results:
        return {
            "classification": "no_detection",
            "confidence": 0.0,
            "facts": ["aucune détection visuelle"],
            "hypotheses": [],
            "uncertainties": ["absence de résultat vision"],
            "provider": "mock",
        }
    cat = results[0].get("category", "unknown")
    score = results[0].get("score", 0.5)
    mapping = {
        "waste": "déchet potentiel — nature chimique non confirmée",
        "plastic_bottle": "contenant plastique — impact visuel, pas de preuve toxicité",
        "container": "contenant — contenu inconnu",
        "debris": "débris — origine indéterminée",
        "dumping": "dépôt — accumulation à vérifier",
    }
    label = mapping.get(cat, f"élément {cat} — classification incertaine")
    return {
        "classification": cat,
        "label": label,
        "confidence": score,
        "facts": [f"objet détecté: {cat}", f"score vision: {score}"],
        "hypotheses": [f"pourrait être {label} (à confirmer terrain)"],
        "uncertainties": [
            "détection visuelle ≠ preuve de pollution chimique",
            "classification basée uniquement sur l'image",
        ],
        "provider": "mock",
    }


async def classification_handler(req: A2ARequest) -> dict:
    """Distingue faits observés vs hypothèses. Utilise Meta Spark si configuré, sinon mock."""
    payload = req.payload
    settings = get_settings()
    provider = getattr(settings, "spark_provider", "mock")
    if provider.strip().lower() != "meta" or not settings.is_meta_configured():  # type: ignore[attr-defined]
        result = _mock_classify(payload)
        result["simulated"] = True
        return result

    model = getattr(settings, "spark_model", "muse-spark-1.3")
    timeout = float(getattr(settings, "spark_timeout_s", 15.0))
    instructions = (
        "Tu es l'agent Classification Eco Sentinel. "
        "Tu distingues faits / hypothèses / incertitudes. "
        "Tu ne confirmes jamais la toxicité chimique sans preuve. "
        "Réponds UNIQUEMENT en JSON valide."
    )
    detection = payload.get("detection", {})
    cats = payload.get("detection", {}).get("results", [])
    input_text = (
        f"Détection vision: {json.dumps(detection, ensure_ascii=False)}\n"
        f"Source: {payload.get('source_id')} | Categories: {cats}\n"
        'Produis JSON: {"classification": "<cat>", "label": "...", '
        '"confidence": 0.0-1.0, "facts": [...], "hypotheses": [...], '
        '"uncertainties": [...]}\n'
        "Facts=observables, hypotheses=prudentes, uncertainties=manques. JSON seul."
    )
    meta_result: dict[str, Any] | None = await call_meta_json(
        model=model,
        instructions=instructions,
        input_text=input_text,
        timeout_s=timeout,
        fallback=None,
    )
    if meta_result and "classification" in meta_result:
        meta_result["provider"] = "meta"
        meta_result["model"] = model
        meta_result["simulated"] = False
        # Assure les champs
        meta_result.setdefault("facts", [])
        meta_result.setdefault("hypotheses", [])
        meta_result.setdefault("uncertainties", [])
        return meta_result

    logger.warning("Classification Meta échouée — fallback mock")
    mock = _mock_classify(payload)
    mock["simulated"] = True
    mock["model"] = model
    return mock
