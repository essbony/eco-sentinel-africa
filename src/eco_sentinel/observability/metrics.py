"""Métriques in-memory pour observabilité."""

import time
from collections import Counter

_counters: Counter[str] = Counter()
_latencies: dict[str, list[float]] = {}


def inc(metric: str, amount: int = 1) -> None:
    _counters[metric] += amount


def observe_latency(metric: str, ms: float) -> None:
    _latencies.setdefault(metric, []).append(ms)
    if len(_latencies[metric]) > 1000:
        _latencies[metric] = _latencies[metric][-1000:]


def snapshot() -> dict:
    return {
        "counters": dict(_counters),
        "latencies_avg_ms": {k: sum(v) / len(v) if v else 0 for k, v in _latencies.items()},
        "ts": time.time(),
    }
