"""Store in-memory thread-safe pour événements et alertes."""

import asyncio
from collections import OrderedDict

from eco_sentinel.models.alerts import Alert
from eco_sentinel.models.events import EcoEvent


class EventStore:
    def __init__(self, max_events: int = 1000):
        self._events: OrderedDict[str, EcoEvent] = OrderedDict()
        self._alerts: OrderedDict[str, Alert] = OrderedDict()
        self._max = max_events
        self._lock = asyncio.Lock()

    async def save_event(self, event: EcoEvent) -> None:
        async with self._lock:
            self._events[event.event_id] = event
            if len(self._events) > self._max:
                self._events.popitem(last=False)

    async def get_event(self, event_id: str) -> EcoEvent | None:
        async with self._lock:
            return self._events.get(event_id)

    async def list_events(self, limit: int = 50) -> list[EcoEvent]:
        async with self._lock:
            items = list(reversed(self._events.values()))
            return items[:limit]

    async def save_alert(self, alert: Alert) -> None:
        async with self._lock:
            self._alerts[alert.alert_id] = alert

    async def list_alerts(self, limit: int = 50) -> list[Alert]:
        async with self._lock:
            items = list(reversed(self._alerts.values()))
            return items[:limit]

    async def count(self) -> dict[str, int]:
        async with self._lock:
            return {"events": len(self._events), "alerts": len(self._alerts)}


# Singleton global
store = EventStore()
