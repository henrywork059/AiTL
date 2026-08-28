from __future__ import annotations

from dataclasses import dataclass
import ipaddress
import json
from threading import Event, RLock, Thread, current_thread
import time
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
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
DEFAULT_FETCH_INTERVAL_MS = 250
FETCH_TIMEOUT_SECONDS = 3.0
STATUS_REFRESH_SECONDS = 2.0
MAX_JSON_RESPONSE_BYTES = 32 * 1024

CAMERA_SETTING_KEYS = (
    "frame_size",
    "jpeg_quality",
    "brightness",
    "contrast",
    "saturation",
    "special_effect",
    "awb",
    "awb_gain",
    "wb_mode",
    "aec",
    "aec2",
    "ae_level",
    "aec_value",
    "agc",
    "agc_gain",
    "gainceiling",
    "bpc",
    "wpc",
    "raw_gma",
    "lenc",
    "hmirror",
    "vflip",
    "dcw",
    "colorbar",
)


class _NoRedirectHandler(HTTPRedirectHandler):
    """Keep the camera transport on the explicitly validated ESP host."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        return None


@dataclass(frozen=True)
class RemoteCapture:
    content: bytes
    content_type: str
    http_status: int


JsonRequester = Callable[[str, str, str, dict[str, str] | None], dict]
CaptureFetcher = Callable[[str], RemoteCapture]


def normalize_private_lan_ipv4(value: str) -> str:
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
    """Control an AiTL ESP camera session and pull JPEGs only after PC-side start."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._stop_event = Event()
        self._thread: Thread | None = None
        self._host: str | None = None
        self._source_id = "esp32_cam_01"
        self._fetch_interval_ms = DEFAULT_FETCH_INTERVAL_MS
        self._streaming_requested = False
        self._settings: dict | None = None
        self._device_status: dict = {}
        self._device_reachable = False
        self._connected_at_ms: int | None = None
        self._stream_started_at_ms: int | None = None
        self._last_probe_at_ms: int | None = None
        self._last_probe_monotonic = 0.0
        self._last_attempt_at_ms: int | None = None
        self._last_success_at_ms: int | None = None
        self._last_http_status: int | None = None
        self._last_frame_number: int | None = None
        self._last_frame_bytes = 0
        self._successful_fetches = 0
        self._failed_fetches = 0
        self._last_error: str | None = None
        self._json_requester: JsonRequester = self._request_json
        self._fetcher: CaptureFetcher = self._fetch_capture

    def _capture_url(self, host: str) -> str:
        return f"http://{host}/capture"

    def _status_url(self, host: str) -> str:
        return f"http://{host}/status"

    def _request_json(
        self,
        host: str,
        path: str,
        method: str = "GET",
        query: dict[str, str] | None = None,
    ) -> dict:
        url = f"http://{host}{path}"
        if query:
            url += "?" + urlencode(query)
        request = Request(
            url,
            data=b"" if method != "GET" else None,
            headers={
                "Accept": "application/json",
                "User-Agent": "AiTL-PC-Studio/0.3.3",
                "Connection": "close",
            },
            method=method,
        )
        try:
            opener = build_opener(_NoRedirectHandler())
            with opener.open(request, timeout=FETCH_TIMEOUT_SECONDS) as response:
                status = int(getattr(response, "status", 200))
                payload = response.read(MAX_JSON_RESPONSE_BYTES + 1)
        except HTTPError as exc:
            body = ""
            try:
                body = exc.read(512).decode("utf-8", errors="replace")
            except Exception:
                body = ""
            raise AppError(
                ErrorCode.CAMERA_NOT_CONNECTED,
                f"ESP camera control request {path} returned HTTP {exc.code}.",
                status_code=502,
                details={"host": host, "path": path, "http_status": exc.code, "response": body},
            ) from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise AppError(
                ErrorCode.CAMERA_NOT_CONNECTED,
                f"PC Studio could not reach the ESP32-CAM {path} endpoint.",
                status_code=502,
                details={"host": host, "path": path, "reason": str(exc)},
            ) from exc

        if status < 200 or status >= 300:
            raise AppError(
                ErrorCode.CAMERA_NOT_CONNECTED,
                f"ESP camera control request {path} returned HTTP {status}.",
                status_code=502,
                details={"host": host, "path": path, "http_status": status},
            )
        if len(payload) > MAX_JSON_RESPONSE_BYTES:
            raise AppError(
                ErrorCode.CAMERA_FRAME_INVALID,
                "ESP camera control response was unexpectedly large.",
                status_code=502,
                details={"host": host, "path": path},
            )
        try:
            parsed = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise AppError(
                ErrorCode.CAMERA_FRAME_INVALID,
                "ESP camera control response was not valid JSON.",
                status_code=502,
                details={"host": host, "path": path},
            ) from exc
        if not isinstance(parsed, dict):
            raise AppError(
                ErrorCode.CAMERA_FRAME_INVALID,
                "ESP camera control response must be a JSON object.",
                status_code=502,
                details={"host": host, "path": path},
            )
        return parsed

    def _fetch_capture(self, host: str) -> RemoteCapture:
        request = Request(
            self._capture_url(host),
            headers={
                "Accept": "image/jpeg",
                "User-Agent": "AiTL-PC-Studio/0.3.3",
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
                "ESP /capture must return image/jpeg.",
                status_code=415,
                details={"host": host, "content_type": content_type},
            )
        return RemoteCapture(content=content, content_type="image/jpeg", http_status=status)

    def _settings_query(self, settings: dict) -> dict[str, str]:
        query: dict[str, str] = {}
        for key in CAMERA_SETTING_KEYS:
            if key not in settings:
                raise AppError(
                    ErrorCode.INVALID_REQUEST,
                    f"Missing remote camera setting: {key}.",
                    status_code=422,
                    details={"setting": key},
                )
            value = settings[key]
            if isinstance(value, bool):
                query[key] = "1" if value else "0"
            else:
                query[key] = str(value)
        return query

    def _stop_worker(self) -> None:
        with self._lock:
            thread = self._thread
            stop_event = self._stop_event
            stop_event.set()

        if thread is not None and thread.is_alive() and thread is not current_thread():
            thread.join(timeout=4.0)

        with self._lock:
            if self._thread is thread:
                self._thread = None

    def _record_success(self, capture: RemoteCapture, frame_number: int) -> None:
        now_ms = int(time.time() * 1000)
        with self._lock:
            self._last_attempt_at_ms = now_ms
            self._last_success_at_ms = now_ms
            self._last_http_status = capture.http_status
            self._last_frame_number = frame_number
            self._last_frame_bytes = len(capture.content)
            self._successful_fetches += 1
            self._device_reachable = True
            self._last_error = None

    def _record_failure(self, message: str, http_status: int | None = None) -> None:
        now_ms = int(time.time() * 1000)
        with self._lock:
            self._last_attempt_at_ms = now_ms
            self._last_http_status = http_status
            self._failed_fetches += 1
            self._device_reachable = False
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

    def connect(self, *, host: str, source_id: str) -> dict:
        """Connect to control/status only. Do not request image bytes."""
        normalized_host = normalize_private_lan_ipv4(host)
        device = self._json_requester(normalized_host, "/status", "GET", None)
        if device.get("camera_ready") is False:
            raise AppError(
                ErrorCode.CAMERA_NOT_CONNECTED,
                "ESP32-CAM reports that its camera sensor is not ready.",
                status_code=502,
                details={"host": normalized_host},
            )

        self.disconnect()
        now_ms = int(time.time() * 1000)
        with self._lock:
            self._host = normalized_host
            self._source_id = source_id
            self._device_status = device
            self._device_reachable = True
            self._connected_at_ms = now_ms
            self._last_probe_at_ms = now_ms
            self._last_probe_monotonic = time.monotonic()
            self._streaming_requested = False
            self._stream_started_at_ms = None
            self._settings = device.get("settings") if isinstance(device.get("settings"), dict) else None
            self._last_error = None

        logger.info(
            "Remote ESP camera control connection established",
            extra={"host": normalized_host, "source_id": source_id},
        )
        return self.status()

    def start_stream(self, *, settings: dict, fetch_interval_ms: int = DEFAULT_FETCH_INTERVAL_MS) -> dict:
        """Apply PC-owned settings first, activate ESP session second, then pull frames."""
        interval = int(fetch_interval_ms)
        if interval < MIN_FETCH_INTERVAL_MS or interval > MAX_FETCH_INTERVAL_MS:
            raise AppError(
                ErrorCode.INVALID_REQUEST,
                f"Remote camera fetch interval must be {MIN_FETCH_INTERVAL_MS}-{MAX_FETCH_INTERVAL_MS} ms.",
                status_code=422,
                details={"fetch_interval_ms": interval},
            )

        with self._lock:
            host = self._host
        if host is None:
            raise AppError(
                ErrorCode.CAMERA_NOT_CONNECTED,
                "Connect to the ESP32-CAM before starting the stream.",
                status_code=409,
            )

        self._stop_worker()

        # Ensure a prior ESP session is not left active before changing settings.
        try:
            self._json_requester(host, "/stop", "POST", None)
        except AppError:
            pass

        applied = self._json_requester(host, "/config", "POST", self._settings_query(settings))
        started = self._json_requester(host, "/start", "POST", None)
        if started.get("session_active") is not True:
            raise AppError(
                ErrorCode.CAMERA_STREAM_NOT_STARTED,
                "ESP32-CAM did not confirm an active camera session.",
                status_code=502,
                details={"host": host},
            )

        with self._lock:
            self._settings = applied.get("settings") if isinstance(applied.get("settings"), dict) else dict(settings)
            self._device_status = started
            self._device_reachable = True
            self._fetch_interval_ms = interval
            self._streaming_requested = True
            self._stream_started_at_ms = int(time.time() * 1000)
            self._successful_fetches = 0
            self._failed_fetches = 0
            self._last_http_status = None
            self._last_frame_number = None
            self._last_frame_bytes = 0
            self._last_success_at_ms = None
            self._last_error = None
            self._stop_event = Event()
            stop_event = self._stop_event
            thread = Thread(target=self._run, args=(stop_event,), name="aitl-remote-camera", daemon=True)
            self._thread = thread
            thread.start()

        logger.info(
            "Remote ESP camera stream started",
            extra={"host": host, "source_id": self._source_id, "fetch_interval_ms": interval},
        )
        return self.status()

    def stop_stream(self, *, best_effort: bool = False) -> dict:
        """Stop PC frame pulls, then disable image responses on the ESP session."""
        self._stop_worker()
        with self._lock:
            host = self._host
            self._streaming_requested = False
            self._stream_started_at_ms = None

        if host is not None:
            try:
                device = self._json_requester(host, "/stop", "POST", None)
                with self._lock:
                    self._device_status = device
                    self._device_reachable = True
                    self._last_error = None
            except AppError as exc:
                with self._lock:
                    self._device_reachable = False
                    self._last_error = exc.message
                if not best_effort:
                    raise
        return self.status()

    def disconnect(self) -> dict:
        self.stop_stream(best_effort=True)
        with self._lock:
            self._host = None
            self._device_status = {}
            self._device_reachable = False
            self._connected_at_ms = None
            self._last_probe_at_ms = None
            self._last_probe_monotonic = 0.0
            self._settings = None
            self._last_error = None
        return self.status()

    def stop(self) -> None:
        self.disconnect()

    def _run(self, stop_event: Event) -> None:
        while not stop_event.is_set():
            with self._lock:
                host = self._host
                source_id = self._source_id
                interval_ms = self._fetch_interval_ms
                streaming_requested = self._streaming_requested

            if host is None or not streaming_requested:
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

    def _refresh_device_status_if_due(self) -> None:
        with self._lock:
            host = self._host
            due = host is not None and (time.monotonic() - self._last_probe_monotonic) >= STATUS_REFRESH_SECONDS
        if not due or host is None:
            return
        try:
            device = self._json_requester(host, "/status", "GET", None)
            now_ms = int(time.time() * 1000)
            with self._lock:
                self._device_status = device
                self._device_reachable = True
                self._last_probe_at_ms = now_ms
                self._last_probe_monotonic = time.monotonic()
                if not self._streaming_requested:
                    self._last_error = None
        except AppError as exc:
            with self._lock:
                self._device_reachable = False
                self._last_probe_at_ms = int(time.time() * 1000)
                self._last_probe_monotonic = time.monotonic()
                self._last_error = exc.message

    def status(self, *, refresh_device: bool = False) -> dict:
        if refresh_device:
            self._refresh_device_status_if_due()

        with self._lock:
            host = self._host
            thread = self._thread
            stream_requested = self._streaming_requested
            device_status = dict(self._device_status)
            settings = dict(self._settings) if isinstance(self._settings, dict) else None
            result = {
                "configured": host is not None,
                "device_reachable": self._device_reachable,
                "worker_running": bool(thread and thread.is_alive()),
                "streaming": bool(stream_requested and thread and thread.is_alive()),
                "paused_for_simulation": bool(
                    stream_requested and thread and thread.is_alive() and camera_frame_service.simulation_enabled
                ),
                "host": host,
                "source_id": self._source_id if host else None,
                "status_url": self._status_url(host) if host else None,
                "capture_url": self._capture_url(host) if host else None,
                "fetch_interval_ms": self._fetch_interval_ms,
                "connected_at_ms": self._connected_at_ms,
                "stream_started_at_ms": self._stream_started_at_ms,
                "last_probe_at_ms": self._last_probe_at_ms,
                "last_attempt_at_ms": self._last_attempt_at_ms,
                "last_success_at_ms": self._last_success_at_ms,
                "last_http_status": self._last_http_status,
                "last_frame_number": self._last_frame_number,
                "last_frame_bytes": self._last_frame_bytes,
                "successful_fetches": self._successful_fetches,
                "failed_fetches": self._failed_fetches,
                "last_error": self._last_error,
                "settings": settings,
                "device": device_status,
                "control_sequence": ["connect", "config", "start", "capture*", "stop"],
                "prototype_only": True,
            }
        return result


remote_camera_service = RemoteCameraService()
