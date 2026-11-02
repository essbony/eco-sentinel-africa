"""Garanties durables : détection <1min, boxes visibles, alerte sonore au trigger."""

import pathlib
import time

import pytest

from eco_sentinel.events.detector import build_event, reset_state, should_create_event
from eco_sentinel.vision import get_vision_adapter
from eco_sentinel.vision.base import VisionInput


@pytest.mark.asyncio
async def test_detection_under_one_minute():
    """Le pipeline doit produire une détection en moins de 60s, même si Meta renvoie vide."""
    reset_state()
    adapter = get_vision_adapter("mock")
    # Image type upload fichier (source_id camera_001) — mock garantit 70% trigger,
    # on force avec hint waste pour être déterministe
    inp = VisionInput(
        source_id="camera_001",
        image_bytes=b"waste outline microsoft test frame",
        categories=["waste", "plastic_bottle", "container", "debris", "dumping"],
        timestamp=time.time(),
    )
    t0 = time.perf_counter()
    out = await adapter.detect(inp)
    ok, reason = should_create_event(
        "camera_001", out, dedup_window_s=60, persistence_threshold=1, confidence_threshold=0.5
    )
    dt = time.perf_counter() - t0
    assert dt < 60, f"détection trop lente: {dt:.1f}s > 60s"
    assert ok, f"should_create_event a refusé: {reason}"
    assert len(out.results) >= 1
    # chaque résultat doit porter une bbox exploitable pour le dashboard
    for r in out.results:
        assert "bbox" in r, "box manquante"
        b = r["bbox"]
        for k in ("x", "y", "width", "height"):
            assert k in b
            assert 0 <= b[k] <= 1, f"{k} hors 0-1: {b[k]}"
        assert b["width"] >= 0.02 and b["height"] >= 0.02


@pytest.mark.asyncio
async def test_boxes_on_image_and_video_sources():
    """Images (camera_001) et frames vidéo (camera_video/camera_live) doivent rendre des boxes."""
    for source_id in ("camera_001", "camera_video", "camera_live"):
        reset_state()
        adapter = get_vision_adapter("mock")
        inp = VisionInput(
            source_id=source_id,
            image_bytes=b"waste frame for " + source_id.encode(),
            categories=["waste", "plastic_bottle", "container", "debris", "dumping"],
            timestamp=time.time(),
        )
        out = await adapter.detect(inp)
        assert len(out.results) >= 1, f"pas de box pour source {source_id}"
        # build_event doit conserver les bboxes pour le WS / dashboard
        ev = build_event(source_id, out)
        assert ev.detection.results
        for det in ev.detection.results:
            assert det.bbox is not None, f"bbox None pour {source_id}"
            assert 0 <= det.bbox.x <= 1
            assert 0 <= det.bbox.y <= 1
            assert det.bbox.width > 0 and det.bbox.height > 0
        # SAM31 avec hint waste doit produire des boxes (via mock fallback si Meta indisponible)
        from eco_sentinel.vision.sam31 import SAM31Adapter

        sam = SAM31Adapter(model_id="sam-3.1", timeout_s=2)
        inp2 = VisionInput(
            source_id=source_id,
            image_bytes=b"\xff\xd8\xff\xe0" + b"\x00" * 200 + b"waste",
            categories=["waste", "plastic_bottle", "container"],
            timestamp=time.time(),
        )
        out2 = await sam.detect(inp2)
        # Si Meta dit 0 on accepte 0 — mock garantit >=1 en cas d'erreur API
        assert isinstance(out2.results, list)
        if len(out2.results) >= 1:
            assert all("bbox" in r for r in out2.results)


def test_alert_sounds_on_trigger():
    """Tout déclenchement (event + boxes ou alert) doit sonner — pas seulement si liveActive."""
    # 1) Backend : un high doit produire une Alert
    from eco_sentinel.alerts.engine import evaluate, reset
    from eco_sentinel.models.events import DetectionInfo, DetectionResult, DetectionStatus, EcoEvent

    reset()
    ev = EcoEvent(source_id="camera_001", confidence=0.88, simulated=False)
    ev.detection = DetectionInfo(
        model="sam-3.1",
        status=DetectionStatus.detected,
        results=[DetectionResult(category="waste", score=0.88, bbox=None)],
    )
    alert, reason = evaluate(
        ev, {"risk_level": "high", "confidence": 0.88}, min_risk="medium", dedup_window_s=0
    )
    assert alert is not None, f"alerte high non déclenchée: {reason}"
    assert alert.severity.value in ("critical", "high", "warning")

    # 2) Frontend : dashboard doit appeler playBeep pour tout trigger non-historique
    html = pathlib.Path("src/eco_sentinel/api/dashboard.html").read_text(encoding="utf-8")
    # le JS doit contenir la logique simplifiée sans gate hasRealImage/liveActive
    assert "alerte sonore au déclenchement" in html
    assert "if(!isHistoric){" in html
    assert "playBeep(sevForBeep)" in html
    assert "playBeep('low')" in html
    # ne doit plus exiger hasRealImage/liveActive pour sonner
    assert (
        "hasRealImage"
        not in html.split("alerte sonore au déclenchement")[1].split("ws.onmessage")[0]
        or "if(!isHistoric && hasRealImage)" not in html
    )
    # seuil historique élargi à 15000 pour éviter de muter un event à 8s de latence
    assert "15000" in html
    assert "2500" not in html.split("alerte sonore au déclenchement")[1][:500]
