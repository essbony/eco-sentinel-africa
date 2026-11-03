"""Intégration SDK A2A officiel (a2a-sdk 0.3.26) pour Eco Sentinel."""

from typing import Any

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from a2a.utils.message import new_agent_text_message

from eco_sentinel.core.logging import get_logger

logger = get_logger("eco_sentinel.a2a.sdk")

# Définitions des 5 agents Eco Sentinel
AGENT_DEFS: dict[str, dict[str, Any]] = {
    "classification": {
        "name": "Eco Classification",
        "description": "Classe les détections visuelles, distingue faits/hypothèses",
        "skill_id": "classify",
        "skill_name": "classification",
        "skill_desc": "Interprète les observations visuelles SAM 3.1",
        "tags": ["vision", "classification"],
        "examples": ["waste plastic bottle detected, score 0.9"],
    },
    "geo": {
        "name": "Eco Geo",
        "description": "Contexte géographique — n'invente jamais la position",
        "skill_id": "geo",
        "skill_name": "geo_context",
        "skill_desc": "Résout la zone géographique d'une caméra",
        "tags": ["geo", "location"],
        "examples": ["camera_001 at Plateau Abidjan"],
    },
    "research": {
        "name": "Eco Research",
        "description": "Recherche documentaire — n'invente pas de sources",
        "skill_id": "research",
        "skill_name": "research",
        "skill_desc": "Fournit contexte documentaire vérifiable",
        "tags": ["research", "context"],
        "examples": ["plastic_bottle research"],
    },
    "analysis": {
        "name": "Eco Analysis",
        "description": "Analyse OpenAI/mock — consolide preuves et évalue risque",
        "skill_id": "analyze",
        "skill_name": "analysis",
        "skill_desc": "Consolidation preuves, grille risque, incertitudes",
        "tags": ["analysis", "risk"],
        "examples": ["analyse risk high"],
    },
    "report": {
        "name": "Eco Report",
        "description": "Génère rapport structuré pour dashboard",
        "skill_id": "report",
        "skill_name": "report",
        "skill_desc": "Synthèse structurée observations/incertitudes",
        "tags": ["report", "dashboard"],
        "examples": ["generate report"],
    },
}


def build_sdk_card(agent_id: str, base_url: str = "http://localhost:8000") -> AgentCard:
    """Construit une AgentCard SDK valide pour l'agent donné."""
    defn = AGENT_DEFS[agent_id]
    return AgentCard(
        name=defn["name"],
        description=defn["description"],
        url=f"{base_url}/a2a/{agent_id}",
        version="1.0.0",
        capabilities=AgentCapabilities(streaming=False, push_notifications=False),
        default_input_modes=["text", "data"],
        default_output_modes=["text", "data"],
        skills=[
            AgentSkill(
                id=defn["skill_id"],
                name=defn["skill_name"],
                description=defn["skill_desc"],
                tags=defn["tags"],
                examples=defn["examples"],
            )
        ],
    )


def mount_a2a_routes(app: Any, base_url: str = "http://localhost:8000") -> None:
    """Monte les 5 agents A2A SDK sur l'app FastAPI principale.

    Chaque agent est exposé à /a2a/{agent_id} avec sa JSON-RPC + discovery.
    Le bus in-process reste la voie principale du Router (latence minimale).
    """
    from a2a.server.apps.jsonrpc.fastapi_app import A2AFastAPIApplication
    from a2a.server.request_handlers.default_request_handler import DefaultRequestHandler
    from a2a.server.tasks.inmemory_task_store import InMemoryTaskStore

    # Import ici pour éviter circulaire
    from eco_sentinel.a2a.protocol import a2a_bus

    for agent_id in AGENT_DEFS:
        executor = a2a_bus.get_executor(agent_id)
        if executor is None:
            continue
        card = build_sdk_card(agent_id, base_url)
        handler = DefaultRequestHandler(
            agent_executor=executor,
            task_store=InMemoryTaskStore(),
        )
        a2a_app = A2AFastAPIApplication(agent_card=card, http_handler=handler)
        a2a_app.add_routes_to_app(
            app,
            rpc_url=f"/a2a/{agent_id}",
            agent_card_url=f"/a2a/{agent_id}/.well-known/agent-card.json",
        )
        logger.info("A2A SDK monté: %s -> /a2a/%s", agent_id, agent_id)


class EcoExecutor(AgentExecutor):
    """Executor SDK qui délègue au handler existant (in-process)."""

    def __init__(self, agent_id: str, handler: Any):
        self.agent_id = agent_id
        self.handler = handler

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        # Extrait le payload du dernier message (DataPart ou TextPart)
        payload: dict[str, Any] = {}
        if context.message and context.message.parts:
            for part in context.message.parts:
                root = part.root
                if hasattr(root, "data") and isinstance(root.data, dict):
                    payload.update(root.data)
                elif hasattr(root, "text"):
                    # Tente de parser JSON dans text
                    try:
                        import json

                        data = json.loads(root.text)
                        if isinstance(data, dict):
                            payload.update(data)
                    except Exception:  # nosec B110  # noqa: S110
                        pass

        # Adapte au format A2ARequest interne (compat router)
        from eco_sentinel.a2a.protocol import A2ARequest

        req = A2ARequest(
            target=self.agent_id,
            capability=AGENT_DEFS[self.agent_id]["skill_id"],
            payload=payload or {},
            correlation_id=context.context_id or "",
        )

        try:
            result = await self.handler(req)
            # Publie le résultat comme message agent
            import json

            msg = new_agent_text_message(
                text=json.dumps(result, default=str, ensure_ascii=False),
            )
            # Ajoute aussi une DataPart structurée
            from a2a.types import DataPart, Part

            msg.parts.append(Part(root=DataPart(data=result)))
            await event_queue.enqueue_event(msg)
        except Exception as e:
            logger.exception("Executor %s error: %s", self.agent_id, e)
            msg = new_agent_text_message(text=f"error: {e}")
            await event_queue.enqueue_event(msg)

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        from a2a.types import TaskState, TaskStatus, TaskStatusUpdateEvent

        await event_queue.enqueue_event(
            TaskStatusUpdateEvent(
                task_id=context.task_id or "",
                context_id=context.context_id or "",
                status=TaskStatus(state=TaskState.canceled),
                final=True,
            )
        )
