from eco_sentinel.vision.base import VisionInput, VisionOutput, VisionPort
from eco_sentinel.vision.mock import MockVisionAdapter
from eco_sentinel.vision.sam31 import SAM31Adapter

__all__ = ["MockVisionAdapter", "SAM31Adapter", "VisionInput", "VisionOutput", "VisionPort"]


def get_vision_adapter(provider: str = "mock") -> VisionPort:
    p = (provider or "mock").strip().lower()
    # meta, sam31, sam-3.1 tous routent vers SAM31Adapter via Meta
    if p in ("sam31", "sam-3.1", "sam_31", "meta"):
        from eco_sentinel.config import get_settings

        s = get_settings()
        model = getattr(s, "vision_model", "sam-3.1")
        timeout = float(getattr(s, "vision_timeout_s", 10.0))
        # Si pas de clé, le SAM31Adapter fera fallback mock tracé
        return SAM31Adapter(model_id=model, timeout_s=timeout)
    return MockVisionAdapter()
