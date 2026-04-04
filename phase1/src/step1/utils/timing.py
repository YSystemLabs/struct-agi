from __future__ import annotations

from contextlib import contextmanager
from time import perf_counter


@contextmanager
def timed_section(metrics: dict[str, int], key: str):
    start = perf_counter()
    try:
        yield
    finally:
        elapsed_ms = int((perf_counter() - start) * 1000)
        metrics[key] = metrics.get(key, 0) + elapsed_ms
