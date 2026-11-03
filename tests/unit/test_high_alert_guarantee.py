"""Garantie : un score élevé (>=0.78) déclenche toujours une alerte, même si Meta répond low."""

import pytest

from eco_sentinel.a2a.protocol import A2ARequest
from eco_sentinel.alerts.engine import evaluate, reset
from eco_sentinel.analysis.openai_agent import _mock_analysis, analysis_handler
from eco_sentinel.models.events import DetectionInfo, DetectionResult, DetectionStatus, EcoEvent


def test_high_score_bypasses_dedup_critical():
    reset()
    ev = EcoEvent(source_id="cam_high", confidence=0.95)
    ev.detection = DetectionInfo(
        model="sam-3.1",
        status=DetectionStatus.detected,
        results=[DetectionResult(category="waste", score=0.95)],
    )
    a1, _ = evaluate(ev, {"risk_level": "critical", "confidence": 0.95}, dedup_window_s=60)
    a2, _ = evaluate(ev, {"risk_level": "critical", "confidence": 0.95}, dedup_window_s=60)
    assert a1 is not None and a2 is not None  # critical jamais dédupliqué


def test_mock_risk_grid_high():
    payload = {
        "detection": {"results": [{"category": "waste", "score": 0.88}]},
        "classification": {
            "classification": "waste",
            "confidence": 0.88,
            "facts": [],
            "hypotheses": [],
            "uncertainties": [],
        },
    }
    res = _mock_analysis(payload)
    assert res["risk_level"] == "high"
    assert res["confidence"] == 0.88


@pytest.mark.asyncio
async def test_analysis_overrides_meta_low_with_mock_high(monkeypatch):
    payload = {
        "detection": {"results": [{"category": "waste", "score": 0.88}]},
        "classification": {
            "classification": "waste",
            "confidence": 0.88,
            "facts": [],
            "hypotheses": [],
            "uncertainties": [],
        },
    }

    # Simule Meta qui répond low alors que le score mock indique high
    async def fake_call_meta(_payload):
        return {"risk_level": "low", "synthesis": "meta low", "confidence": 0.4, "provider": "meta"}

    import eco_sentinel.analysis.openai_agent as mod

    monkeypatch.setattr(mod, "_call_meta", fake_call_meta)
    # force provider meta
    from eco_sentinel.config.settings import get_settings

    s = get_settings()
    orig = s.spark_provider
    s.spark_provider = "meta"
    try:
        req = A2ARequest(target="analysis", capability="analyze", payload=payload)
        # patch is_meta_configured au niveau du handler via monkeypatch
        import eco_sentinel.config.settings as cfg_mod

        monkeypatch.setattr(cfg_mod.Settings, "is_meta_configured", lambda self: True)
        res = await analysis_handler(req)
        assert res["risk_level"] == "high", (
            f"Meta low ne doit pas écraser mock high, got {res['risk_level']}"
        )
        # doit déclencher une alerte
        ev = EcoEvent(source_id="cam1", confidence=res["confidence"])
        ev.detection = DetectionInfo(
            model="sam",
            status=DetectionStatus.detected,
            results=[DetectionResult(category="waste", score=0.88)],
        )
        reset()
        alert, _ = evaluate(ev, res, min_risk="medium", dedup_window_s=0)
        assert alert is not None
    finally:
        s.spark_provider = orig
