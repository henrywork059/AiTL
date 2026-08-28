from __future__ import annotations

from dataclasses import dataclass
import ipaddress
import json
from threading import Event, RLock, Thread, current_thread
import time
from typing import BinaryIO, Callable
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

MIN_TARGET_FPS = 1
MAX_TARGET_FPS = 30
DEFAULT_TARGET_FPS = 15
STREAM_CONNECT_TIMEOUT_SECONDS = 3.0
STREAM_RETRY_SECONDS = 0.20
STATUS_REFRESH_SECONDS = 2.0
MAX_JSON_RESPONSE_BYTES = 32 * 1024
STREAM_READ_BYTES = 4096
STREAM_BUFFER_SLACK_BYTES = 128 * 1024

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
    """Keep all ESP transport requests on the validated private-LAN host."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        return None


@dataclass(frozen=True)
class RemoteCapture:
    """Compatibility value used by older focused tests/tools."""

    content: bytes
    content_type: str
    http_status: int


JsonRequester = Callable[[str, str, str, dict[str, str] | None], dict]
StreamOpener = Callable[[str], BinaryIO]


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
    """Control V034 ESP sessions and ingest one persistent low-latency MJPEG stream."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._stop_event = Event()
        self._thread: Thread | None = None
        self._active_stream: BinaryIO | None = None

        self._host: str | None = None
        self._source_id = "esp32_cam_01"
        self._target_fps = DEFAULT_TARGET_FPS
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
        self._stream_reconnects = 0
        self._stream_bytes_received = 0
        self._dropped_stale_frames = 0
        self._last_frame_interval_ms: float | None = None
        self._measured_fps = 0.0
        self._last_error: str | None = None

        self._json_requester: JsonRequester = self._request_json
        self._stream_opener: StreamOpener = self._open_mjpeg_stream

    def _status_url(self, host: str) -> str:
        return f"http://{host}/status"

    def _capture_url(self, host: str) -> str:
        return f"http://{host}/capture"

    def _stream_url(self, host: str) -> str:
        return f"http://{host}:81/stream"

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
                "User-Agent": "AiTL-PC-Studio/0.3.4",
                "Connection": "close",
            },
            method=method,
        )
        try:
            opener = build_opener(_NoRedirectHandler())
            with opener.open(request, timeout=STREAM_CONNECT_TIMEOUT_SECONDS) as response:
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

    def _open_mjpeg_stream(self, host: str) -> BinaryIO:
        request = Request(
            self._stream_url(host),
            headers={
                "Accept": "multipart/x-mixed-replace,image/jpeg",
                "User-Agent": "AiTL-PC-Studio/0.3.4",
                "Connection": "close",
            },
            method="GET",
        )
        try:
            opener = build_opener(_NoRedirectHandler())
            response = opener.open(request, timeout=STREAM_CONNECT_TIMEOUT_SECONDS)
        except HTTPError as exc:
            raise AppError(
                ErrorCode.CAMERA_NOT_CONNECTED,
                f"ESP camera returned HTTP {exc.code} for the MJPEG stream.",
                status_code=502,
                details={"host": host, "http_status": exc.code},
            ) from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise AppError(
                ErrorCode.CAMERA_NOT_CONNECTED,
                "PC Studio could not open the ESP32-CAM MJPEG stream.",
                status_code=502,
                details={"host": host, "reason": str(exc)},
            ) from exc

        status = int(getattr(response, "status", 200))
        if status < 200 or status >= 300:
            response.close()
            raise AppError(
                ErrorCode.CAMERA_NOT_CONNECTED,
                f"ESP camera returned HTTP {status} for the MJPEG stream.",
                status_code=502,
                details={"host": host, "http_status": status},
            )
        return response

    def _settings_query(self, settings: dict, target_fps: int) -> dict[str, str]:
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
            query[key] = "1" if value is True else "0" if value is False else str(value)
        query["stream_fps"] = str(target_fps)
        return query

    def _stop_worker(self) -> None:
        with self._lock:
            thread = self._thread
            stop_event = self._stop_event
            active_stream = self._active_stream
            stop_event.set()

        # Closing the active socket unblocks a pending stream read immediately.
        if active_stream is not None:
            try:
                active_stream.close()
            except Exception:
                pass

        if thread is not None and thread.is_alive() and thread is not current_thread():
            thread.join(timeout=3.0)

        with self._lock:
            if self._thread is thread:
                self._thread = None
            if self._active_stream is active_stream:
                self._active_stream = None

    def _record_frame(self, content: bytes, frame_number: int) -> None:
        now_ms = int(time.time() * 1000)
        with self._lock:
            previous_success = self._last_success_at_ms
            self._last_attempt_at_ms = now_ms
            self._last_success_at_ms = now_ms
            self._last_http_status = 200
            self._last_frame_number = frame_number
            self._last_frame_bytes = len(content)
            self._successful_fetches += 1
            self._device_reachable = True
            self._last_error = None

            if previous_success is not None:
                interval_ms = max(1.0, float(now_ms - previous_success))
                instantaneous_fps = 1000.0 / interval_ms
                self._last_frame_interval_ms = interval_ms
                if self._measured_fps <= 0:
                    self._measured_fps = instantaneous_fps
                else:
                    self._measured_fps = (self._measured_fps * 0.80) + (instantaneous_fps * 0.20)

    def _record_failure(self, message: str, http_status: int | None = None) -> None:
        now_ms = int(time.time() * 1000)
        with self._lock:
            self._last_attempt_at_ms = now_ms
            self._last_http_status = http_status
            self._failed_fetches += 1
            self._device_reachable = False
            self._last_error = message

    def _store_jpeg(self, *, source_id: str, content: bytes) -> None:
        if len(content) > MAX_FRAME_BYTES:
            raise AppError(
                ErrorCode.CAMERA_FRAME_TOO_LARGE,
                "ESP MJPEG frame exceeded the backend 8 MiB frame limit.",
                status_code=413,
                details={"size_bytes": len(content), "max_size_bytes": MAX_FRAME_BYTES},
            )
        frame = camera_frame_service.store_upload(
            source_id=source_id,
            content_type="image/jpeg",
            content=content,
        )
        self._record_frame(content, frame.frame_number)

    def _consume_mjpeg_stream(
        self,
        *,
        stream: BinaryIO,
        source_id: str,
        stop_event: Event,
    ) -> str:
        """Extract JPEG SOI/EOI frames from a multipart stream without queueing stale frames."""
        buffer = bytearray()

        while not stop_event.is_set():
            if camera_frame_service.simulation_enabled:
                return "paused_for_simulation"

            read1 = getattr(stream, "read1", None)
            chunk = read1(STREAM_READ_BYTES) if callable(read1) else stream.read(STREAM_READ_BYTES)
            if not chunk:
                if stop_event.is_set():
                    return "stopped"
                return "stream_ended"

            with self._lock:
                self._stream_bytes_received += len(chunk)
            buffer.extend(chunk)

            latest_complete: bytes | None = None
            complete_count = 0

            while True:
                soi = buffer.find(b"\xff\xd8")
                if soi < 0:
                    # Preserve a possible split SOI marker only.
                    if len(buffer) > 1:
                        del buffer[:-1]
                    break

                if soi > 0:
                    del buffer[:soi]

                eoi = buffer.find(b"\xff\xd9", 2)
                if eoi < 0:
                    if len(buffer) > MAX_FRAME_BYTES + STREAM_BUFFER_SLACK_BYTES:
                        raise AppError(
                            ErrorCode.CAMERA_FRAME_TOO_LARGE,
                            "ESP MJPEG stream contained an oversized/incomplete JPEG frame.",
                            status_code=413,
                        )
                    break

                latest_complete = bytes(buffer[: eoi + 2])
                complete_count += 1
                del buffer[: eoi + 2]

            if latest_complete is not None:
                # If several complete JPEGs arrived in one network read, processing
                # older ones would add latency. Keep only the newest complete frame.
                if complete_count > 1:
                    with self._lock:
                        self._dropped_stale_frames += complete_count - 1
                self._store_jpeg(source_id=source_id, content=latest_complete)

        return "stopped"

    def connect(self, *, host: str, source_id: str) -> dict:
        """Connect to status/control only; V034 still transfers zero images on Connect."""
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

    def start_stream(
        self,
        *,
        settings: dict,
        target_fps: int = DEFAULT_TARGET_FPS,
        fetch_interval_ms: int | None = None,
    ) -> dict:
        """Apply settings, activate ESP session, then open one persistent MJPEG transport."""
        # Compatibility for V033 callers/tests that supplied a capture interval.
        if fetch_interval_ms is not None and target_fps == DEFAULT_TARGET_FPS:
            interval = max(1, int(fetch_interval_ms))
            target_fps = max(MIN_TARGET_FPS, min(MAX_TARGET_FPS, round(1000 / interval)))

        fps = int(target_fps)
        if fps < MIN_TARGET_FPS or fps > MAX_TARGET_FPS:
            raise AppError(
                ErrorCode.INVALID_REQUEST,
                f"Remote camera target_fps must be {MIN_TARGET_FPS}-{MAX_TARGET_FPS}.",
                status_code=422,
                details={"target_fps": fps},
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
        try:
            self._json_requester(host, "/stop", "POST", None)
        except AppError:
            pass

        applied = self._json_requester(host, "/config", "POST", self._settings_query(settings, fps))
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
            self._target_fps = fps
            self._streaming_requested = True
            self._stream_started_at_ms = int(time.time() * 1000)
            self._successful_fetches = 0
            self._failed_fetches = 0
            self._stream_reconnects = 0
            self._stream_bytes_received = 0
            self._dropped_stale_frames = 0
            self._last_http_status = None
            self._last_frame_number = None
            self._last_frame_bytes = 0
            self._last_success_at_ms = None
            self._last_frame_interval_ms = None
            self._measured_fps = 0.0
            self._last_error = None
            self._stop_event = Event()
            stop_event = self._stop_event
            thread = Thread(target=self._run, args=(stop_event,), name="aitl-remote-mjpeg", daemon=True)
            self._thread = thread
            thread.start()

        logger.info(
            "Remote ESP MJPEG stream started",
            extra={"host": host, "source_id": self._source_id, "target_fps": fps},
        )
        return self.status()

    def stop_stream(self, *, best_effort: bool = False) -> dict:
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
                streaming_requested = self._streaming_requested

            if host is None or not streaming_requested:
                return

            if camera_frame_service.simulation_enabled:
                stop_event.wait(0.05)
                continue

            stream: BinaryIO | None = None
            try:
                stream = self._stream_opener(host)
                with self._lock:
                    self._active_stream = stream
                    self._device_reachable = True
                    self._last_http_status = 200
                    self._last_error = None

                outcome = self._consume_mjpeg_stream(
                    stream=stream,
                    source_id=source_id,
                    stop_event=stop_event,
                )
                if outcome in {"stopped", "paused_for_simulation"}:
                    continue
                self._record_failure("ESP MJPEG stream ended unexpectedly.")
            except AppError as exc:
                self._record_failure(exc.message, exc.details.get("http_status") if exc.details else None)
            except (OSError, TimeoutError, ValueError) as exc:
                if not stop_event.is_set():
                    self._record_failure(f"ESP MJPEG transport error: {exc}")
            finally:
                if stream is not None:
                    try:
                        stream.close()
                    except Exception:
                        pass
                with self._lock:
                    if self._active_stream is stream:
                        self._active_stream = None

            if not stop_event.is_set() and not camera_frame_service.simulation_enabled:
                with self._lock:
                    self._stream_reconnects += 1
                stop_event.wait(STREAM_RETRY_SECONDS)

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
            worker_running = bool(thread and thread.is_alive())
            device_status = dict(self._device_status)
            settings = dict(self._settings) if isinstance(self._settings, dict) else None
            target_fps = self._target_fps

            return {
                "configured": host is not None,
                "device_reachable": self._device_reachable,
                "worker_running": worker_running,
                "streaming": bool(stream_requested and worker_running),
                "paused_for_simulation": bool(
                    stream_requested and worker_running and camera_frame_service.simulation_enabled
                ),
                "transport": "mjpeg" if stream_requested else "idle",
                "host": host,
                "source_id": self._source_id if host else None,
                "status_url": self._status_url(host) if host else None,
                "capture_url": self._capture_url(host) if host else None,
                "stream_url": self._stream_url(host) if host else None,
                "target_fps": target_fps,
                # Compatibility/status aid for V033 clients.
                "fetch_interval_ms": round(1000 / max(1, target_fps)),
                "measured_fps": round(self._measured_fps, 2),
                "last_frame_interval_ms": (
                    round(self._last_frame_interval_ms, 1)
                    if self._last_frame_interval_ms is not None
                    else None
                ),
                "stream_reconnects": self._stream_reconnects,
                "stream_bytes_received": self._stream_bytes_received,
                "dropped_stale_frames": self._dropped_stale_frames,
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
                "control_sequence": ["connect", "config", "start", "mjpeg_stream", "stop"],
                "prototype_only": True,
            }


remote_camera_service = RemoteCameraService()
