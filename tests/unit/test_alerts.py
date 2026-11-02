from eco_sentinel.alerts.engine import evaluate, reset
from eco_sentinel.models.events import DetectionInfo, DetectionResult, DetectionStatus, EcoEvent


def _event(risk_sim="high", score=0.9):
    ev = EcoEvent(source_id="cam1", confidence=score, simulated=True)
    ev.detection = DetectionInfo(
        model="sam-3.1-mock",
        status=DetectionStatus.detected,
        results=[DetectionResult(category="waste", score=score)],
    )
    return ev


def test_alert_triggered():
    reset()
    ev = _event()
    alert, reason = evaluate(
        ev, {"risk_level": "high", "confidence": 0.9}, min_risk="medium", dedup_window_s=0
    )
    assert alert is not None
    assert alert.severity.value == "critical"


def test_alert_suppressed_low_risk():
    reset()
    ev = _event()
    alert, reason = evaluate(
        ev, {"risk_level": "low", "confidence": 0.9}, min_risk="medium", dedup_window_s=0
    )
    assert alert is None
    assert "risque" in reason


def test_alert_dedup():
    reset()
    ev = _event()
    a1, _ = evaluate(
        ev, {"risk_level": "high", "confidence": 0.9}, min_risk="medium", dedup_window_s=60
    )
    assert a1 is not None
    a2, reason2 = evaluate(
        ev, {"risk_level": "high", "confidence": 0.9}, min_risk="medium", dedup_window_s=60
    )
    assert a2 is None
    assert "dédupliquée" in reason2
