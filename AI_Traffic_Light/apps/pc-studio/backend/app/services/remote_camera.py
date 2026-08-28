from __future__ import annotations

from dataclasses import dataclass
import ipaddress
from threading import Event, RLock, Thread, current_thread
import time
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

from app.core.error_codes import ErrorCode
from app.core.exceptions import AppError
from app.core.logging_config import get_logger
from app.services.camera_frames import MAX_FRAME_BYTES, camera_frame_service

logger = get_logger(__name__)

_PRIVATE_LAN_NETWORKS = (
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
)
MIN_FETCH_INTERVAL_MS = 100
MAX_FETCH_INTERVAL_MS = 5000
DEFAULT_FETCH_INTERVAL_MS = 500
FETCH_TIMEOUT_SECONDS = 3.0


class _NoRedirectHandler(HTTPRedirectHandler):
    """Do not follow camera redirects outside the validated LAN target."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        return None


@dataclass(frozen=True)
class RemoteCapture:
    content: bytes
    content_type: str
    http_status: int


def normalize_private_lan_ipv4(value: str) -> str:
    """Validate one literal RFC1918 IPv4 address for the prototype camera puller."""
    candidate = value.strip()
    try:
        address = ipaddress.ip_address(candidate)
    except ValueError as exc:
        raise AppError(
            ErrorCode.CAMERA_SOURCE_INVALID,
            "ESP camera address must be a literal private-LAN IPv4 address, for example 192.168.1.87.",
            status_code=422,
            details={"host": candidate},
        ) from exc

    if not isinstance(address, ipaddress.IPv4Address) or not any(address in network for network in _PRIVATE_LAN_NETWORKS):
        raise AppError(
            ErrorCode.CAMERA_SOURCE_INVALID,
            "ESP camera address must be inside 10/8, 172.16/12, or 192.168/16.",
            status_code=422,
            details={"host": candidate},
        )
    return str(address)


class RemoteCameraService:
    """Pull JPEG snapshots from a stock ESP32 CameraWebServer into CameraFrameService."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._stop_event = Event()
        self._thread: Thread | None = None
        self._host: str | None = None
        self._source_id = "esp32_cam_01"
        self._fetch_interval_ms = DEFAULT_FETCH_INTERVAL_MS
        self._started_at_ms: int | None = None
        self._last_attempt_at_ms: int | None = None
        self._last_success_at_ms: int | None = None
        self._last_http_status: int | None = None
        self._last_frame_number: int | None = None
        self._last_frame_bytes = 0
        self._successful_fetches = 0
        self._failed_fetches = 0
        self._last_error: str | None = None
        self._fetcher: Callable[[str], RemoteCapture] = self._fetch_capture

    def _capture_url(self, host: str) -> str:
        return f"http://{host}/capture"

    def _stream_url(self, host: str) -> str:
        return f"http://{host}:81/stream"

    def _fetch_capture(self, host: str) -> RemoteCapture:
        request = Request(
            self._capture_url(host),
            headers={
                "Accept": "image/jpeg",
                "User-Agent": "AiTL-PC-Studio/0.3",
                "Connection": "close",
            },
            method="GET",
        )
        try:
            opener = build_opener(_NoRedirectHandler())
            with opener.open(request, timeout=FETCH_TIMEOUT_SECONDS) as response:
                status = int(getattr(response, "status", 200))
                content_type = response.headers.get_content_type().lower()
                content = response.read(MAX_FRAME_BYTES + 1)
        except HTTPError as exc:
            raise AppError(
                ErrorCode.CAMERA_NOT_CONNECTED,
                f"ESP camera returned HTTP {exc.code} for /capture.",
                status_code=502,
                details={"host": host, "http_status": exc.code},
            ) from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise AppError(
                ErrorCode.CAMERA_NOT_CONNECTED,
                "PC Studio could not reach the ESP32-CAM /capture endpoint.",
                status_code=502,
                details={"host": host, "reason": str(exc)},
            ) from exc

        if status < 200 or status >= 300:
            raise AppError(
                ErrorCode.CAMERA_NOT_CONNECTED,
                f"ESP camera returned HTTP {status} for /capture.",
                status_code=502,
                details={"host": host, "http_status": status},
            )
        if len(content) > MAX_FRAME_BYTES:
            raise AppError(
                ErrorCode.CAMERA_FRAME_TOO_LARGE,
                "ESP camera frame exceeded the backend 8 MiB frame limit.",
                status_code=413,
                details={"host": host, "max_size_bytes": MAX_FRAME_BYTES},
            )
        if content_type not in {"image/jpeg", "image/jpg"}:
            raise AppError(
                ErrorCode.CAMERA_FRAME_TYPE_UNSUPPORTED,
                "ESP CameraWebServer /capture must return image/jpeg.",
                status_code=415,
                details={"host": host, "content_type": content_type},
            )
        return RemoteCapture(content=content, content_type="image/jpeg", http_status=status)

    def _record_success(self, capture: RemoteCapture, frame_number: int) -> None:
        now_ms = int(time.time() * 1000)
        with self._lock:
            self._last_attempt_at_ms = now_ms
            self._last_success_at_ms = now_ms
            self._last_http_status = capture.http_status
            self._last_frame_number = frame_number
            self._last_frame_bytes = len(capture.content)
            self._successful_fetches += 1
            self._last_error = None

    def _record_failure(self, message: str, http_status: int | None = None) -> None:
        now_ms = int(time.time() * 1000)
        with self._lock:
            self._last_attempt_at_ms = now_ms
            self._last_http_status = http_status
            self._failed_fetches += 1
            self._last_error = message

    def _ingest_once(self, host: str, source_id: str) -> dict:
        capture = self._fetcher(host)
        frame = camera_frame_service.store_upload(
            source_id=source_id,
            content_type=capture.content_type,
            content=capture.content,
        )
        self._record_success(capture, frame.frame_number)
        return frame.metadata()

    def connect(self, *, host: str, source_id: str, fetch_interval_ms: int = DEFAULT_FETCH_INTERVAL_MS) -> dict:
        normalized_host = normalize_private_lan_ipv4(host)
        interval = int(fetch_interval_ms)
        if interval < MIN_FETCH_INTERVAL_MS or interval > MAX_FETCH_INTERVAL_MS:
            raise AppError(
                ErrorCode.INVALID_REQUEST,
                f"Remote camera fetch interval must be {MIN_FETCH_INTERVAL_MS}-{MAX_FETCH_INTERVAL_MS} ms.",
                status_code=422,
                details={"fetch_interval_ms": interval},
            )

        # Probe before changing active configuration. This also gives the existing
        # PC-side camera pipeline an immediate real frame.
        try:
            frame_metadata = self._ingest_once(normalized_host, source_id)
        except AppError:
            raise
        except Exception as exc:
            raise AppError(
                ErrorCode.CAMERA_NOT_CONNECTED,
                "PC Studio could not read a valid frame from the ESP32-CAM.",
                status_code=502,
                details={"host": normalized_host, "reason": str(exc)},
            ) from exc

        self.disconnect()
        with self._lock:
            self._host = normalized_host
            self._source_id = source_id
            self._fetch_interval_ms = interval
            self._started_at_ms = int(time.time() * 1000)
            self._last_success_at_ms = self._started_at_ms
            self._last_http_status = 200
            self._last_frame_number = int(frame_metadata["frame_number"])
            self._last_frame_bytes = int(frame_metadata["size_bytes"])
            self._successful_fetches = 1
            self._failed_fetches = 0
            self._last_error = None
            self._stop_event = Event()
            stop_event = self._stop_event
            thread = Thread(target=self._run, args=(stop_event,), name="aitl-remote-camera", daemon=True)
            self._thread = thread
            thread.start()

        logger.info(
            "Remote ESP camera connected",
            extra={"host": normalized_host, "source_id": source_id, "fetch_interval_ms": interval},
        )
        return self.status()

    def disconnect(self) -> dict:
        with self._lock:
            thread = self._thread
            stop_event = self._stop_event
            stop_event.set()
            self._host = None
            self._started_at_ms = None

        if thread is not None and thread.is_alive() and thread is not current_thread():
            thread.join(timeout=4.0)

        with self._lock:
            if self._thread is thread:
                self._thread = None

        return self.status()

    def stop(self) -> None:
        """Stop the background worker during FastAPI shutdown."""
        self.disconnect()

    def _run(self, stop_event: Event) -> None:
        while not stop_event.is_set():
            with self._lock:
                host = self._host
                source_id = self._source_id
                interval_ms = self._fetch_interval_ms

            if host is None:
                return

            if camera_frame_service.simulation_enabled:
                stop_event.wait(max(0.1, interval_ms / 1000.0))
                continue

            try:
                self._ingest_once(host, source_id)
            except AppError as exc:
                self._record_failure(exc.message, exc.details.get("http_status") if exc.details else None)
            except Exception as exc:
                self._record_failure(str(exc))

            stop_event.wait(interval_ms / 1000.0)

    def status(self) -> dict:
        with self._lock:
            host = self._host
            thread = self._thread
            last_success_at_ms = self._last_success_at_ms
            last_attempt_at_ms = self._last_attempt_at_ms
            started_at_ms = self._started_at_ms
            source_id = self._source_id
            interval_ms = self._fetch_interval_ms
            successful_fetches = self._successful_fetches
            failed_fetches = self._failed_fetches
            last_http_status = self._last_http_status
            last_frame_number = self._last_frame_number
            last_frame_bytes = self._last_frame_bytes
            last_error = self._last_error

        now_ms = int(time.time() * 1000)
        worker_running = bool(thread and thread.is_alive() and host)
        success_age_ms = now_ms - last_success_at_ms if last_success_at_ms is not None else None
        connected = bool(worker_running and success_age_ms is not None and success_age_ms <= max(5000, interval_ms * 4))
        paused_for_simulation = bool(worker_running and camera_frame_service.simulation_enabled)

        return {
            "configured": host is not None,
            "worker_running": worker_running,
            "connected": connected,
            "paused_for_simulation": paused_for_simulation,
            "host": host,
            "source_id": source_id if host else None,
            "capture_url": self._capture_url(host) if host else None,
            "stream_url": self._stream_url(host) if host else None,
            "fetch_interval_ms": interval_ms,
            "started_at_ms": started_at_ms,
            "last_attempt_at_ms": last_attempt_at_ms,
            "last_success_at_ms": last_success_at_ms,
            "success_age_ms": success_age_ms,
            "last_http_status": last_http_status,
            "last_frame_number": last_frame_number,
            "last_frame_bytes": last_frame_bytes,
            "successful_fetches": successful_fetches,
            "failed_fetches": failed_fetches,
            "last_error": last_error,
            "prototype_only": True,
        }


remote_camera_service = RemoteCameraService()
