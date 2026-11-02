"""Port Vision — abstraction SAM 3.1."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class VisionInput:
    source_id: str
    image_bytes: bytes
    categories: list[str]
    timestamp: float


@dataclass
class VisionOutput:
    model: str
    results: list[dict]
    raw_ref: str | None = None
    latency_ms: float | None = None
    simulated: bool = False


class VisionPort(ABC):
    @abstractmethod
    async def detect(self, inp: VisionInput) -> VisionOutput:
        """Détecte les catégories demandées."""

    @property
    @abstractmethod
    def model_id(self) -> str:
        pass
