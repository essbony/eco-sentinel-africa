"""Protocole A2A — bus in-process + bridge SDK officiel (a2a-sdk 0.3.26)."""

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from eco_sentinel.core.logging import get_logger

logger = get_logger("eco_sentinel.a2a")


@dataclass
class AgentCard:
    """Carte de capacité d'un agent A2A."""

    agent_id: str
    name: str
    description: str
    capabilities: list[str]
    endpoint: str | None = None


@dataclass
class A2ARequest:
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sender: str = "router"
    target: str = ""
    capability: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class A2AResponse:
    request_id: str
    correlation_id: str
    agent_id: str
    status: str  # ok | error | timeout
    result: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    latency_ms: float = 0


class A2ABus:
    """Bus A2A in-process + bridge vers SDK officiel."""

    def __init__(self, timeout_s: float = 10.0):
        self._agents: dict[str, tuple[AgentCard, Any]] = {}
        self._executors: dict[str, Any] = {}
        self.timeout_s = timeout_s

    def register(self, card: AgentCard, handler: Any) -> None:
        self._agents[card.agent_id] = (card, handler)
        # Bridge SDK : crée aussi un Executor SDK pour exposition HTTP
        try:
            from eco_sentinel.a2a.sdk import EcoExecutor

            self._executors[card.agent_id] = EcoExecutor(card.agent_id, handler)
        except Exception:
            pass
        logger.info("A2A agent enregistré: %s (%s)", card.agent_id, card.capabilities)

    def list_cards(self) -> list[AgentCard]:
        return [c for c, _ in self._agents.values()]

    def get_executor(self, agent_id: str) -> Any | None:
        return self._executors.get(agent_id)

    def get_sdk_cards(self, base_url: str = "http://localhost:8000") -> list[Any]:
        """Retourne les AgentCard SDK officielles pour tous les agents."""
        try:
            from eco_sentinel.a2a.sdk import build_sdk_card

            return [build_sdk_card(aid, base_url) for aid in self._agents]
        except Exception:
            return []

    async def call(self, req: A2ARequest) -> A2AResponse:
        start = time.time()
        if req.target not in self._agents:
            return A2AResponse(
                request_id=req.request_id,
                correlation_id=req.correlation_id,
                agent_id=req.target,
                status="error",
                error=f"agent {req.target} inconnu",
                latency_ms=(time.time() - start) * 1000,
            )
        card, handler = self._agents[req.target]
        try:
            result = await asyncio.wait_for(handler(req), timeout=self.timeout_s)
            return A2AResponse(
                request_id=req.request_id,
                correlation_id=req.correlation_id,
                agent_id=req.target,
                status="ok",
                result=result if isinstance(result, dict) else {"output": result},
                latency_ms=(time.time() - start) * 1000,
            )
        except TimeoutError:
            logger.warning("A2A timeout %s -> %s", req.sender, req.target)
            return A2AResponse(
                request_id=req.request_id,
                correlation_id=req.correlation_id,
                agent_id=req.target,
                status="timeout",
                error="timeout",
                latency_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            logger.exception("A2A error %s", req.target)
            return A2AResponse(
                request_id=req.request_id,
                correlation_id=req.correlation_id,
                agent_id=req.target,
                status="error",
                error=str(e),
                latency_ms=(time.time() - start) * 1000,
            )


# Singleton
a2a_bus = A2ABus()
