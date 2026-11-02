"""Agent contexte géographique — n'invente jamais la position."""

from eco_sentinel.a2a.protocol import A2ARequest
from eco_sentinel.config import get_settings
from eco_sentinel.core.logging import get_logger
from eco_sentinel.core.meta_client import call_meta_json

logger = get_logger("eco_sentinel.geo")

KNOWN_ZONES = {
    "abidjan_plateau": {"lat": 5.316, "lon": -4.013, "name": "Plateau, Abidjan"},
    "abidjan_yopougon": {"lat": 5.336, "lon": -4.084, "name": "Yopougon, Abidjan"},
    "abidjan_cocody": {"lat": 5.355, "lon": -3.984, "name": "Cocody, Abidjan"},
}


def _mock_geo(payload: dict) -> dict:
    location = payload.get("location")
    source_id = payload.get("source_id", "unknown")
    if not location or (not location.get("latitude") and not location.get("zone")):
        return {
            "zone": None,
            "resolved": False,
            "message": "aucune coordonnée fournie — position caméra non inventée",
            "source_id": source_id,
            "provider": "mock",
        }
    lat = location.get("latitude")
    lon = location.get("longitude")
    zone = location.get("zone")
    if zone and zone in KNOWN_ZONES:
        info = KNOWN_ZONES[zone]
        return {
            "zone": zone,
            "resolved": True,
            "info": info,
            "source_id": source_id,
            "provider": "mock",
        }
    if lat is not None and lon is not None:
        best = None
        best_dist = 999
        for zid, z in KNOWN_ZONES.items():
            dist = abs(z["lat"] - lat) + abs(z["lon"] - lon)
            if dist < best_dist:
                best_dist = dist
                best = zid
        return {
            "zone": best,
            "resolved": True,
            "distance_deg": round(best_dist, 4),
            "source_id": source_id,
            "provider": "mock",
        }
    return {"zone": zone, "resolved": False, "source_id": source_id, "provider": "mock"}


async def geo_handler(req: A2ARequest) -> dict:
    payload = req.payload
    settings = get_settings()
    provider = getattr(settings, "spark_provider", "mock")

    # Logique déterministe locale (ne jamais inventer) — LLM enrichit si résolu
    mock_result = _mock_geo(payload)

    if provider.strip().lower() != "meta" or not settings.is_meta_configured():  # type: ignore[attr-defined]
        mock_result["simulated"] = True
        return mock_result

    # Si non résolu, ne pas appeler le LLM pour éviter hallucination de position
    if not mock_result.get("resolved"):
        mock_result["simulated"] = True
        return mock_result

    # Enrichissement via Meta Spark (description zone)
    model = getattr(settings, "spark_model", "muse-spark-1.3")
    timeout = float(getattr(settings, "spark_timeout_s", 15.0))
    instructions = (
        "Tu es l'agent Geo Eco Sentinel. "
        "Tu enrichis le contexte géo sans jamais inventer de coordonnées. "
        "Réponds UNIQUEMENT en JSON."
    )
    import json

    info_json = json.dumps(mock_result, ensure_ascii=False)
    input_text = (
        f"Zone résolue: {mock_result.get('zone')} | info: {info_json}\n"
        'Produis JSON: {"zone": "...", "description": "...", "risks": [...]}\n'
        "Ne fournis que le JSON."
    )
    enriched = await call_meta_json(
        model=model,
        instructions=instructions,
        input_text=input_text,
        timeout_s=timeout,
        fallback=None,
    )
    if enriched and "description" in enriched:
        mock_result["description"] = enriched.get("description")
        mock_result["risks"] = enriched.get("risks", [])
        mock_result["provider"] = "meta"
        mock_result["model"] = model
        mock_result["simulated"] = False
        return mock_result

    mock_result["simulated"] = True
    return mock_result
