"""Client Meta unifié — tous les Muse (SAM 3.1 / Wonder / Spark) via le même base_url + OpenAI.

Conforme à l'intro et à la doc officielle Meta Dev AI : un seul BASE_URL et une seule API
d'inférence OpenAI-compatible pour tous les modèles Muse (vision + router + agents + analysis).

Exemple officiel (sync) — doc Meta :
    import os
    from openai import OpenAI
    client = OpenAI(
        base_url="https://api.meta.ai/v1",
        api_key=os.environ["MODEL_API_KEY"],
    )
    response = client.responses.create(
        model="muse-spark-1.3",
        input="What is the capital of France?",
    )
    print(response.model_dump_json(indent=2))

Le pipeline async du projet utilise AsyncOpenAI avec la même config (voir get_meta_client).
"""

import base64
import json
from typing import Any

from eco_sentinel.config import get_settings
from eco_sentinel.core.logging import get_logger

logger = get_logger("eco_sentinel.meta")

_client: Any | None = None
_sync_client: Any | None = None


def get_sync_client() -> Any | None:
    """Client OpenAI sync — exemple exact de la doc Meta (même base_url/api_key)."""
    global _sync_client
    if _sync_client is not None:
        return _sync_client
    try:
        settings = get_settings()
        api_key = settings.effective_api_key  # type: ignore[attr-defined]
        base_url = settings.effective_base_url  # type: ignore[attr-defined]
        if not api_key:
            logger.warning("Meta client sync non configuré — MODEL_API_KEY manquant")
            return None
        from openai import OpenAI

        _sync_client = OpenAI(api_key=api_key, base_url=base_url)
        logger.info("Meta client sync initialisé base_url=%s", base_url)
        return _sync_client
    except Exception as e:
        logger.warning("Impossible d'initialiser le client Meta sync: %s", e)
        return None


def reset_sync_client() -> None:
    global _sync_client
    _sync_client = None


def get_meta_client() -> Any | None:
    """Retourne AsyncOpenAI Meta (MODEL_API_KEY + BASE_URL)."""
    global _client
    if _client is not None:
        return _client
    try:
        settings = get_settings()
        api_key = settings.effective_api_key  # type: ignore[attr-defined]
        base_url = settings.effective_base_url  # type: ignore[attr-defined]
        if not api_key:
            logger.warning("Meta client non configuré — MODEL_API_KEY manquant")
            return None
        from openai import AsyncOpenAI

        _client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        logger.info("Meta client initialisé base_url=%s", base_url)
        return _client
    except Exception as e:
        logger.warning("Impossible d'initialiser le client Meta: %s", e)
        return None


def reset_meta_client() -> None:
    global _client
    _client = None


def extract_text(resp: Any) -> str:
    """Extrait le texte depuis Responses API ou Chat Completions."""
    # Responses API: resp.output_text ou resp.output[*].content
    if hasattr(resp, "output_text") and resp.output_text:
        text = str(resp.output_text).strip()
        if text:
            return text
    if hasattr(resp, "output") and resp.output:
        texts: list[str] = []
        for item in resp.output:
            contents = getattr(item, "content", None)
            if contents:
                for c in contents:
                    t = getattr(c, "text", None)
                    if t and str(t).strip():
                        texts.append(str(t).strip())
        if texts:
            joined = "\n".join(texts).strip()
            if joined:
                return joined
    # Chat Completions
    if hasattr(resp, "choices") and resp.choices:
        msg = resp.choices[0].message
        content = getattr(msg, "content", None)
        if content:
            if isinstance(content, str) and content.strip():
                return content.strip()
            # content could be list
            try:
                joined = "".join(
                    part.get("text", "") if isinstance(part, dict) else str(part)
                    for part in content
                ).strip()
                if joined:
                    return joined
            except Exception:  # nosec B110  # noqa: S110
                pass
    # Aucun texte exploitable → signal d'échec, ne pas fallback vers str(resp)
    return ""


async def call_meta_responses(
    *,
    model: str,
    instructions: str | None = None,
    input_text: str,
    image_bytes: bytes | None = None,
    image_format: str = "jpeg",
    timeout_s: float = 20.0,
    response_format_json: bool = False,
    max_tokens: int = 600,
) -> str | None:
    """
    Appelle l'API Responses de Meta via le client OpenAI compatible.
    Tente Responses API puis fallback Chat Completions.
    Retourne le texte brut ou None si échec.
    """
    import asyncio

    client = get_meta_client()
    if client is None:
        return None

    # Construit l'input pour Responses API
    # Pour image : input avec type image_url
    try:
        # Use Responses API first
        kwargs: dict[str, Any] = {
            "model": model,
            "input": input_text,
        }
        if instructions:
            kwargs["instructions"] = instructions
        if response_format_json:
            # Responses API: text.format
            kwargs["text"] = {"format": {"type": "json_object"}}
        if image_bytes:
            b64 = base64.b64encode(image_bytes).decode()
            mime = "image/png" if image_format == "png" else "image/jpeg"
            kwargs["input"] = [
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": input_text},
                        {"type": "input_image", "image_url": f"data:{mime};base64,{b64}"},
                    ],
                }
            ]

        # Try responses.create
        if hasattr(client, "responses"):
            try:
                resp = await asyncio.wait_for(client.responses.create(**kwargs), timeout=timeout_s)
                return extract_text(resp)
            except Exception as e:
                # Surface error details for debugging
                logger.warning(
                    "Responses API échouée (%s), fallback chat.completions: %s", model, e
                )
        # Fallback chat.completions
        messages: list[dict[str, Any]] = []
        if instructions:
            messages.append({"role": "system", "content": instructions})
        if image_bytes:
            b64 = base64.b64encode(image_bytes).decode()
            mime = "image/png" if image_format == "png" else "image/jpeg"
            messages.append(
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": input_text},
                        {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                    ],
                }
            )
        else:
            messages.append({"role": "user", "content": input_text})

        chat_kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": max_tokens,
        }
        if response_format_json:
            chat_kwargs["response_format"] = {"type": "json_object"}

        resp2 = await asyncio.wait_for(
            client.chat.completions.create(**chat_kwargs), timeout=timeout_s
        )
        return extract_text(resp2)

    except TimeoutError:
        logger.warning("Timeout appel Meta model=%s", model)
        return None
    except Exception as e:
        logger.warning("Erreur appel Meta model=%s: %s", model, e)
        return None


async def call_meta_json(
    *,
    model: str,
    instructions: str,
    input_text: str,
    timeout_s: float = 20.0,
    fallback: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Appelle Meta et parse le JSON retourné. Retourne None si échec."""
    text = await call_meta_responses(
        model=model,
        instructions=instructions,
        input_text=input_text,
        timeout_s=timeout_s,
        response_format_json=True,
        max_tokens=800,
    )
    if not text:
        return fallback
    # Nettoie les fences markdown
    cleaned = text.strip()
    if cleaned.startswith("```"):
        # Retire ```json ... ```
        lines = cleaned.split("\n")
        # enlève première et dernière si fences
        if lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    try:
        return json.loads(cleaned)  # type: ignore[no-any-return]
    except Exception:
        # Tente d'extraire JSON imbriqué
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(cleaned[start : end + 1])  # type: ignore[no-any-return]
            except Exception:  # nosec B110  # noqa: S110
                pass
        logger.warning("Réponse Meta non-JSON model=%s: %.200s", model, text)
        return fallback
