"""Routes API + WebSocket Eco Sentinel."""

import base64
import pathlib
from typing import Annotated, Any

from fastapi import APIRouter, File, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from eco_sentinel.api.broadcast import register, unregister
from eco_sentinel.config import get_settings
from eco_sentinel.core.logging import get_logger
from eco_sentinel.ingestion.service import ingestion_service
from eco_sentinel.persistence.store import store

logger = get_logger("eco_sentinel.routes")
router = APIRouter()

DASHBOARD_HTML = pathlib.Path(__file__).with_name("dashboard.html").read_text(encoding="utf-8")


@router.get("/health")
async def health() -> dict[str, Any]:
    s = get_settings()
    counts = await store.count()
    return {
        "status": "ok",
        "app": s.app_name,
        "version": "0.1.0",
        "env": s.env,
        "counts": counts,
        "vision": s.vision_model,
        "router": s.router_model,
    }


@router.get("/")
async def root() -> dict[str, str]:
    return {"message": "Eco Sentinel Africa API — voir /docs et /dashboard"}


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard() -> str:
    return DASHBOARD_HTML


@router.get("/events")
async def list_events(limit: int = 50) -> list[dict[str, Any]]:
    events = await store.list_events(limit=limit)
    return [e.model_dump(mode="json") for e in events]


@router.get("/events/{event_id}")
async def get_event(event_id: str) -> dict[str, Any]:
    ev = await store.get_event(event_id)
    if not ev:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="event not found")
    return ev.model_dump(mode="json")


@router.get("/alerts")
async def list_alerts(limit: int = 50) -> list[dict[str, Any]]:
    alerts = await store.list_alerts(limit=limit)
    return [a.model_dump(mode="json") for a in alerts]


@router.get("/sources")
async def list_sources() -> list[dict[str, Any]]:
    return [s.__dict__ for s in ingestion_service.list_sources()]


@router.post("/ingest/image")
async def ingest_image(
    file: Annotated[UploadFile, File(...)],  # noqa: B008
    source_id: str = "camera_001",
) -> dict[str, Any]:
    data = await file.read()
    result = await ingestion_service.ingest(source_id, data)
    return result


@router.post("/ingest/b64")
async def ingest_b64(payload: dict[str, Any]) -> dict[str, Any]:
    source_id = payload.get("source_id", "camera_001")
    b64 = payload.get("b64", "")
    try:
        data = base64.b64decode(b64)
    except Exception:
        data = b64.encode()
    result = await ingestion_service.ingest(source_id, data)
    return result


@router.websocket("/ws/ingest/{source_id}")
async def ws_ingest(websocket: WebSocket, source_id: str) -> None:
    await websocket.accept()
    logger.info("WS ingest connecté source=%s", source_id)
    try:
        while True:
            msg = await websocket.receive()
            data: bytes | None = None
            if "bytes" in msg and msg["bytes"]:
                data = msg["bytes"]
            elif "text" in msg and msg["text"]:
                try:
                    data = base64.b64decode(msg["text"])
                except Exception:
                    data = msg["text"].encode()
            if data:
                result = await ingestion_service.ingest(source_id, data)
                await websocket.send_json(result)
    except WebSocketDisconnect:
        ingestion_service.mark_disconnected(source_id, "ws disconnect")
        logger.info("WS ingest déconnecté source=%s", source_id)
    except Exception as e:
        logger.exception("WS ingest error %s", e)
        try:
            await websocket.close()
        except Exception:  # nosec B110  # noqa: S110
            pass


@router.websocket("/ws/events")
async def ws_events(websocket: WebSocket) -> None:
    await websocket.accept()
    await register(websocket)
    logger.info("WS events dashboard connecté")
    try:
        # Envoie l'historique récent
        events = await store.list_events(limit=10)
        for ev in reversed(events):
            await websocket.send_json(
                {
                    "type": "event",
                    "event": ev.model_dump(mode="json"),
                    "alert": None,
                    "orchestration": {},
                }
            )
        while True:
            await websocket.receive_text()  # heartbeat / ping
    except WebSocketDisconnect:
        pass
    finally:
        await unregister(websocket)
