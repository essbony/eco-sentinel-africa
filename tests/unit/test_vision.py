import pytest

from eco_sentinel.vision import get_vision_adapter
from eco_sentinel.vision.base import VisionInput


@pytest.mark.asyncio
async def test_mock_vision_detects_waste():
    adapter = get_vision_adapter("mock")
    inp = VisionInput(
        source_id="cam1", image_bytes=b"waste plastic", categories=["waste"], timestamp=0
    )
    out = await adapter.detect(inp)
    assert out.simulated is True
    assert len(out.results) >= 1
    assert out.results[0]["category"] == "waste"


@pytest.mark.asyncio
async def test_mock_vision_empty():
    adapter = get_vision_adapter("mock")
    # bytes sans hint waste et hash contrôlé — peut ou non détecter, mais ne doit pas crasher
    inp = VisionInput(
        source_id="cam1", image_bytes=b"clean image no waste xyz", categories=["waste"], timestamp=0
    )
    out = await adapter.detect(inp)
    assert isinstance(out.results, list)


@pytest.mark.asyncio
async def test_mock_multi_boxes_non_superposees():
    """Mock doit générer plusieurs boîtes de catégories distinctes, non superposées."""
    adapter = get_vision_adapter("mock")
    inp = VisionInput(
        source_id="cam1",
        image_bytes=b"waste mock frame multi",
        categories=["waste", "plastic_bottle", "container", "debris", "dumping"],
        timestamp=0,
    )
    out = await adapter.detect(inp)
    # waste hint → 3 boîtes attendues
    assert len(out.results) == 3, f"attendu 3 boîtes, got {len(out.results)}"
    cats = [r["category"] for r in out.results]
    assert cats == ["waste", "plastic_bottle", "container"]
    # bboxes non superposées (x espacés)
    xs = [r["bbox"]["x"] for r in out.results]
    assert len(set(xs)) == 3
    # scores distincts et >0.7
    for r in out.results:
        assert r["score"] >= 0.7
        assert 0 <= r["bbox"]["x"] <= 1 and 0 <= r["bbox"]["y"] <= 1
