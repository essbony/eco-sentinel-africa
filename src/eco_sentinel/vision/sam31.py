"""Adaptateur SAM 3.1 via API Meta (OpenAI compatible Responses)."""

import time

from eco_sentinel.core.logging import get_logger
from eco_sentinel.core.meta_client import call_meta_responses, get_meta_client
from eco_sentinel.vision.base import VisionInput, VisionOutput, VisionPort
from eco_sentinel.vision.mock import MockVisionAdapter

logger = get_logger("eco_sentinel.vision")


def _iou(a: dict, b: dict) -> float:
    """IoU entre deux bbox {x,y,width,height} en 0-1."""
    ax1, ay1 = a["x"], a["y"]
    ax2, ay2 = a["x"] + a["width"], a["y"] + a["height"]
    bx1, by1 = b["x"], b["y"]
    bx2, by2 = b["x"] + b["width"], b["y"] + b["height"]
    inter_x1, inter_y1 = max(ax1, bx1), max(ay1, by1)
    inter_x2, inter_y2 = min(ax2, bx2), min(ay2, by2)
    if inter_x2 <= inter_x1 or inter_y2 <= inter_y1:
        return 0.0
    inter = (inter_x2 - inter_x1) * (inter_y2 - inter_y1)
    union = a["width"] * a["height"] + b["width"] * b["height"] - inter
    return inter / union if union > 0 else 0.0


def _nms(results: list[dict], iou_thresh: float = 0.45) -> list[dict]:
    """Supprime les doublons fortement chevauchants, garde le meilleur score."""
    if len(results) <= 1:
        return results
    sorted_res = sorted(results, key=lambda r: r.get("score", 0), reverse=True)
    kept: list[dict] = []
    for cand in sorted_res:
        if all(_iou(cand["bbox"], k["bbox"]) < iou_thresh for k in kept):
            kept.append(cand)
    return kept


class SAM31Adapter(VisionPort):
    """
    Adaptateur SAM 3.1 via Meta API.
    Utilise MODEL_API_KEY + BASE_URL avec l'API Responses (OpenAI compatible).
    Fallback mock tracé si l'appel échoue.
    """

    def __init__(self, model_id: str = "sam-3.1", timeout_s: float = 10.0):
        self._model_id = model_id
        self._timeout_s = timeout_s
        self._fallback = MockVisionAdapter(model_id="sam-3.1")

    @property
    def model_id(self) -> str:
        return self._model_id

    async def detect(self, inp: VisionInput) -> VisionOutput:
        start = time.time()
        client = get_meta_client()
        if client is None:
            logger.warning("SAM31 sans MODEL_API_KEY — fallback mock")
            out = await self._fallback.detect(inp)
            out.model = f"{self._model_id} (mock-no-key)"
            return out

        # Détecte format image
        image_format = "jpeg"
        if inp.image_bytes.startswith(b"\x89PNG"):
            image_format = "png"

        categories_str = (
            ", ".join(inp.categories)
            if inp.categories
            else "waste,plastic_bottle,container,debris,dumping"
        )

        # Prompt équilibré : pas trop conservateur
        instructions = (
            "Tu es SAM 3.1 — modèle de segmentation/détection visuelle. "
            "Tu décris ce que tu vois, tu ne prouves jamais la toxicité. "
            "Détecte si l'objet correspond à la catégorie, même partiel. "
            "Les bbox entourent l'objet sans marge. "
            "Score 0.9+ si net, 0.75-0.89 si visible, 0.55-0.74 si incertain. "
            "Réponds en JSON valide."
        )
        input_text = (
            f"Analyse cette image et détecte parmi [{categories_str}]. "
            "Pour chaque détection: category, score 0-1, "
            "bbox {{x,y,width,height}} 0-1, label. "
            'JSON: {{"detections": [{{"category": "...", "score": 0.9, '
            '"bbox": {{"x":0.1,"y":0.1,"width":0.2,"height":0.2}}, "label": "..."}}]}}. '
            'Si rien, {{"detections": []}}.'
        )

        raw = await call_meta_responses(
            model=self._model_id,
            instructions=instructions,
            input_text=input_text,
            image_bytes=inp.image_bytes,
            image_format=image_format,
            timeout_s=self._timeout_s,
            response_format_json=True,
            max_tokens=900,
        )

        # Si SAM vide, tente Spark
        if not raw or not raw.strip():
            logger.warning("SAM31 vide (model=%s) — fallback Spark", self._model_id)
            try:
                from eco_sentinel.config import get_settings

                s = get_settings()
                spark_model = getattr(s, "spark_model", "muse-spark-1.3")
                raw = await call_meta_responses(
                    model=spark_model,
                    instructions=instructions,
                    input_text=input_text,
                    image_bytes=inp.image_bytes,
                    image_format=image_format,
                    timeout_s=min(self._timeout_s + 5, 20),
                    response_format_json=True,
                    max_tokens=900,
                )
                if raw and raw.strip():
                    logger.info("Fallback Spark vision a répondu (%s)", spark_model)
            except Exception as e:
                logger.warning("Fallback Spark échoué: %s", e)
                raw = None
        result = None
        if raw:
            import json

            cleaned = raw.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                if lines[0].strip().startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].strip().startswith("```"):
                    lines = lines[:-1]
                cleaned = "\n".join(lines).strip()
            try:
                result = json.loads(cleaned)
            except Exception:
                start_idx = cleaned.find("{")
                end_idx = cleaned.rfind("}")
                if start_idx != -1 and end_idx != -1:
                    try:
                        result = json.loads(cleaned[start_idx : end_idx + 1])
                    except Exception:
                        result = None

        if result is None or "detections" not in result:
            logger.warning("SAM31 appel échoué ou vide — fallback mock (model=%s)", self._model_id)
            out = await self._fallback.detect(inp)
            out.model = f"{self._model_id} (mock-fallback)"
            out.latency_ms = (time.time() - start) * 1000
            return out

        detections = result.get("detections", [])
        results: list[dict] = []
        allowed = set(inp.categories) if inp.categories else set()
        for det in detections if isinstance(detections, list) else []:
            cat = str(det.get("category", "unknown")).strip()
            # Filtre catégorie inconnue
            if allowed and cat not in allowed and cat != "unknown":
                # tolère mapping proche
                cat_lower = cat.lower().replace(" ", "_")
                if cat_lower not in allowed:
                    continue
            try:
                score = float(det.get("score", 0.5))
            except Exception:
                score = 0.5
            score = max(0.0, min(1.0, score))
            # Filtre basse confiance — seuil aligné sur detector (0.5)
            if score < 0.45:
                continue
            bbox = det.get("bbox") if isinstance(det.get("bbox"), dict) else {}
            try:
                x = float(bbox.get("x", 0.1))
                y = float(bbox.get("y", 0.1))
                w = float(bbox.get("width", bbox.get("w", 0.2)))
                h = float(bbox.get("height", bbox.get("h", 0.2)))
            except Exception:
                x, y, w, h = 0.1, 0.1, 0.2, 0.2
            # Clamp et validation bbox
            x = max(0.0, min(0.92, x))
            y = max(0.0, min(0.92, y))
            w = max(0.02, min(0.98 - x, w))
            h = max(0.02, min(0.98 - y, h))
            # Écarte bbox dégénérées
            if w < 0.02 or h < 0.02:
                continue
            results.append(
                {
                    "category": cat,
                    "score": round(score, 3),
                    "bbox": {
                        "x": round(x, 3),
                        "y": round(y, 3),
                        "width": round(w, 3),
                        "height": round(h, 3),
                    },
                    "mask_ref": det.get("mask_ref"),
                    "tracking_id": det.get("tracking_id"),
                    "label": det.get("label", cat),
                }
            )

        # NMS pour éviter multi-comptage du même objet
        results = _nms(results, iou_thresh=0.45)
        # Tri par score décroissant : le meilleur porte le signal high
        results.sort(key=lambda r: r["score"], reverse=True)

        latency = (time.time() - start) * 1000
        model_name = self._model_id
        # Ne pas halluciner si modèle dit 0 — fallback déjà géré
        return VisionOutput(
            model=model_name,
            results=results,
            raw_ref=f"meta://{model_name}/{inp.source_id}",
            latency_ms=latency,
            simulated=False,
        )
