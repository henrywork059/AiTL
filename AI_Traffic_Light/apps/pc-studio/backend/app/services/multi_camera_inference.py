"""One background inference service using the latest frame from every available camera."""
from __future__ import annotations

from threading import Event, Lock, Thread
import time
from typing import Any

from app.core.logging_config import get_logger
from app.services.inference import inference_service
from app.services.camera_frames import camera_frame_service
from app.services.crosswalk_signals import crosswalk_signal_service
from app.services.remote_camera_manager import remote_camera_manager
from app.services.runtime_settings import runtime_settings_service

logger = get_logger(__name__)
STALE_RESULT_MS = 5000


class MultiCameraInferenceService:
    def __init__(self) -> None:
        self._stop = Event()
        self._lock = Lock()
        self._thread: Thread | None = None
        self._results: dict[str, dict[str, Any]] = {}
        self._keys: dict[str, tuple[Any, ...]] = {}

    def start(self) -> None:
        with self._lock:
            if self._thread and self._thread.is_alive():
                return
            self._stop.clear()
            self._thread = Thread(target=self._run, name="aitl-multi-camera-ai", daemon=True)
            self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        thread = self._thread
        if thread and thread.is_alive():
            thread.join(timeout=2.0)
        with self._lock:
            self._thread = None
            self._results.clear()
            self._keys.clear()

    def result(self, source_id: str) -> dict[str, Any]:
        with self._lock:
            item = self._results.get(source_id)
            payload = dict(item) if item else {"source_id": source_id, "frame": None, "error": None}
        if payload.get("frame") is not None and payload.get("model_id") != inference_service.status()["active_model_id"]:
            return {"source_id": source_id, "frame": None, "error": "Model changed"}
        if payload.get("frame") is not None and int(time.time() * 1000) - payload["frame"]["timestamp_ms"] > STALE_RESULT_MS:
            return {"source_id": source_id, "frame": None, "error": "Frame is stale"}
        return payload

    def _run(self) -> None:
        while not self._stop.is_set():
            start = time.monotonic()
            try:
                settings = runtime_settings_service.get()
                model_id = inference_service.status()["active_model_id"]
                if model_id is None:
                    with self._lock:
                        self._results.clear()
                        self._keys.clear()
                else:
                    frames = remote_camera_manager.frames_for_inference()
                    seen = {frame.source_id for frame in frames}
                    with self._lock:
                        for source_id in list(self._results):
                            if source_id not in seen:
                                self._results.pop(source_id, None)
                                self._keys.pop(source_id, None)
                    for frame in frames:
                        if self._stop.is_set():
                            break
                        key = (model_id, settings["default_confidence"], frame.frame_number, frame.received_at_ms)
                        with self._lock:
                            if self._keys.get(frame.source_id) == key:
                                continue
                        try:
                            result = inference_service.detect_frame(frame, confidence_threshold=settings["default_confidence"])
                            if inference_service.status()["active_model_id"] != model_id:
                                break
                            item = {"source_id": frame.source_id, "frame": result, "error": None, "model_id": model_id}
                        except Exception as exc:  # One failed camera must not stop others.
                            logger.warning("Camera AI inference failed", extra={"source_id": frame.source_id, "error": str(exc)})
                            item = {"source_id": frame.source_id, "frame": None, "error": str(exc)[:200], "model_id": model_id}
                        with self._lock:
                            self._results[frame.source_id] = item
                            self._keys[frame.source_id] = key
                # Publish per-camera detections to the correct simulated crossing
                # irrespective of whether the Network page is currently open.
                with self._lock:
                    snapshot = dict(self._results)
                active_model_id = inference_service.status()["active_model_id"]
                simulation_enabled = camera_frame_service.simulation_enabled
                now_ms = int(time.time() * 1000)
                virtual_preview = not simulation_enabled and bool(active_model_id) and any(
                    item.get("error") is None and item.get("model_id") == active_model_id
                    and isinstance(item.get("frame"), dict)
                    and isinstance(item["frame"].get("timestamp_ms"), (int, float))
                    and 0 <= now_ms - item["frame"]["timestamp_ms"] <= STALE_RESULT_MS
                    for item in snapshot.values()
                )
                crosswalk_signal_service.ingest_camera_results(
                    snapshot,
                    simulation_enabled=simulation_enabled,
                    simulation_paused=camera_frame_service.simulation_paused,
                    virtual_preview=virtual_preview,
                    model_id=active_model_id,
                )
            except Exception:
                logger.exception("Global multi-camera inference iteration failed")
            try:
                interval = runtime_settings_service.get()["inference_interval_ms"] / 1000
            except Exception:
                interval = 0.5
            self._stop.wait(max(0.01, interval - (time.monotonic() - start)))


multi_camera_inference_service = MultiCameraInferenceService()
