"""Fresh, distinct source-frame evidence for software-only emergency requests."""
from __future__ import annotations

from typing import Any


def confirmed_emergency(evidence: dict[str, Any] | None, now_ms: int, max_age_ms: int) -> bool:
    """Require two distinct frame IDs on one source, at least one second apart."""
    if not evidence:
        return False
    by_source: dict[str, dict[int, int]] = {}
    for (source, number, timestamp, model), _ in evidence["positive"].items():
        if model != evidence["model_id"] or not 0 <= now_ms - timestamp <= max_age_ms:
            continue
        frames = by_source.setdefault(source, {})
        frames[number] = min(timestamp, frames.get(number, timestamp))
    return any(len(frames) >= 2 and max(frames.values()) - min(frames.values()) >= 1000
               for frames in by_source.values())
