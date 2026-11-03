"""Logging structuré Eco Sentinel."""

import logging
import sys
import uuid
from contextvars import ContextVar

correlation_id_var: ContextVar[str | None] = ContextVar("correlation_id", default=None)


def get_correlation_id() -> str:
    cid = correlation_id_var.get()
    if cid is None:
        cid = str(uuid.uuid4())
        correlation_id_var.set(cid)
    return cid


def set_correlation_id(cid: str) -> None:
    correlation_id_var.set(cid)


class CorrelationFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = correlation_id_var.get() or "-"  # type: ignore[attr-defined]
        return True


def get_logger(name: str = "eco_sentinel") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        fmt = "%(asctime)s | %(levelname)s | %(name)s | [%(correlation_id)s] | %(message)s"
        handler.setFormatter(logging.Formatter(fmt))
        handler.addFilter(CorrelationFilter())
        logger.addHandler(handler)
        level_name = "INFO"
        try:
            from eco_sentinel.config import get_settings

            level_name = get_settings().log_level
        except Exception:  # nosec B110  # noqa: S110
            pass
        logger.setLevel(getattr(logging, level_name.upper(), logging.INFO))
        logger.propagate = False
    return logger
