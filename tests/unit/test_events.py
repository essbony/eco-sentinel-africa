import pytest

from eco_sentinel.events.detector import build_event, reset_state, should_create_event
from eco_sentinel.models.events import EcoEvent
from eco_sentinel.vision.base import VisionOutput


def test_event_contract_validation():
    ev = EcoEvent(source_id="camera_001", asset_reference="frame-1")
    assert ev.schema_version == "1.0"
    assert ev.source_id == "camera_001"
    with pytest.raises(ValueError):
        EcoEvent(source_id="")


def test_event_transitions():
    ev = EcoEvent(source_id="cam1")
    ev.transition_analysis(ev.analysis_status.__class__.in_progress)
    assert ev.analysis_status.value == "in_progress"
    with pytest.raises(ValueError):
        ev.transition_analysis(ev.analysis_status.__class__.pending)


def test_should_create_event_no_detection():
    reset_state()
    out = VisionOutput(model="sam-3.1-mock", results=[], simulated=True)
    ok, reason = should_create_event("cam1", out)
    assert not ok
    assert "aucune" in reason


def test_should_create_and_build():
    reset_state()
    out = VisionOutput(
        model="sam-3.1-mock", results=[{"category": "waste", "score": 0.9}], simulated=True
    )
    ok, _ = should_create_event("cam2", out, dedup_window_s=0)
    assert ok
    ev = build_event("cam2", out)
    assert ev.detection.status.value == "detected"
    assert ev.simulated is True


def test_dedup_and_persistence():
    reset_state()
    out = VisionOutput(
        model="sam-3.1-mock", results=[{"category": "waste", "score": 0.9}], simulated=True
    )
    ok1, _ = should_create_event("cam3", out, dedup_window_s=60, persistence_threshold=3)
    assert ok1
    ok2, reason2 = should_create_event("cam3", out, dedup_window_s=60, persistence_threshold=3)
    assert not ok2  # dedup 2/3
    assert "persistance" in reason2 or "dedup" in reason2
    ok3, reason3 = should_create_event("cam3", out, dedup_window_s=60, persistence_threshold=3)
    assert ok3  # persistance 3/3 atteinte
    assert "persistance" in reason3
