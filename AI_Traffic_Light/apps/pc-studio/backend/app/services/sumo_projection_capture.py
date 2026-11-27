"""Convert one isolated native projection into explicit evaluation-only capture frames.

Do not use these frames as selected camera observations, detector input or saved
legacy camera sources. Capture service reuse is exercised only in a temporary
evaluation dataset. Native metadata/CSV remain separate from dataset metadata.
"""
from __future__ import annotations

from app.services.camera_frames import CameraFrame
from app.services.sumo_projection import HEIGHT, WIDTH, VIEW_FLIPS
from app.services.observation_identity import EVALUATION_ORIGINS, evaluation_source_id
import cv2
import numpy as np


def evaluation_frames(meta: dict, views: dict[str, bytes], *, received_at_ms: int) -> tuple[CameraFrame, ...]:
    if meta.get("provenance") not in EVALUATION_ORIGINS or meta.get("width") != WIDTH or meta.get("height") != HEIGHT:
        raise ValueError("Unexpected native capture provenance or dimensions")
    generation, tick = meta.get("generation"), meta.get("tick")
    if type(generation) is not int or generation < 0 or type(tick) is not int or tick < 0 or type(received_at_ms) is not int or received_at_ms < 0:
        raise ValueError("Invalid native capture identity")
    if set(views) != set(VIEW_FLIPS):
        raise ValueError("Expected four coherent native views")
    frames = []
    canonical = None
    for source, flip in VIEW_FLIPS.items():
        content = views[source]
        image = cv2.imdecode(np.frombuffer(content, np.uint8), cv2.IMREAD_COLOR)
        if not content.startswith(b"\x89PNG\r\n\x1a\n") or image is None or image.shape != (HEIGHT, WIDTH, 3):
            raise ValueError("Invalid native capture PNG")
        if canonical is None:
            canonical = image
        elif not np.array_equal(image, cv2.flip(canonical, flip)):
            raise ValueError("Native capture views differ from canonical frame")
        frames.append(CameraFrame(content=content, content_type="image/png",
                                  source_id=evaluation_source_id(meta["provenance"],generation,source),
                                  width=WIDTH, height=HEIGHT, received_at_ms=received_at_ms,
                                  frame_number=tick, origin=meta["provenance"], mode_generation=generation))
    return tuple(frames)
