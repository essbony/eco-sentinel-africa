"""Broadcast WebSocket pour dashboard."""

import asyncio
import json

from fastapi import WebSocket

from eco_sentinel.core.logging import get_logger

logger = get_logger("eco_sentinel.broadcast")

_clients: set[WebSocket] = set()
_lock = asyncio.Lock()


async def register(ws: WebSocket) -> None:
    async with _lock:
        _clients.add(ws)


async def unregister(ws: WebSocket) -> None:
    async with _lock:
        _clients.discard(ws)


async def broadcast_event(event, alert, orchestration) -> None:
    if not _clients:
        return
    payload = json.dumps(
        {
            "type": "event",
            "event": event.model_dump(mode="json"),
            "alert": alert.model_dump(mode="json") if alert else None,
            "orchestration": {
                "risk": orchestration.get("analysis", {}).get("risk_level"),
                "confidence": orchestration.get("analysis", {}).get("confidence"),
                "a2a_latencies": orchestration.get("a2a_latencies", {}),
            },
        },
        default=str,
    )
    dead: list[WebSocket] = []
    for ws in list(_clients):
        try:
            await ws.send_text(payload)
        except Exception:
            dead.append(ws)
    for ws in dead:
        await unregister(ws)
