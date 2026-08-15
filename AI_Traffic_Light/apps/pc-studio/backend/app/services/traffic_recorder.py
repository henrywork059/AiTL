from __future__ import annotations

from threading import Event, Lock, Thread

from app.core.logging_config import get_logger
from app.services.traffic_history import traffic_history_service
from app.services.traffic_logic import get_live_traffic_state

logger = get_logger(__name__)


class TrafficRecorderService:
    """Background sampler that records detection-backed traffic occupancy while the backend runs."""

    def __init__(self) -> None:
        self._stop_event = Event()
        self._thread: Thread | None = None
        self._lock = Lock()

    def start(self) -> None:
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop_event.clear()
            self._thread = Thread(target=self._run, name="aitl-traffic-history", daemon=True)
            self._thread.start()
        logger.info(
            "Traffic history recorder started",
            extra={"sample_interval_ms": traffic_history_service.sample_interval_ms},
        )

    def stop(self) -> None:
        with self._lock:
            thread = self._thread
            self._stop_event.set()
        if thread is not None and thread.is_alive():
            thread.join(timeout=2.0)
        with self._lock:
            self._thread = None
        logger.info("Traffic history recorder stopped")

    def _run(self) -> None:
        interval_seconds = traffic_history_service.sample_interval_ms / 1000
        while not self._stop_event.wait(interval_seconds):
            try:
                state = get_live_traffic_state()
                traffic_history_service.record_state(state)
            except Exception:  # noqa: BLE001 - background recorder must not terminate the API process.
                logger.exception("Traffic history background sample failed")


traffic_recorder_service = TrafficRecorderService()
