import pytest

from eco_sentinel.ingestion.service import IngestionService


@pytest.mark.asyncio
async def test_ingestion_validation():
    svc = IngestionService(max_queue_size=2, sample_fps=100, max_image_bytes=100)
    with pytest.raises(ValueError):
        await svc.ingest("", b"data")
    with pytest.raises(ValueError):
        await svc.ingest("cam1", b"")
    with pytest.raises(ValueError):
        await svc.ingest("cam1", b"x" * 200)


@pytest.mark.asyncio
async def test_ingestion_backpressure_and_sampling():
    svc = IngestionService(max_queue_size=2, sample_fps=100, max_image_bytes=5000)
    img = b"\xff\xd8fakejpeg"
    r1 = await svc.ingest("cam1", img)
    assert r1["status"] == "queued"
    r2 = await svc.ingest("cam1", img)
    assert r2["status"] in ("queued", "sample_skipped")
    # Fill queue to test backpressure: force sample interval 0
    svc2 = IngestionService(max_queue_size=1, sample_fps=1000, max_image_bytes=5000)
    await svc2.ingest("cam2", img)
    await svc2.ingest("cam2", img)
    assert svc2.queue.qsize() <= 1
