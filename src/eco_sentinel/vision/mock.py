"""Mock SAM 3.1 — déterministe, testable, documente les limites."""

import asyncio
import hashlib
import time

from eco_sentinel.vision.base import VisionInput, VisionOutput, VisionPort


class MockVisionAdapter(VisionPort):
    """Mock : ne prouve aucune toxicité — pure perception visuelle simulée."""

    def __init__(self, model_id: str = "sam-3.1-mock"):
        self._model_id = model_id

    @property
    def model_id(self) -> str:
        return self._model_id

    async def detect(self, inp: VisionInput) -> VisionOutput:
        start = time.time()
        await asyncio.sleep(0.01)  # latence simulée

        # Déterministe : hash de l'image → pseudo-détections
        h = hashlib.md5(inp.image_bytes).hexdigest()
        # Si l'image contient le mot "waste" en clair, on simule une détection
        # sinon détection aléatoire basée sur hash (environ 30% de détections)
        has_waste_hint = b"waste" in inp.image_bytes.lower()
        score_seed = int(h[:2], 16)

        results: list[dict] = []
        is_live = inp.source_id in ("camera_live", "camera_video")
        is_file = inp.source_id == "camera_001"
        # Hallucination réduite : sans hint waste, taux bas
        live_trigger = is_live and score_seed < 25  # ~10% live
        file_trigger = is_file and score_seed < 35  # ~14% fichier
        if has_waste_hint or live_trigger or file_trigger or score_seed < 30:
            cats = inp.categories[:4] if has_waste_hint else inp.categories[:3]
            # génère 2-4 boîtes avec positions décalées pour voir multi-détection
            n = 3 if has_waste_hint else (2 if score_seed % 3 != 0 else 1)
            for idx, cat in enumerate(cats[:n]):
                # décalage spatial pour éviter superposition
                x = round(0.08 + idx * 0.28 + (score_seed % 7) / 100, 2)
                y = round(0.18 + (idx % 2) * 0.32 + (score_seed % 5) / 100, 2)
                bw = 0.18 if idx == 0 else 0.16
                bh = 0.22 if idx == 0 else 0.18
                # clamp 0-1
                x = min(0.78, x)
                y = min(0.72, y)
                # segmentation polygon (8 points) autour du bbox pour simuler SAM 3.1
                pad = 0.015
                mx1, my1 = max(0, x - pad), max(0, y - pad)
                mx2, my2 = min(1, x + bw + pad), min(1, y + bh + pad)
                # forme irrégulière
                mask = [
                    [mx1 + bw * 0.15, my1 + bh * 0.05],
                    [mx1 + bw * 0.75, my1 + bh * 0.02],
                    [mx2 - bw * 0.08, my1 + bh * 0.28],
                    [mx2 - bw * 0.04, my1 + bh * 0.72],
                    [mx2 - bw * 0.32, my2 - bh * 0.06],
                    [mx1 + bw * 0.28, my2 - bh * 0.03],
                    [mx1 + bw * 0.06, my1 + bh * 0.65],
                    [mx1 + bw * 0.02, my1 + bh * 0.22],
                ]
                # score garanti haut pour déclencher alerte jury (waste → high)
                base = 0.85 if idx == 0 and has_waste_hint else 0.72
                results.append(
                    {
                        "category": cat,
                        "score": round(base + (score_seed % 12 + idx * 5) / 100, 2),
                        "bbox": {"x": x, "y": y, "width": bw, "height": bh},
                        "mask": mask,
                        "mask_ref": f"mock://mask/{cat}/{idx}",
                        "tracking_id": str(idx + 1),
                    }
                )

        latency = (time.time() - start) * 1000
        return VisionOutput(
            model=self._model_id,
            results=results,
            raw_ref=f"mock://{inp.source_id}/{h[:8]}",
            latency_ms=latency,
            simulated=True,
        )
