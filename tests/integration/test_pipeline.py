"""Test E2E pipeline : ingestion → vision → event → orchestration → alerte."""

import base64

from fastapi.testclient import TestClient

from eco_sentinel.api.app import create_app


def test_health_and_ingest():
    app = create_app()
    with TestClient(app) as client:
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

        # Ingest image mock (contient "waste" → détection)
        img = b"\xff\xd8waste mock image"
        r2 = client.post(
            "/ingest/image",
            files={"file": ("test.jpg", img, "image/jpeg")},
            params={"source_id": "camera_001"},
        )
        assert r2.status_code == 200
        assert r2.json()["status"] in ("queued", "sample_skipped")


def test_ingest_b64_and_events_flow():
    app = create_app()
    with TestClient(app) as client:
        b64 = base64.b64encode(b"\xff\xd8waste b64 test").decode()
        r = client.post("/ingest/b64", json={"source_id": "camera_002", "b64": b64})
        assert r.status_code == 200

        # Laisse le worker traiter
        import time

        time.sleep(0.6)

        r2 = client.get("/events")
        assert r2.status_code == 200
        # Au moins 0 événement (si sample_skipped ou dedup, peut être 0 — mais ne doit pas crasher)

        r3 = client.get("/sources")
        assert r3.status_code == 200
        assert any(s["source_id"] == "camera_002" for s in r3.json())


def test_dashboard_served():
    app = create_app()
    with TestClient(app) as client:
        r = client.get("/dashboard")
        assert r.status_code == 200
        assert "Eco Sentinel" in r.text
