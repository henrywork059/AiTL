from __future__ import annotations

import http.client
import json
import socket
import statistics
import struct
from threading import Event, Lock, Thread
import time
from typing import Any
from urllib.parse import urlencode
from uuid import uuid4

from app.core.error_codes import ErrorCode
from app.core.exceptions import AppError
from app.core.logging_config import get_logger
from app.services.camera_frames import MAX_FRAME_BYTES, camera_frame_service
from app.services.remote_camera import (
    CAMERA_PROTOCOL,
    CAMERA_SETTING_KEYS,
    COMPATIBLE_CAMERA_PROTOCOLS,
    FRAME_PROTOCOL,
    TCP_STREAM_PORT,
    normalize_private_lan_ipv4,
)
from app.services.remote_camera_manager import remote_camera_manager

logger = get_logger(__name__)

CONTROL_PORT = 80
CONTROL_PROBE_ATTEMPTS = 8
CONTROL_TIMEOUT_SECONDS = 2.5
CONTROL_ACTION_ATTEMPTS = 3
CONTROL_ACTION_BACKOFF_SECONDS = 0.15
DIRECT_TARGET_FPS = 5
DIRECT_PHASE_SECONDS = 8.0
MANAGED_PHASE_SECONDS = 8.0
STREAM_CONNECT_TIMEOUT_SECONDS = 2.0
STREAM_READ_TIMEOUT_SECONDS = 2.0
STATUS_POLL_INTERVAL_SECONDS = 1.0
FRAME_HEADER = struct.Struct("!4sIII")
FRAME_MAGIC = b"ATL1"

DiagnosticCheck = dict[str, Any]


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    rank = (len(ordered) - 1) * percentile
    lower = int(rank)
    upper = min(len(ordered) - 1, lower + 1)
    fraction = rank - lower
    return float(ordered[lower] + (ordered[upper] - ordered[lower]) * fraction)


def _round_or_none(value: float | None, digits: int = 1) -> float | None:
    return None if value is None else round(value, digits)


def classify_camera_diagnostic(
    *,
    control_successes: int,
    protocol_ok: bool,
    camera_ready: bool,
    clean_frames: int,
    clean_disconnects: int,
    clean_bad_frames: int,
    polled_frames: int,
    polled_disconnects: int,
    polled_bad_frames: int,
    status_poll_failures: int,
    managed_frames: int,
    managed_failed_fetches: int,
    send_failures_delta: int,
    deadline_drops_delta: int,
    rssi_min: int | None,
) -> dict[str, Any]:
    """Turn measured evidence into one concise likely-cause diagnosis.

    This classifier is deliberately evidence-based: it distinguishes a direct
    ESP camera/TCP failure from HTTP-control contention and from a failure that
    appears only in PC Studio's normal stream worker.
    """

    clean_good = clean_frames >= 12 and clean_disconnects == 0 and clean_bad_frames == 0
    polled_good = polled_frames >= 12 and polled_disconnects == 0 and polled_bad_frames == 0
    managed_good = managed_frames >= 8 and managed_failed_fetches == 0
    weak_rssi = rssi_min is not None and rssi_min <= -75

    if control_successes == 0:
        return {
            "overall": "failed",
            "diagnosis_code": "control_unreachable",
            "title": "ESP control endpoint is unreachable",
            "summary": "PC Studio could not obtain a valid /status response from the selected ESP camera.",
            "confidence": "high",
            "likely_causes": [
                "Wrong or changed ESP IPv4 address",
                "ESP HTTP control server is not responding",
                "PC and ESP are not mutually reachable on the local network",
            ],
            "recommendations": [
                "Confirm the IP shown in the ESP Serial Monitor matches Camera Sources.",
                "Open the ESP /status address from the same PC and check local-network isolation/firewall settings.",
            ],
        }

    if not protocol_ok:
        return {
            "overall": "failed",
            "diagnosis_code": "firmware_incompatible",
            "title": "Camera firmware protocol is incompatible",
            "summary": "The ESP responded, but its camera or stream protocol does not match the binary TCP camera path accepted by PC Studio.",
            "confidence": "high",
            "likely_causes": ["Older or mismatched ESP32-CAM firmware"],
            "recommendations": ["Flash the current compatible AiTL ESP32-CAM firmware and run the diagnosis again."],
        }

    if not camera_ready:
        return {
            "overall": "failed",
            "diagnosis_code": "camera_not_ready",
            "title": "ESP camera sensor is not ready",
            "summary": "Network control is reachable, but the firmware reports that the camera sensor failed initialization or is unavailable.",
            "confidence": "high",
            "likely_causes": ["Camera ribbon/camera module problem", "OV2640 initialization failure"],
            "recommendations": ["Power-cycle the ESP, reseat the camera ribbon, and check the Serial Monitor for camera-init errors."],
        }

    if not clean_good and (send_failures_delta > 0 or deadline_drops_delta > 0):
        return {
            "overall": "failed",
            "diagnosis_code": "esp_camera_tcp_send_stall",
            "title": "ESP camera-to-TCP sender is stalling",
            "summary": "The direct receiver bypassed the normal PC Studio stream worker, but camera frames still stalled or disconnected and the ESP recorded send/deadline failures.",
            "confidence": "high",
            "likely_causes": [
                "ESP camera capture/DMA and lwIP transmit interaction",
                "TCP acknowledgements/backpressure are not progressing while the camera stream is active",
                "ESP sender deadline/transport behavior rather than the frontend preview",
            ],
            "recommendations": [
                "Treat the ESP camera/TCP send path as the primary failure area; changing the frontend will not solve this evidence pattern.",
                "Compare the accepted-byte and errno telemetry with the JPEG frame size before changing transport behavior.",
            ],
        }

    if not clean_good:
        return {
            "overall": "failed",
            "diagnosis_code": "direct_camera_stream_failure",
            "title": "Direct camera stream is unstable",
            "summary": "The selected ESP could not maintain the direct ATL1/JPEG stream even with PC Studio's normal stream worker bypassed.",
            "confidence": "high",
            "likely_causes": ["ESP stream sender", "Wi-Fi/TCP path", "Camera/network scheduling interaction"],
            "recommendations": ["Use the direct-stream metrics and ESP send telemetry to isolate sender versus RF/backpressure behavior."],
        }

    if clean_good and not polled_good and (status_poll_failures > 0 or polled_disconnects > clean_disconnects):
        return {
            "overall": "failed",
            "diagnosis_code": "control_stream_contention",
            "title": "HTTP control traffic disrupts camera streaming",
            "summary": "The camera stream is stable without control polling but becomes unstable when /status requests run concurrently.",
            "confidence": "high",
            "likely_causes": ["ESP single-threaded WebServer/control handling contends with the camera TCP send loop"],
            "recommendations": [
                "Reduce or defer ESP /status polling while streaming.",
                "Keep camera image transport and control-plane work from blocking each other on the ESP loop.",
            ],
        }

    if clean_good and polled_good and not managed_good:
        return {
            "overall": "failed",
            "diagnosis_code": "pc_studio_stream_integration",
            "title": "Direct stream works, but PC Studio's managed stream path fails",
            "summary": "The ESP delivered frames successfully to the diagnostic receiver, including with status polling, but the normal PC Studio worker did not receive them reliably.",
            "confidence": "high",
            "likely_causes": ["PC Studio stream worker/reconnect/session integration", "Backend receive-path state handling"],
            "recommendations": ["Focus the next repair on RemoteCameraService/RemoteCameraManager rather than ESP JPEG quality or camera hardware."],
        }

    if clean_good and polled_good and managed_good and (control_successes < CONTROL_PROBE_ATTEMPTS or status_poll_failures > 0):
        return {
            "overall": "warning",
            "diagnosis_code": "control_plane_instability",
            "title": "Image transport works, but ESP control requests are intermittent",
            "summary": "Direct and managed image streaming passed, but one or more /status control requests timed out or failed during the same run.",
            "confidence": "medium",
            "likely_causes": ["Intermittent ESP HTTP control responsiveness", "Wi-Fi/control-plane latency spikes"],
            "recommendations": ["Keep the stream transport unchanged and focus any follow-up repair on low-rate ESP control/status reliability."],
        }

    if weak_rssi:
        return {
            "overall": "warning",
            "diagnosis_code": "wifi_margin_low",
            "title": "Camera works, but Wi-Fi margin is weak",
            "summary": "The diagnostic stream completed, but the measured ESP RSSI entered a weak range that can make future control or TCP stalls more likely.",
            "confidence": "medium",
            "likely_causes": ["Weak or variable 2.4 GHz AP/BSSID association"],
            "recommendations": ["Improve ESP antenna/AP placement or verify that the ESP is associated with the intended nearby BSSID."],
        }

    return {
        "overall": "healthy",
        "diagnosis_code": "healthy_now",
        "title": "Camera path is healthy in this diagnostic run",
        "summary": "Control, direct camera transport, concurrent status polling, and the normal PC Studio managed stream all passed the built-in checks.",
        "confidence": "medium",
        "likely_causes": [],
        "recommendations": ["If the original failure is intermittent, run Diagnose again while the problem is visible and compare the saved metrics."],
    }


class CameraDiagnosticService:
    """One-click, state-restoring diagnostics for the selected ESP camera."""

    def __init__(self) -> None:
        self._run_lock = Lock()

    @staticmethod
    def _http_json(
        host: str,
        path: str,
        method: str = "GET",
        query: dict[str, str] | None = None,
    ) -> tuple[dict[str, Any], float]:
        target = path
        if query:
            target += "?" + urlencode(query)

        started = time.perf_counter()
        connection = http.client.HTTPConnection(host, CONTROL_PORT, timeout=CONTROL_TIMEOUT_SECONDS)
        try:
            connection.request(
                method,
                target,
                body=b"" if method != "GET" else None,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "AiTL-PC-Studio-Camera-Diagnostics",
                    "Connection": "close",
                },
            )
            response = connection.getresponse()
            payload = response.read(32 * 1024 + 1)
            status = int(response.status)
        finally:
            connection.close()

        elapsed_ms = (time.perf_counter() - started) * 1000.0
        if status < 200 or status >= 300:
            raise OSError(f"HTTP {status} from ESP {path}")
        if len(payload) > 32 * 1024:
            raise ValueError("ESP diagnostic control response exceeded 32 KiB")
        parsed = json.loads(payload.decode("utf-8"))
        if not isinstance(parsed, dict):
            raise ValueError("ESP diagnostic control response was not a JSON object")
        return parsed, elapsed_ms

    def _control_action(
        self,
        host: str,
        path: str,
        method: str = "POST",
        query: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(1, CONTROL_ACTION_ATTEMPTS + 1):
            try:
                response, _ = self._http_json(host, path, method, query)
                return response
            except (OSError, TimeoutError, http.client.HTTPException, json.JSONDecodeError, ValueError) as exc:
                last_error = exc
                if attempt < CONTROL_ACTION_ATTEMPTS:
                    time.sleep(CONTROL_ACTION_BACKOFF_SECONDS * attempt)
        assert last_error is not None
        raise last_error

    @staticmethod
    def _settings_query(settings: dict[str, Any], fps: int) -> dict[str, str]:
        query: dict[str, str] = {}
        for key in CAMERA_SETTING_KEYS:
            if key not in settings:
                raise ValueError(f"Saved camera setting is missing: {key}")
            value = settings[key]
            query[key] = "1" if value is True else "0" if value is False else str(value)
        query["stream_fps"] = str(fps)
        return query

    @staticmethod
    def _recv_exact(sock: socket.socket, size: int) -> bytes:
        buffer = bytearray(size)
        view = memoryview(buffer)
        offset = 0
        while offset < size:
            received = sock.recv_into(view[offset:])
            if received == 0:
                raise EOFError("ESP closed the TCP stream")
            offset += received
        return bytes(buffer)

    @staticmethod
    def _open_stream(host: str) -> socket.socket:
        sock = socket.create_connection((host, TCP_STREAM_PORT), timeout=STREAM_CONNECT_TIMEOUT_SECONDS)
        sock.settimeout(STREAM_READ_TIMEOUT_SECONDS)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 256 * 1024)
        except OSError:
            pass
        return sock

    def _run_stream_phase(self, host: str, *, seconds: float, poll_status: bool, expected_fps: int) -> dict[str, Any]:
        poll_stop = Event()
        poll_latencies: list[float] = []
        poll_failures: list[str] = []

        def poll_worker() -> None:
            while not poll_stop.wait(STATUS_POLL_INTERVAL_SECONDS):
                try:
                    _, elapsed = self._http_json(host, "/status")
                    poll_latencies.append(elapsed)
                except Exception as exc:
                    poll_failures.append(f"{type(exc).__name__}: {exc}")

        poll_thread: Thread | None = None
        if poll_status:
            poll_thread = Thread(target=poll_worker, name="aitl-camera-diagnostic-poll", daemon=True)
            poll_thread.start()

        phase_started = time.monotonic()
        deadline = phase_started + seconds
        sock: socket.socket | None = None
        connections = 0
        connect_latencies: list[float] = []
        disconnects = 0
        frames = 0
        bytes_received = 0
        sequence_gaps = 0
        bad_frames = 0
        last_sequence: int | None = None
        payload_sizes: list[int] = []
        arrivals: list[float] = []
        errors: list[str] = []
        first_frame_ms: float | None = None

        def close_socket() -> None:
            nonlocal sock
            if sock is None:
                return
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                sock.close()
            except OSError:
                pass
            sock = None

        try:
            while time.monotonic() < deadline:
                if sock is None:
                    try:
                        connect_started = time.perf_counter()
                        sock = self._open_stream(host)
                        connect_latencies.append((time.perf_counter() - connect_started) * 1000.0)
                        connections += 1
                    except Exception as exc:
                        errors.append(f"connect {type(exc).__name__}: {exc}")
                        time.sleep(0.10)
                        continue

                try:
                    header = self._recv_exact(sock, FRAME_HEADER.size)
                    magic, payload_length, sequence, _source_uptime_ms = FRAME_HEADER.unpack(header)
                    if magic != FRAME_MAGIC:
                        raise ValueError("ATL1 magic mismatch")
                    if payload_length <= 0 or payload_length > MAX_FRAME_BYTES:
                        raise ValueError(f"invalid payload length {payload_length}")
                    content = self._recv_exact(sock, payload_length)
                    if not content.startswith(b"\xff\xd8") or not content.endswith(b"\xff\xd9"):
                        bad_frames += 1
                    if last_sequence is not None:
                        delta = (sequence - last_sequence) & 0xFFFFFFFF
                        if 1 < delta < 0x80000000:
                            sequence_gaps += delta - 1
                    last_sequence = sequence
                    now = time.monotonic()
                    if first_frame_ms is None:
                        first_frame_ms = (now - phase_started) * 1000.0
                    frames += 1
                    bytes_received += FRAME_HEADER.size + payload_length
                    payload_sizes.append(payload_length)
                    arrivals.append(now)
                except (socket.timeout, TimeoutError, EOFError, OSError, ValueError) as exc:
                    disconnects += 1
                    errors.append(f"{type(exc).__name__}: {exc}")
                    close_socket()
                    time.sleep(0.10)
        finally:
            poll_stop.set()
            if poll_thread is not None:
                poll_thread.join(timeout=1.0)
            # End a normal measurement phase from the control plane before
            # closing the receiver socket. This avoids manufacturing an ESP
            # ECONNRESET/send-failure at every diagnostic phase boundary.
            try:
                self._control_action(host, "/stop")
                time.sleep(0.05)
            except Exception as exc:
                errors.append(f"phase-stop {type(exc).__name__}: {exc}")
            close_socket()

        runtime_seconds = max(0.001, time.monotonic() - phase_started)
        intervals_ms = [(b - a) * 1000.0 for a, b in zip(arrivals, arrivals[1:])]
        if len(arrivals) >= 2:
            elapsed = max(0.001, arrivals[-1] - arrivals[0])
            measured_fps = (len(arrivals) - 1) / elapsed
        else:
            measured_fps = 0.0
        throughput_mbps = (bytes_received * 8.0) / runtime_seconds / 1_000_000.0
        fps_ratio = measured_fps / max(1, expected_fps)

        return {
            "frames": frames,
            "bytes_received": bytes_received,
            "runtime_seconds": round(runtime_seconds, 2),
            "expected_fps": expected_fps,
            "measured_fps": round(measured_fps, 2),
            "fps_ratio": round(fps_ratio, 3),
            "throughput_mbps": round(throughput_mbps, 3),
            "connections": connections,
            "connect_avg_ms": _round_or_none(statistics.mean(connect_latencies) if connect_latencies else None),
            "connect_p95_ms": _round_or_none(_percentile(connect_latencies, 0.95)),
            "first_frame_ms": _round_or_none(first_frame_ms),
            "disconnects": disconnects,
            "sequence_gaps": sequence_gaps,
            "bad_frames": bad_frames,
            "payload_avg_bytes": round(statistics.mean(payload_sizes)) if payload_sizes else 0,
            "payload_min_bytes": min(payload_sizes) if payload_sizes else 0,
            "payload_max_bytes": max(payload_sizes) if payload_sizes else 0,
            "frame_interval_avg_ms": _round_or_none(statistics.mean(intervals_ms) if intervals_ms else None),
            "frame_interval_p95_ms": _round_or_none(_percentile(intervals_ms, 0.95)),
            "frame_interval_max_ms": _round_or_none(max(intervals_ms) if intervals_ms else None),
            "frame_interval_std_ms": _round_or_none(statistics.pstdev(intervals_ms) if len(intervals_ms) >= 2 else None),
            "errors": errors[:8],
            "status_poll_successes": len(poll_latencies),
            "status_poll_failures": len(poll_failures),
            "status_poll_avg_ms": _round_or_none(statistics.mean(poll_latencies) if poll_latencies else None),
            "status_poll_p95_ms": _round_or_none(_percentile(poll_latencies, 0.95)),
            "status_poll_errors": poll_failures[:8],
        }

    def _run_reconnect_phase(self, host: str) -> dict[str, Any]:
        """Deliberately replace one receiver socket and verify a fresh client can resume."""
        first_frames = 0
        second_frames = 0
        errors: list[str] = []
        reconnect_ms: float | None = None

        def read_frames(sock: socket.socket, count: int) -> int:
            received = 0
            for _ in range(count):
                header = self._recv_exact(sock, FRAME_HEADER.size)
                magic, payload_length, _sequence, _uptime = FRAME_HEADER.unpack(header)
                if magic != FRAME_MAGIC or payload_length <= 0 or payload_length > MAX_FRAME_BYTES:
                    raise ValueError("invalid ATL1 reconnect-test frame")
                content = self._recv_exact(sock, payload_length)
                if not content.startswith(b"\xff\xd8") or not content.endswith(b"\xff\xd9"):
                    raise ValueError("invalid JPEG in reconnect test")
                received += 1
            return received

        first: socket.socket | None = None
        second: socket.socket | None = None
        try:
            first = self._open_stream(host)
            first_frames = read_frames(first, 4)
            try:
                first.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            first.close()
            first = None
            time.sleep(0.20)
            started = time.perf_counter()
            second = self._open_stream(host)
            second_frames = read_frames(second, 6)
            reconnect_ms = (time.perf_counter() - started) * 1000.0
        except Exception as exc:
            errors.append(f"{type(exc).__name__}: {exc}")
        finally:
            for candidate in (first, second):
                if candidate is not None:
                    try:
                        candidate.close()
                    except OSError:
                        pass
        return {
            "first_socket_frames": first_frames,
            "second_socket_frames": second_frames,
            "reconnect_success": first_frames >= 4 and second_frames >= 6,
            "reconnect_ms": _round_or_none(reconnect_ms),
            "intentional_socket_replacements": 1,
            "errors": errors,
        }

    @staticmethod
    def _profile_from_status(manager_status: dict[str, Any]) -> dict[str, Any]:
        source_id = manager_status.get("active_source_id")
        if not source_id:
            raise AppError(
                ErrorCode.CAMERA_NOT_CONNECTED,
                "Save and select an ESP camera in Camera Sources before running diagnostics.",
                status_code=409,
            )
        cameras = manager_status.get("cameras")
        if not isinstance(cameras, list):
            cameras = []
        profile = next((item for item in cameras if isinstance(item, dict) and item.get("source_id") == source_id), None)
        if profile is None:
            raise AppError(
                ErrorCode.CAMERA_NOT_CONNECTED,
                "The selected ESP camera profile could not be resolved for diagnostics.",
                status_code=409,
                details={"source_id": source_id},
            )
        return dict(profile)

    def _managed_phase(
        self,
        *,
        host: str,
        source_id: str,
        settings: dict[str, Any],
        target_fps: int,
    ) -> dict[str, Any]:
        error: str | None = None
        baseline = remote_camera_manager.status(refresh_device=False)
        baseline_frames = _safe_int(baseline.get("successful_fetches"))
        baseline_failed = _safe_int(baseline.get("failed_fetches"))
        baseline_reconnects = _safe_int(baseline.get("stream_reconnects"))
        baseline_recoveries = _safe_int(baseline.get("session_recoveries"))
        baseline_bytes = _safe_int(baseline.get("stream_bytes_received"))
        phase_started = time.monotonic()

        try:
            remote_camera_manager.connect(host=host, source_id=source_id)
            remote_camera_manager.start_stream(settings=settings, target_fps=target_fps)
        except AppError as exc:
            return {
                "frames": 0,
                "failed_fetches": 0,
                "reconnects": 0,
                "session_recoveries": 0,
                "bytes_received": 0,
                "stream_connected": False,
                "measured_fps": 0.0,
                "expected_fps": target_fps,
                "fps_ratio": 0.0,
                "error": exc.message,
            }

        last_status: dict[str, Any] = {}
        while time.monotonic() - phase_started < MANAGED_PHASE_SECONDS:
            last_status = remote_camera_manager.status(refresh_device=False)
            time.sleep(0.25)

        frames = max(0, _safe_int(last_status.get("successful_fetches")) - baseline_frames)
        failed = max(0, _safe_int(last_status.get("failed_fetches")) - baseline_failed)
        reconnects = max(0, _safe_int(last_status.get("stream_reconnects")) - baseline_reconnects)
        recoveries = max(0, _safe_int(last_status.get("session_recoveries")) - baseline_recoveries)
        bytes_received = max(0, _safe_int(last_status.get("stream_bytes_received")) - baseline_bytes)
        stream_connected = bool(last_status.get("stream_connected"))
        measured_fps = _safe_float(last_status.get("measured_fps"))
        if last_status.get("last_error"):
            error = str(last_status.get("last_error"))

        try:
            remote_camera_manager.stop_stream(best_effort=True)
        except Exception:
            pass

        return {
            "frames": frames,
            "failed_fetches": failed,
            "reconnects": reconnects,
            "session_recoveries": recoveries,
            "bytes_received": bytes_received,
            "stream_connected": stream_connected,
            "measured_fps": round(measured_fps, 2),
            "expected_fps": target_fps,
            "fps_ratio": round(measured_fps / max(1, target_fps), 3),
            "error": error,
        }

    def _restore_state(
        self,
        *,
        host: str,
        source_id: str,
        settings: dict[str, Any],
        target_fps: int,
        was_connected: bool,
        was_streaming: bool,
        simulation_was_enabled: bool,
    ) -> tuple[bool, str | None]:
        try:
            remote_camera_manager.save_profile(
                host=host,
                source_id=source_id,
                settings=settings,
                target_fps=target_fps,
                select=True,
            )

            if was_streaming:
                current = remote_camera_manager.status(refresh_device=False)
                if not current.get("configured"):
                    remote_camera_manager.connect(host=host, source_id=source_id)
                remote_camera_manager.start_stream(settings=settings, target_fps=target_fps)
            elif was_connected:
                current = remote_camera_manager.status(refresh_device=False)
                if not current.get("configured"):
                    remote_camera_manager.connect(host=host, source_id=source_id)
                else:
                    remote_camera_manager.stop_stream(best_effort=True)
            else:
                try:
                    remote_camera_manager.disconnect()
                except AppError:
                    pass

            if simulation_was_enabled:
                camera_frame_service.set_simulation(True)
                remote_camera_manager.sync_after_simulation_change()
            return True, None
        except Exception as exc:
            if simulation_was_enabled:
                try:
                    camera_frame_service.set_simulation(True)
                    remote_camera_manager.sync_after_simulation_change()
                except Exception:
                    pass
            return False, f"{type(exc).__name__}: {exc}"

    def run(self) -> dict[str, Any]:
        if not self._run_lock.acquire(blocking=False):
            raise AppError(ErrorCode.INVALID_REQUEST, "A camera diagnostic run is already in progress.", status_code=409)

        run_id = f"camdiag-{uuid4().hex[:10]}"
        started_epoch_ms = int(time.time() * 1000)
        started_monotonic = time.monotonic()
        checks: list[DiagnosticCheck] = []
        restore_context: dict[str, Any] | None = None
        restore_attempted = False
        state_restored = False
        restore_error: str | None = None

        try:
            initial_status = remote_camera_manager.status(refresh_device=False)
            profile = self._profile_from_status(initial_status)
            source_id = str(profile["source_id"])
            host = normalize_private_lan_ipv4(str(profile["host"]))
            settings = dict(profile.get("settings") or {})
            target_fps = _safe_int(profile.get("target_fps"), 15)
            load_target_fps = max(DIRECT_TARGET_FPS, min(target_fps, 15))
            was_connected = bool(profile.get("connected"))
            was_streaming = bool(profile.get("streaming"))
            simulation_was_enabled = bool(camera_frame_service.simulation_enabled)
            restore_context = {
                "host": host, "source_id": source_id, "settings": settings, "target_fps": target_fps,
                "was_connected": was_connected, "was_streaming": was_streaming,
                "simulation_was_enabled": simulation_was_enabled,
            }

            if simulation_was_enabled:
                camera_frame_service.set_simulation(False)
                remote_camera_manager.sync_after_simulation_change()
            if was_streaming:
                try:
                    remote_camera_manager.stop_stream(best_effort=True)
                except Exception:
                    pass

            # A. Repeated control probes for baseline latency/stability.
            control_latencies: list[float] = []
            control_errors: list[str] = []
            status_samples: list[dict[str, Any]] = []
            for _ in range(CONTROL_PROBE_ATTEMPTS):
                try:
                    status, elapsed = self._http_json(host, "/status")
                    status_samples.append(status)
                    control_latencies.append(elapsed)
                except Exception as exc:
                    control_errors.append(f"{type(exc).__name__}: {exc}")
                time.sleep(0.10)

            control_successes = len(status_samples)
            control_failures = len(control_errors)
            last_device_status = status_samples[-1] if status_samples else {}
            protocol_ok = bool(last_device_status) and (
                str(last_device_status.get("protocol") or "") in COMPATIBLE_CAMERA_PROTOCOLS
                and str(last_device_status.get("stream_protocol") or "") == FRAME_PROTOCOL
            )
            camera_ready = bool(last_device_status.get("camera_ready")) if last_device_status else False
            rssi_values = [_safe_int(item.get("rssi"), -127) for item in status_samples if item.get("rssi") is not None]
            rssi_values = [value for value in rssi_values if value > -127]
            rssi_min = min(rssi_values) if rssi_values else None
            rssi_max = max(rssi_values) if rssi_values else None
            rssi_avg = round(statistics.mean(rssi_values), 1) if rssi_values else None
            control_avg = statistics.mean(control_latencies) if control_latencies else None
            control_p95 = _percentile(control_latencies, 0.95)
            control_max = max(control_latencies) if control_latencies else None

            checks.append({"id":"control","label":"ESP HTTP control stability","status":"pass" if control_failures == 0 else "warn" if control_successes else "fail","detail":f"{control_successes}/{CONTROL_PROBE_ATTEMPTS} probes; p95 {_round_or_none(control_p95)} ms; max {_round_or_none(control_max)} ms","metrics":{"successes":control_successes,"failures":control_failures,"average_ms":_round_or_none(control_avg),"p95_ms":_round_or_none(control_p95),"max_ms":_round_or_none(control_max),"errors":control_errors[:5]}})
            checks.append({"id":"firmware","label":"Firmware / wire protocol","status":"pass" if protocol_ok else "fail","detail":f"{last_device_status.get('protocol')} + {last_device_status.get('stream_protocol')}" if last_device_status else "No device status available","metrics":{"camera_protocol":last_device_status.get("protocol"),"stream_protocol":last_device_status.get("stream_protocol"),"expected_camera_protocol":CAMERA_PROTOCOL,"expected_stream_protocol":FRAME_PROTOCOL}})
            checks.append({"id":"camera_sensor","label":"Camera sensor readiness","status":"pass" if camera_ready else "fail","detail":"ESP reports camera_ready=true" if camera_ready else "ESP did not report a ready camera sensor","metrics":{"camera_ready":camera_ready}})
            wifi_status = "warn" if rssi_min is None or rssi_min <= -75 else "pass"
            checks.append({"id":"wifi","label":"Wi-Fi signal stability","status":wifi_status,"detail":f"RSSI avg {rssi_avg} dBm, range {rssi_min}..{rssi_max} dBm" if rssi_avg is not None else "RSSI telemetry unavailable","metrics":{"rssi_avg":rssi_avg,"rssi_min":rssi_min,"rssi_max":rssi_max,"rssi_span":(rssi_max-rssi_min) if rssi_min is not None and rssi_max is not None else None,"bssid":last_device_status.get("wifi_bssid"),"channel":last_device_status.get("wifi_channel")}})

            empty_stream = {"frames":0,"disconnects":0,"bad_frames":0,"sequence_gaps":0,"measured_fps":0.0,"fps_ratio":0.0,"throughput_mbps":0.0}
            clean_phase = dict(empty_stream)
            polled_phase = dict(empty_stream)
            load_phase = dict(empty_stream)
            reconnect_phase = {"reconnect_success":False,"first_socket_frames":0,"second_socket_frames":0,"intentional_socket_replacements":0,"errors":[]}
            managed_phase = {"frames":0,"failed_fetches":0,"reconnects":0,"session_recoveries":0,"stream_connected":False,"measured_fps":0.0,"fps_ratio":0.0,"error":None}
            lifecycle_ok = False
            stop_ok = False
            after_status = dict(last_device_status)
            baseline_send_failures = _safe_int(last_device_status.get("stream_send_failures"))
            baseline_deadlines = _safe_int(last_device_status.get("stream_deadline_drops"))
            baseline_wifi_disc = _safe_int(last_device_status.get("wifi_disconnects"))
            baseline_wifi_rec = _safe_int(last_device_status.get("wifi_reconnects"))

            if control_successes > 0 and protocol_ok and camera_ready:
                # B. Lifecycle/config functionality.
                try:
                    try: self._control_action(host, "/stop")
                    except Exception: pass
                    configured = self._control_action(host, "/config", query=self._settings_query(settings, DIRECT_TARGET_FPS))
                    started = self._control_action(host, "/start")
                    lifecycle_ok = started.get("session_active") is True
                    checks.append({"id":"lifecycle","label":"Config / start lifecycle","status":"pass" if lifecycle_ok else "fail","detail":f"Saved image settings applied; diagnostic stream armed at {DIRECT_TARGET_FPS} FPS" if lifecycle_ok else "ESP did not confirm session_active=true","metrics":{"configured_frame_size":configured.get("configured_frame_size") or configured.get("settings",{}).get("frame_size"),"configured_quality":configured.get("configured_jpeg_quality") or configured.get("settings",{}).get("jpeg_quality"),"session_active":started.get("session_active")}})

                    # C. Clean direct receiver: isolates ESP camera + TCP + PC socket.
                    clean_phase = self._run_stream_phase(host, seconds=DIRECT_PHASE_SECONDS, poll_status=False, expected_fps=DIRECT_TARGET_FPS)
                    self._control_action(host, "/stop")
                    stop_status, _ = self._http_json(host, "/status")
                    stop_ok = stop_status.get("session_active") is False
                    clean_good = clean_phase.get("frames",0) >= 20 and clean_phase.get("disconnects",0)==0 and clean_phase.get("bad_frames",0)==0
                    checks.append({"id":"direct_stream","label":"Direct ATL1/JPEG functionality","status":"pass" if clean_good else "fail","detail":f"{clean_phase.get('frames',0)} frames; {clean_phase.get('measured_fps',0)} FPS; {clean_phase.get('throughput_mbps',0)} Mbps; {clean_phase.get('disconnects',0)} disconnects","metrics":clean_phase})

                    # D. Same load plus status polling: control/data contention.
                    self._control_action(host, "/config", query=self._settings_query(settings, DIRECT_TARGET_FPS)); self._control_action(host, "/start")
                    polled_phase = self._run_stream_phase(host, seconds=DIRECT_PHASE_SECONDS, poll_status=True, expected_fps=DIRECT_TARGET_FPS)
                    self._control_action(host, "/stop")
                    polled_good = polled_phase.get("frames",0) >= 20 and polled_phase.get("disconnects",0)==0 and polled_phase.get("bad_frames",0)==0 and polled_phase.get("status_poll_failures",0)==0
                    checks.append({"id":"control_during_stream","label":"Control + stream concurrency","status":"pass" if polled_good else "fail","detail":f"{polled_phase.get('frames',0)} frames; stream p95 {polled_phase.get('frame_interval_p95_ms')} ms; HTTP p95 {polled_phase.get('status_poll_p95_ms')} ms; {polled_phase.get('status_poll_failures',0)} poll failures","metrics":polled_phase})

                    # E. Requested-load headroom test, capped at 15 FPS for a bounded diagnostic.
                    self._control_action(host, "/config", query=self._settings_query(settings, load_target_fps)); self._control_action(host, "/start")
                    load_phase = self._run_stream_phase(host, seconds=DIRECT_PHASE_SECONDS, poll_status=False, expected_fps=load_target_fps)
                    self._control_action(host, "/stop")
                    load_ratio = _safe_float(load_phase.get("fps_ratio"))
                    load_status = "pass" if load_ratio >= 0.85 and load_phase.get("disconnects",0)==0 else "warn" if load_ratio >= 0.60 and load_phase.get("disconnects",0)==0 else "fail"
                    checks.append({"id":"throughput_headroom","label":"Throughput / FPS headroom","status":load_status,"detail":f"Target {load_target_fps} FPS; achieved {load_phase.get('measured_fps',0)} FPS ({load_ratio*100:.0f}%); {load_phase.get('throughput_mbps',0)} Mbps","metrics":load_phase})

                    # F. Deliberate receiver replacement tests reconnect functionality.
                    self._control_action(host, "/config", query=self._settings_query(settings, DIRECT_TARGET_FPS)); self._control_action(host, "/start")
                    reconnect_before, _ = self._http_json(host, "/status")
                    reconnect_phase = self._run_reconnect_phase(host)
                    time.sleep(0.25)
                    reconnect_after, _ = self._http_json(host, "/status")
                    self._control_action(host, "/stop")
                    expected_reset_delta = max(0, _safe_int(reconnect_after.get("stream_send_failures")) - _safe_int(reconnect_before.get("stream_send_failures")))
                    reconnect_phase["esp_send_failures_during_intentional_replacement"] = expected_reset_delta
                    checks.append({"id":"reconnect","label":"TCP reconnect functionality","status":"pass" if reconnect_phase.get("reconnect_success") else "fail","detail":f"Fresh receiver resumed with {reconnect_phase.get('second_socket_frames',0)} frames in {reconnect_phase.get('reconnect_ms')} ms; {expected_reset_delta} ESP reset(s) during intentional socket replacement","metrics":reconnect_phase})

                    # G. Normal PC Studio integration, using per-phase deltas.
                    managed_phase = self._managed_phase(host=host, source_id=source_id, settings=settings, target_fps=load_target_fps)
                    managed_good = managed_phase.get("frames",0) >= 12 and managed_phase.get("failed_fetches",0)==0
                    checks.append({"id":"pc_studio_managed","label":"Normal PC Studio worker functionality","status":"pass" if managed_good else "fail","detail":f"{managed_phase.get('frames',0)} new frames; {managed_phase.get('measured_fps',0)} FPS; {managed_phase.get('failed_fetches',0)} failures; {managed_phase.get('reconnects',0)} reconnects","metrics":managed_phase})
                except Exception as exc:
                    checks.append({"id":"lifecycle_error","label":"Diagnostic stream setup","status":"fail","detail":f"{type(exc).__name__}: {exc}","metrics":{}})
                    try: self._control_action(host, "/stop")
                    except Exception: pass

                try:
                    after_status, _ = self._http_json(host, "/status")
                except Exception:
                    pass
            else:
                for cid,label in (("lifecycle","Config / start lifecycle"),("direct_stream","Direct ATL1/JPEG functionality"),("control_during_stream","Control + stream concurrency"),("throughput_headroom","Throughput / FPS headroom"),("reconnect","TCP reconnect functionality"),("pc_studio_managed","Normal PC Studio worker functionality")):
                    checks.append({"id":cid,"label":label,"status":"skip","detail":"Skipped because control/protocol/camera readiness did not pass.","metrics":{}})

            total_send_failures = max(0, _safe_int(after_status.get("stream_send_failures")) - baseline_send_failures)
            total_deadlines = max(0, _safe_int(after_status.get("stream_deadline_drops")) - baseline_deadlines)
            intentional_resets = _safe_int(reconnect_phase.get("esp_send_failures_during_intentional_replacement"))
            unexpected_send_failures = max(0, total_send_failures - intentional_resets)
            wifi_disc_delta = max(0, _safe_int(after_status.get("wifi_disconnects")) - baseline_wifi_disc)
            wifi_rec_delta = max(0, _safe_int(after_status.get("wifi_reconnects")) - baseline_wifi_rec)

            diagnosis = classify_camera_diagnostic(
                control_successes=control_successes, protocol_ok=protocol_ok, camera_ready=camera_ready,
                clean_frames=_safe_int(clean_phase.get("frames")), clean_disconnects=_safe_int(clean_phase.get("disconnects")), clean_bad_frames=_safe_int(clean_phase.get("bad_frames")),
                polled_frames=_safe_int(polled_phase.get("frames")), polled_disconnects=_safe_int(polled_phase.get("disconnects")), polled_bad_frames=_safe_int(polled_phase.get("bad_frames")), status_poll_failures=_safe_int(polled_phase.get("status_poll_failures")),
                managed_frames=_safe_int(managed_phase.get("frames")), managed_failed_fetches=_safe_int(managed_phase.get("failed_fetches")),
                send_failures_delta=unexpected_send_failures, deadline_drops_delta=total_deadlines, rssi_min=rssi_min,
            )

            # Bottleneck analysis and stability scoring.
            bottlenecks: list[dict[str, Any]] = []
            def add_bottleneck(layer: str, severity: str, evidence: str, action: str) -> None:
                bottlenecks.append({"layer":layer,"severity":severity,"evidence":evidence,"action":action})
            if control_failures or (control_p95 is not None and control_p95 > 600):
                add_bottleneck("HTTP control", "high" if control_failures else "medium", f"{control_failures} failures; p95 {_round_or_none(control_p95)} ms", "Investigate ESP HTTP responsiveness/control scheduling before changing JPEG transport.")
            if rssi_min is not None and rssi_min <= -75:
                add_bottleneck("Wi-Fi RF", "high" if rssi_min <= -82 else "medium", f"RSSI reached {rssi_min} dBm", "Improve AP/antenna placement or association with the intended nearby BSSID.")
            if _safe_float(load_phase.get("fps_ratio")) < 0.75 and _safe_int(load_phase.get("disconnects")) == 0:
                add_bottleneck("Throughput capacity", "medium", f"Only {_safe_float(load_phase.get('fps_ratio'))*100:.0f}% of {load_target_fps} FPS sustained", "Use achieved FPS as the real capacity at the current resolution/quality; do not reduce image quality unless required by the application.")
            budget_ms = 1000.0 / max(1, load_target_fps)
            load_p95 = _safe_float(load_phase.get("frame_interval_p95_ms"))
            if load_p95 > budget_ms * 2.0:
                add_bottleneck("Latency / jitter", "medium", f"Frame-interval p95 {load_p95:.0f} ms vs {budget_ms:.0f} ms target period", "Treat variable send/ACK scheduling as a stability limit even if average FPS appears acceptable.")
            if polled_phase.get("status_poll_failures",0) or (_safe_float(polled_phase.get("fps_ratio")) + 0.15 < _safe_float(clean_phase.get("fps_ratio"))):
                add_bottleneck("Control/data contention", "high" if polled_phase.get("status_poll_failures",0) else "medium", f"Clean ratio {_safe_float(clean_phase.get('fps_ratio')):.2f}; with polling {_safe_float(polled_phase.get('fps_ratio')):.2f}; poll failures {polled_phase.get('status_poll_failures',0)}", "Reduce status/control work while the ESP is transmitting frames.")
            if clean_phase.get("disconnects",0) or unexpected_send_failures or total_deadlines:
                add_bottleneck("ESP/TCP sender", "high", f"Direct disconnects {clean_phase.get('disconnects',0)}; unexpected ESP send failures {unexpected_send_failures}; deadlines {total_deadlines}", "Focus on ESP sender/lwIP scheduling rather than browser rendering.")
            if clean_phase.get("frames",0) >= 20 and polled_phase.get("frames",0) >= 20 and (managed_phase.get("failed_fetches",0) or managed_phase.get("frames",0) < 12):
                add_bottleneck("PC Studio receive path", "high", f"Direct phases passed but managed worker got {managed_phase.get('frames',0)} frames / {managed_phase.get('failed_fetches',0)} failures", "Inspect RemoteCameraService/Manager receive and reconnect state.")

            score = 100
            score -= min(30, control_failures * 10)
            score -= min(30, (_safe_int(clean_phase.get("disconnects")) + _safe_int(polled_phase.get("disconnects"))) * 15)
            score -= min(20, (_safe_int(clean_phase.get("bad_frames")) + _safe_int(polled_phase.get("bad_frames"))) * 10)
            score -= min(20, _safe_int(polled_phase.get("status_poll_failures")) * 5)
            score -= min(20, _safe_int(managed_phase.get("failed_fetches")) * 5)
            score -= min(15, unexpected_send_failures * 5 + total_deadlines * 5)
            score -= min(10, wifi_disc_delta * 5)
            load_ratio = min(1.0, max(0.0, _safe_float(load_phase.get("fps_ratio"))))
            if load_phase.get("frames",0): score -= round((1.0 - load_ratio) * 20)
            if load_p95 > budget_ms * 2.0: score -= 8
            score = max(0, min(100, int(score)))
            grade = "excellent" if score >= 90 else "good" if score >= 75 else "marginal" if score >= 55 else "unstable"
            stability = {"score":score,"grade":grade,"target_fps":load_target_fps,"sustained_fps":_safe_float(load_phase.get("measured_fps")),"fps_headroom_ratio":_safe_float(load_phase.get("fps_ratio")),"frame_interval_p95_ms":load_phase.get("frame_interval_p95_ms"),"frame_interval_max_ms":load_phase.get("frame_interval_max_ms"),"unexpected_send_failures":unexpected_send_failures,"deadline_drops":total_deadlines,"wifi_disconnects_delta":wifi_disc_delta,"wifi_reconnects_delta":wifi_rec_delta}
            functionality = {"control":control_successes>0,"protocol":protocol_ok,"camera_sensor":camera_ready,"config_start":lifecycle_ok,"stop":stop_ok,"jpeg_stream":clean_phase.get("frames",0)>=20 and clean_phase.get("bad_frames",0)==0,"concurrent_control":polled_phase.get("frames",0)>=20 and polled_phase.get("status_poll_failures",0)==0,"reconnect":bool(reconnect_phase.get("reconnect_success")),"pc_studio_worker":managed_phase.get("frames",0)>=12 and managed_phase.get("failed_fetches",0)==0}

            if diagnosis["diagnosis_code"] == "healthy_now" and bottlenecks:
                diagnosis = {**diagnosis, "overall":"warning", "diagnosis_code":"healthy_with_bottleneck", "title":"Camera functions, but a performance bottleneck was measured", "summary":"All essential camera functions completed, but the detailed run found one or more capacity, latency, or control-path bottlenecks.", "confidence":"high", "likely_causes":[item["layer"] for item in bottlenecks], "recommendations":[item["action"] for item in bottlenecks]}
            elif diagnosis["diagnosis_code"] == "healthy_now" and score >= 90:
                diagnosis = {**diagnosis, "confidence":"high", "summary":"Control, camera lifecycle, direct JPEG transport, concurrent control, reconnect, requested-load test, and the normal PC Studio worker all passed with no material bottleneck detected."}

            restore_attempted = True
            state_restored, restore_error = self._restore_state(**restore_context)
            checks.append({"id":"state_restore","label":"Restore previous camera state","status":"pass" if state_restored else "warn","detail":"Previous camera/simulation state restored." if state_restored else f"Automatic restore needs attention: {restore_error}","metrics":{"restored":state_restored,"error":restore_error}})

            metrics = {
                "control_successes":control_successes,"control_failures":control_failures,"control_avg_ms":_round_or_none(control_avg),"control_p95_ms":_round_or_none(control_p95),"control_max_ms":_round_or_none(control_max),
                "rssi_avg":rssi_avg,"rssi_min":rssi_min,"rssi_max":rssi_max,"wifi_bssid":after_status.get("wifi_bssid") or last_device_status.get("wifi_bssid"),"wifi_channel":after_status.get("wifi_channel") or last_device_status.get("wifi_channel"),
                "direct_clean_frames":_safe_int(clean_phase.get("frames")),"direct_clean_fps":_safe_float(clean_phase.get("measured_fps")),"direct_clean_disconnects":_safe_int(clean_phase.get("disconnects")),"direct_clean_bad_frames":_safe_int(clean_phase.get("bad_frames")),"direct_clean_sequence_gaps":_safe_int(clean_phase.get("sequence_gaps")),"direct_clean_p95_interval_ms":clean_phase.get("frame_interval_p95_ms"),
                "direct_polled_frames":_safe_int(polled_phase.get("frames")),"direct_polled_fps":_safe_float(polled_phase.get("measured_fps")),"direct_polled_disconnects":_safe_int(polled_phase.get("disconnects")),"direct_polled_bad_frames":_safe_int(polled_phase.get("bad_frames")),"status_poll_failures":_safe_int(polled_phase.get("status_poll_failures")),"status_poll_p95_ms":polled_phase.get("status_poll_p95_ms"),
                "load_target_fps":load_target_fps,"load_frames":_safe_int(load_phase.get("frames")),"load_fps":_safe_float(load_phase.get("measured_fps")),"load_fps_ratio":_safe_float(load_phase.get("fps_ratio")),"load_throughput_mbps":_safe_float(load_phase.get("throughput_mbps")),"load_frame_interval_p95_ms":load_phase.get("frame_interval_p95_ms"),"load_frame_interval_max_ms":load_phase.get("frame_interval_max_ms"),"load_payload_avg_bytes":_safe_int(load_phase.get("payload_avg_bytes")),
                "reconnect_success":bool(reconnect_phase.get("reconnect_success")),"reconnect_ms":reconnect_phase.get("reconnect_ms"),"diagnostic_transition_resets":intentional_resets,
                "managed_frames":_safe_int(managed_phase.get("frames")),"managed_failed_fetches":_safe_int(managed_phase.get("failed_fetches")),"managed_reconnects":_safe_int(managed_phase.get("reconnects")),"managed_session_recoveries":_safe_int(managed_phase.get("session_recoveries")),"managed_fps":_safe_float(managed_phase.get("measured_fps")),"managed_fps_ratio":_safe_float(managed_phase.get("fps_ratio")),
                "device_send_failures_delta":total_send_failures,"device_unexpected_send_failures_delta":unexpected_send_failures,"device_deadline_drops_delta":total_deadlines,"last_send_errno":after_status.get("last_send_errno"),"last_send_accepted_bytes":after_status.get("last_send_accepted_bytes"),"last_frame_bytes":after_status.get("last_frame_bytes"),"send_ewma_ms":after_status.get("send_ewma_ms"),"wifi_disconnects":after_status.get("wifi_disconnects"),"wifi_reconnects":after_status.get("wifi_reconnects"),
            }

            duration_ms = int(round((time.monotonic()-started_monotonic)*1000))
            report = {"run_id":run_id,"started_at_ms":started_epoch_ms,"duration_ms":duration_ms,"source_id":source_id,"host":host,**diagnosis,"checks":checks,"metrics":metrics,"functionality":functionality,"stability":stability,"bottlenecks":bottlenecks,"device":{"protocol":after_status.get("protocol") or last_device_status.get("protocol"),"stream_protocol":after_status.get("stream_protocol") or last_device_status.get("stream_protocol"),"firmware_revision":after_status.get("firmware_revision") or last_device_status.get("firmware_revision"),"camera_ready":after_status.get("camera_ready",camera_ready),"rssi":after_status.get("rssi"),"wifi_bssid":after_status.get("wifi_bssid"),"wifi_channel":after_status.get("wifi_channel")},"state_restored":state_restored,"restore_error":restore_error,"diagnostic_target_fps":DIRECT_TARGET_FPS,"diagnostic_load_fps":load_target_fps,"prototype_only":True}
            logger.info("Detailed camera diagnostic run completed", extra={"run_id":run_id,"source_id":source_id,"host":host,"diagnosis_code":report["diagnosis_code"],"overall":report["overall"],"stability_score":score,"bottleneck_count":len(bottlenecks),"duration_ms":duration_ms})
            return report
        finally:
            if restore_context is not None and not restore_attempted:
                try: self._restore_state(**restore_context)
                except Exception: logger.exception("Camera diagnostic emergency state restore failed")
            self._run_lock.release()


camera_diagnostic_service = CameraDiagnosticService()
