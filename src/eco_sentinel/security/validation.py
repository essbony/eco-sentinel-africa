"""Validations sécurité : taille image, injection prompt, CORS."""

import re

MAX_IMAGE_BYTES = 5_000_000
MAX_SOURCE_ID_LEN = 128

PROMPT_INJECTION_PATTERNS = [
    r"ignore previous instructions",
    r"system prompt",
    r"jailbreak",
]


def validate_source_id(source_id: str) -> str:
    if not source_id or len(source_id) > MAX_SOURCE_ID_LEN:
        raise ValueError("source_id invalide")
    if not re.match(r"^[a-zA-Z0-9_\-]+$", source_id):
        raise ValueError("source_id caractères autorisés: alphanum _ -")
    return source_id


def validate_image_size(data: bytes, max_bytes: int = MAX_IMAGE_BYTES) -> None:
    if len(data) > max_bytes:
        raise ValueError(f"image {len(data)} > {max_bytes} bytes")
    if len(data) == 0:
        raise ValueError("image vide")


def sanitize_prompt(text: str) -> str:
    lower = text.lower()
    for pat in PROMPT_INJECTION_PATTERNS:
        if pat in lower:
            raise ValueError(f"prompt injection détecté: {pat}")
    return text
