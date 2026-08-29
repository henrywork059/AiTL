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
CONTROL_PROBE_ATTEMPTS = 3
CONTROL_TIMEOUT_SECONDS = 2.5
CONTROL_ACTION_ATTEMPTS = 3
CONTROL_ACTION_BACKOFF_SECONDS = 0.15
DIRECT_TARGET_FPS = 5
DIRECT_PHASE_SECONDS = 6.0
MANAGED_PHASE_SECONDS = 6.0
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

    def _run_stream_phase(self, host: str, *, seconds: float, poll_status: bool) -> dict[str, Any]:
        poll_stop = Event()
        poll_latencies: list[float] = []
        poll_failures: list[str] = []

        def poll_worker() -> None:
            while not poll_stop.wait(STATUS_POLL_INTERVAL_SECONDS):
                try:
                    _, elapsed = self._http_json(host, "/status")
                    poll_latencies.append(elapsed)
                except Exception as exc:  # diagnostics intentionally records every transport exception
                    poll_failures.append(f"{type(exc).__name__}: {exc}")

        poll_thread: Thread | None = None
        if poll_status:
            poll_thread = Thread(target=poll_worker, name="aitl-camera-diagnostic-poll", daemon=True)
            poll_thread.start()

        deadline = time.monotonic() + seconds
        sock: socket.socket | None = None
        connections = 0
        disconnects = 0
        frames = 0
        bytes_received = 0
        sequence_gaps = 0
        bad_frames = 0
        last_sequence: int | None = None
        payload_sizes: list[int] = []
        arrivals: list[float] = []
        errors: list[str] = []

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
                        sock = self._open_stream(host)
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
                    frames += 1
                    bytes_received += FRAME_HEADER.size + payload_length
                    payload_sizes.append(payload_length)
                    arrivals.append(time.monotonic())
                except (socket.timeout, TimeoutError, EOFError, OSError, ValueError) as exc:
                    disconnects += 1
                    errors.append(f"{type(exc).__name__}: {exc}")
                    close_socket()
                    time.sleep(0.10)
        finally:
            close_socket()
            poll_stop.set()
            if poll_thread is not None:
                poll_thread.join(timeout=1.0)

        if len(arrivals) >= 2:
            elapsed = max(0.001, arrivals[-1] - arrivals[0])
            measured_fps = (len(arrivals) - 1) / elapsed
        else:
            measured_fps = 0.0

        return {
            "frames": frames,
            "bytes_received": bytes_received,
            "measured_fps": round(measured_fps, 2),
            "connections": connections,
            "disconnects": disconnects,
            "sequence_gaps": sequence_gaps,
            "bad_frames": bad_frames,
            "payload_avg_bytes": round(statistics.mean(payload_sizes)) if payload_sizes else 0,
            "payload_min_bytes": min(payload_sizes) if payload_sizes else 0,
            "payload_max_bytes": max(payload_sizes) if payload_sizes else 0,
            "errors": errors[:8],
            "status_poll_successes": len(poll_latencies),
            "status_poll_failures": len(poll_failures),
            "status_poll_avg_ms": round(statistics.mean(poll_latencies), 1) if poll_latencies else None,
            "status_poll_errors": poll_failures[:8],
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
    ) -> dict[str, Any]:
        error: str | None = None
        try:
            remote_camera_manager.connect(host=host, source_id=source_id)
            remote_camera_manager.start_stream(settings=settings, target_fps=DIRECT_TARGET_FPS)
        except AppError as exc:
            return {
                "frames": 0,
                "failed_fetches": 0,
                "reconnects": 0,
                "session_recoveries": 0,
                "stream_connected": False,
                "measured_fps": 0.0,
                "error": exc.message,
            }

        phase_started = time.monotonic()
        last_status: dict[str, Any] = {}
        while time.monotonic() - phase_started < MANAGED_PHASE_SECONDS:
            last_status = remote_camera_manager.status(refresh_device=False)
            time.sleep(0.25)

        frames = _safe_int(last_status.get("successful_fetches"))
        failed = _safe_int(last_status.get("failed_fetches"))
        reconnects = _safe_int(last_status.get("stream_reconnects"))
        recoveries = _safe_int(last_status.get("session_recoveries"))
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
            "stream_connected": stream_connected,
            "measured_fps": round(measured_fps, 2),
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
            raise AppError(
                ErrorCode.INVALID_REQUEST,
                "A camera diagnostic run is already in progress.",
                status_code=409,
            )

        run_id = f"camdiag-{uuid4().hex[:10]}"
        started_epoch_ms = int(time.time() * 1000)
        started_monotonic = time.monotonic()
        checks: list[DiagnosticCheck] = []
        state_restored = False
        restore_error: str | None = None
        restore_attempted = False
        restore_context: dict[str, Any] | None = None

        try:
            initial_status = remote_camera_manager.status(refresh_device=False)
            profile = self._profile_from_status(initial_status)
            source_id = str(profile["source_id"])
            host = normalize_private_lan_ipv4(str(profile["host"]))
            settings = dict(profile.get("settings") or {})
            target_fps = _safe_int(profile.get("target_fps"), 15)
            was_connected = bool(profile.get("connected"))
            was_streaming = bool(profile.get("streaming"))
            simulation_was_enabled = bool(camera_frame_service.simulation_enabled)
            restore_context = {
                "host": host,
                "source_id": source_id,
                "settings": settings,
                "target_fps": target_fps,
                "was_connected": was_connected,
                "was_streaming": was_streaming,
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

            # 1. Direct control-plane probes.
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
            protocol_ok = (
                str(last_device_status.get("protocol") or "") in COMPATIBLE_CAMERA_PROTOCOLS
                and str(last_device_status.get("stream_protocol") or "") == FRAME_PROTOCOL
            ) if last_device_status else False
            camera_ready = bool(last_device_status.get("camera_ready")) if last_device_status else False

            rssi_values = [
                _safe_int(item.get("rssi"), -127)
                for item in status_samples
                if item.get("rssi") is not None
            ]
            rssi_values = [value for value in rssi_values if value > -127]
            rssi_min = min(rssi_values) if rssi_values else None
            rssi_max = max(rssi_values) if rssi_values else None
            rssi_avg = round(statistics.mean(rssi_values), 1) if rssi_values else None

            control_status = "pass" if control_successes == CONTROL_PROBE_ATTEMPTS else "warn" if control_successes else "fail"
            checks.append({
                "id": "control",
                "label": "ESP HTTP control",
                "status": control_status,
                "detail": (
                    f"{control_successes}/{CONTROL_PROBE_ATTEMPTS} /status probes succeeded"
                    + (f"; average {statistics.mean(control_latencies):.0f} ms" if control_latencies else "")
                ),
                "metrics": {
                    "successes": control_successes,
                    "failures": control_failures,
                    "average_ms": round(statistics.mean(control_latencies), 1) if control_latencies else None,
                    "errors": control_errors[:3],
                },
            })

            checks.append({
                "id": "firmware",
                "label": "Firmware / wire protocol",
                "status": "pass" if protocol_ok else "fail",
                "detail": (
                    f"{last_device_status.get('protocol')} + {last_device_status.get('stream_protocol')}"
                    if last_device_status else "No device status available"
                ),
                "metrics": {
                    "camera_protocol": last_device_status.get("protocol"),
                    "stream_protocol": last_device_status.get("stream_protocol"),
                    "expected_camera_protocol": CAMERA_PROTOCOL,
                    "expected_stream_protocol": FRAME_PROTOCOL,
                },
            })

            checks.append({
                "id": "camera_sensor",
                "label": "Camera sensor readiness",
                "status": "pass" if camera_ready else "fail",
                "detail": "ESP reports camera_ready=true" if camera_ready else "ESP did not report a ready camera sensor",
                "metrics": {"camera_ready": camera_ready},
            })

            wifi_status = "warn" if rssi_min is not None and rssi_min <= -75 else "pass" if rssi_min is not None else "warn"
            checks.append({
                "id": "wifi",
                "label": "Wi-Fi link margin",
                "status": wifi_status,
                "detail": (
                    f"RSSI average {rssi_avg} dBm, range {rssi_min}..{rssi_max} dBm"
                    if rssi_avg is not None else "RSSI telemetry unavailable"
                ),
                "metrics": {
                    "rssi_avg": rssi_avg,
                    "rssi_min": rssi_min,
                    "rssi_max": rssi_max,
                    "bssid": last_device_status.get("wifi_bssid"),
                    "channel": last_device_status.get("wifi_channel"),
                },
            })

            clean_phase: dict[str, Any] = {
                "frames": 0, "disconnects": 0, "measured_fps": 0.0, "status_poll_failures": 0
            }
            polled_phase: dict[str, Any] = {
                "frames": 0, "disconnects": 0, "measured_fps": 0.0, "status_poll_failures": 0
            }
            managed_phase: dict[str, Any] = {
                "frames": 0, "failed_fetches": 0, "reconnects": 0, "session_recoveries": 0,
                "stream_connected": False, "measured_fps": 0.0, "error": None,
            }
            send_failures_delta = 0
            deadline_drops_delta = 0
            after_direct_status = dict(last_device_status)

            if control_successes > 0 and protocol_ok and camera_ready:
                baseline_send_failures = _safe_int(last_device_status.get("stream_send_failures"))
                baseline_deadlines = _safe_int(last_device_status.get("stream_deadline_drops"))

                # Stop/config/start using the saved image settings but conservative 5 FPS.
                try:
                    try:
                        self._control_action(host, "/stop")
                    except Exception:
                        pass
                    self._control_action(host, "/config", query=self._settings_query(settings, DIRECT_TARGET_FPS))
                    started = self._control_action(host, "/start")
                    if started.get("session_active") is not True:
                        raise OSError("ESP did not confirm session_active=true")

                    clean_phase = self._run_stream_phase(host, seconds=DIRECT_PHASE_SECONDS, poll_status=False)
                    time.sleep(0.25)
                    polled_phase = self._run_stream_phase(host, seconds=DIRECT_PHASE_SECONDS, poll_status=True)
                    try:
                        after_direct_status, _ = self._http_json(host, "/status")
                    except Exception:
                        after_direct_status = dict(started)
                    try:
                        self._control_action(host, "/stop")
                    except Exception:
                        pass
                except Exception as exc:
                    clean_phase["errors"] = [f"setup {type(exc).__name__}: {exc}"]
                    try:
                        after_direct_status, _ = self._http_json(host, "/status")
                    except Exception:
                        pass

                send_failures_delta = max(
                    0,
                    _safe_int(after_direct_status.get("stream_send_failures")) - baseline_send_failures,
                )
                deadline_drops_delta = max(
                    0,
                    _safe_int(after_direct_status.get("stream_deadline_drops")) - baseline_deadlines,
                )

                clean_good = clean_phase.get("frames", 0) >= 12 and clean_phase.get("disconnects", 0) == 0
                checks.append({
                    "id": "direct_stream",
                    "label": "Direct ATL1 camera stream",
                    "status": "pass" if clean_good else "fail",
                    "detail": (
                        f"{clean_phase.get('frames', 0)} frames, {clean_phase.get('measured_fps', 0)} FPS, "
                        f"{clean_phase.get('disconnects', 0)} disconnects"
                    ),
                    "metrics": clean_phase,
                })

                polled_good = polled_phase.get("frames", 0) >= 12 and polled_phase.get("disconnects", 0) == 0
                checks.append({
                    "id": "control_during_stream",
                    "label": "Streaming with /status polling",
                    "status": "pass" if polled_good and polled_phase.get("status_poll_failures", 0) == 0 else "fail",
                    "detail": (
                        f"{polled_phase.get('frames', 0)} frames, {polled_phase.get('disconnects', 0)} stream disconnects, "
                        f"{polled_phase.get('status_poll_failures', 0)} status-poll failures"
                    ),
                    "metrics": polled_phase,
                })

                # Exercise the normal PC Studio worker after the direct receiver.
                managed_phase = self._managed_phase(host=host, source_id=source_id, settings=settings)
                managed_good = managed_phase.get("frames", 0) >= 8 and managed_phase.get("failed_fetches", 0) == 0
                checks.append({
                    "id": "pc_studio_managed",
                    "label": "Normal PC Studio stream worker",
                    "status": "pass" if managed_good else "fail",
                    "detail": (
                        f"{managed_phase.get('frames', 0)} frames, {managed_phase.get('failed_fetches', 0)} failures, "
                        f"{managed_phase.get('reconnects', 0)} reconnects"
                    ),
                    "metrics": managed_phase,
                })
            else:
                checks.extend([
                    {
                        "id": "direct_stream",
                        "label": "Direct ATL1 camera stream",
                        "status": "skip",
                        "detail": "Skipped because control/protocol/camera readiness did not pass.",
                        "metrics": {},
                    },
                    {
                        "id": "control_during_stream",
                        "label": "Streaming with /status polling",
                        "status": "skip",
                        "detail": "Skipped because the direct stream could not be armed safely.",
                        "metrics": {},
                    },
                    {
                        "id": "pc_studio_managed",
                        "label": "Normal PC Studio stream worker",
                        "status": "skip",
                        "detail": "Skipped because the ESP was not ready for a managed stream test.",
                        "metrics": {},
                    },
                ])

            diagnosis = classify_camera_diagnostic(
                control_successes=control_successes,
                protocol_ok=protocol_ok,
                camera_ready=camera_ready,
                clean_frames=_safe_int(clean_phase.get("frames")),
                clean_disconnects=_safe_int(clean_phase.get("disconnects")),
                clean_bad_frames=_safe_int(clean_phase.get("bad_frames")),
                polled_frames=_safe_int(polled_phase.get("frames")),
                polled_disconnects=_safe_int(polled_phase.get("disconnects")),
                polled_bad_frames=_safe_int(polled_phase.get("bad_frames")),
                status_poll_failures=_safe_int(polled_phase.get("status_poll_failures")),
                managed_frames=_safe_int(managed_phase.get("frames")),
                managed_failed_fetches=_safe_int(managed_phase.get("failed_fetches")),
                send_failures_delta=send_failures_delta,
                deadline_drops_delta=deadline_drops_delta,
                rssi_min=rssi_min,
            )

            restore_attempted = True
            state_restored, restore_error = self._restore_state(
                host=host,
                source_id=source_id,
                settings=settings,
                target_fps=target_fps,
                was_connected=was_connected,
                was_streaming=was_streaming,
                simulation_was_enabled=simulation_was_enabled,
            )
            checks.append({
                "id": "state_restore",
                "label": "Restore previous camera state",
                "status": "pass" if state_restored else "warn",
                "detail": "Previous camera/simulation state restored." if state_restored else f"Automatic restore needs attention: {restore_error}",
                "metrics": {"restored": state_restored, "error": restore_error},
            })

            duration_ms = int(round((time.monotonic() - started_monotonic) * 1000))
            metrics = {
                "control_successes": control_successes,
                "control_failures": control_failures,
                "control_avg_ms": round(statistics.mean(control_latencies), 1) if control_latencies else None,
                "rssi_avg": rssi_avg,
                "rssi_min": rssi_min,
                "rssi_max": rssi_max,
                "wifi_bssid": after_direct_status.get("wifi_bssid") or last_device_status.get("wifi_bssid"),
                "wifi_channel": after_direct_status.get("wifi_channel") or last_device_status.get("wifi_channel"),
                "direct_clean_frames": _safe_int(clean_phase.get("frames")),
                "direct_clean_fps": _safe_float(clean_phase.get("measured_fps")),
                "direct_clean_disconnects": _safe_int(clean_phase.get("disconnects")),
                "direct_clean_bad_frames": _safe_int(clean_phase.get("bad_frames")),
                "direct_polled_frames": _safe_int(polled_phase.get("frames")),
                "direct_polled_fps": _safe_float(polled_phase.get("measured_fps")),
                "direct_polled_disconnects": _safe_int(polled_phase.get("disconnects")),
                "direct_polled_bad_frames": _safe_int(polled_phase.get("bad_frames")),
                "status_poll_failures": _safe_int(polled_phase.get("status_poll_failures")),
                "managed_frames": _safe_int(managed_phase.get("frames")),
                "managed_failed_fetches": _safe_int(managed_phase.get("failed_fetches")),
                "managed_reconnects": _safe_int(managed_phase.get("reconnects")),
                "managed_session_recoveries": _safe_int(managed_phase.get("session_recoveries")),
                "device_send_failures_delta": send_failures_delta,
                "device_deadline_drops_delta": deadline_drops_delta,
                "last_send_errno": after_direct_status.get("last_send_errno"),
                "last_send_accepted_bytes": after_direct_status.get("last_send_accepted_bytes"),
                "last_frame_bytes": after_direct_status.get("last_frame_bytes"),
                "send_ewma_ms": after_direct_status.get("send_ewma_ms"),
                "wifi_disconnects": after_direct_status.get("wifi_disconnects"),
                "wifi_reconnects": after_direct_status.get("wifi_reconnects"),
            }

            report = {
                "run_id": run_id,
                "started_at_ms": started_epoch_ms,
                "duration_ms": duration_ms,
                "source_id": source_id,
                "host": host,
                **diagnosis,
                "checks": checks,
                "metrics": metrics,
                "device": {
                    "protocol": after_direct_status.get("protocol") or last_device_status.get("protocol"),
                    "stream_protocol": after_direct_status.get("stream_protocol") or last_device_status.get("stream_protocol"),
                    "firmware_revision": after_direct_status.get("firmware_revision") or last_device_status.get("firmware_revision"),
                    "camera_ready": after_direct_status.get("camera_ready", camera_ready),
                    "rssi": after_direct_status.get("rssi"),
                    "wifi_bssid": after_direct_status.get("wifi_bssid"),
                    "wifi_channel": after_direct_status.get("wifi_channel"),
                },
                "state_restored": state_restored,
                "restore_error": restore_error,
                "diagnostic_target_fps": DIRECT_TARGET_FPS,
                "prototype_only": True,
            }

            logger.info(
                "Camera diagnostic run completed",
                extra={
                    "run_id": run_id,
                    "source_id": source_id,
                    "host": host,
                    "diagnosis_code": report["diagnosis_code"],
                    "overall": report["overall"],
                    "duration_ms": duration_ms,
                },
            )
            return report
        finally:
            if restore_context is not None and not restore_attempted:
                try:
                    self._restore_state(**restore_context)
                except Exception:
                    logger.exception("Camera diagnostic emergency state restore failed")
            self._run_lock.release()


camera_diagnostic_service = CameraDiagnosticService()
