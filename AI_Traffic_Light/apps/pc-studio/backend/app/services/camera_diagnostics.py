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
from app.services.camera_diagnostic_analysis import (
    EXPECTED_CONTROL_PROBES,
    analyze_camera_bottlenecks,
    classify_camera_diagnostic,
    percentile,
    phase_clean,
    phase_ratio,
    safe_float,
    safe_int,
)
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
CONTROL_PROBE_ATTEMPTS = EXPECTED_CONTROL_PROBES
CONTROL_TIMEOUT_SECONDS = 2.5
CONTROL_ACTION_ATTEMPTS = 3
CONTROL_ACTION_BACKOFF_SECONDS = 0.15
LOAD_TARGET_FPS = (5, 10, 15)
LOAD_PHASE_SECONDS = 5.0
CONTENTION_PHASE_SECONDS = 8.0
STABILITY_PHASE_SECONDS = 20.0
MANAGED_PHASE_SECONDS = 10.0
STREAM_CONNECT_TIMEOUT_SECONDS = 2.0
STREAM_READ_TIMEOUT_SECONDS = 2.5
STATUS_POLL_INTERVAL_SECONDS = 1.0
FRAME_HEADER = struct.Struct("!4sIII")
FRAME_MAGIC = b"ATL1"
FRAME_SIZE_DIMENSIONS = {
    "QQVGA": (160, 120), "HQVGA": (240, 176), "QVGA": (320, 240), "CIF": (400, 296),
    "VGA": (640, 480), "SVGA": (800, 600), "XGA": (1024, 768), "SXGA": (1280, 1024), "UXGA": (1600, 1200),
}


class CameraDiagnosticService:
    """One-click state-restoring functionality, stability and bottleneck diagnosis."""

    def __init__(self) -> None:
        self._run_lock = Lock()

    @staticmethod
    def _http_json(host: str, path: str, method: str = "GET", query: dict[str, str] | None = None) -> tuple[dict[str, Any], float]:
        target = path + (("?" + urlencode(query)) if query else "")
        started = time.perf_counter()
        connection = http.client.HTTPConnection(host, CONTROL_PORT, timeout=CONTROL_TIMEOUT_SECONDS)
        try:
            connection.request(
                method, target, body=b"" if method != "GET" else None,
                headers={"Accept": "application/json", "User-Agent": "AiTL-PC-Studio-Camera-Diagnostics", "Connection": "close"},
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

    def _control_action(self, host: str, path: str, method: str = "POST", query: dict[str, str] | None = None) -> dict[str, Any]:
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
    def _settings_match(device_settings: Any, expected: dict[str, Any]) -> tuple[bool, list[str]]:
        if not isinstance(device_settings, dict):
            return False, ["settings object missing"]
        mismatches: list[str] = []
        for key in CAMERA_SETTING_KEYS:
            if key not in device_settings:
                mismatches.append(f"{key}=missing")
                continue
            actual, wanted = device_settings[key], expected[key]
            normalized = actual
            if isinstance(wanted, bool):
                normalized = actual if isinstance(actual, bool) else str(actual).lower() in {"1", "true", "on"}
            elif isinstance(wanted, int):
                normalized = safe_int(actual, -999999)
            else:
                normalized = str(actual)
            if normalized != wanted:
                mismatches.append(f"{key}:{actual!r}!={wanted!r}")
        return not mismatches, mismatches

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

    def _run_stream_phase(self, host: str, *, seconds: float, target_fps: int, poll_status: bool) -> dict[str, Any]:
        """Measure a live phase and snapshot ESP counters before intentionally closing its socket."""
        try:
            start_status, _ = self._http_json(host, "/status")
        except Exception:
            start_status = {}

        poll_stop = Event()
        poll_latencies: list[float] = []
        poll_failures: list[str] = []
        poll_samples: list[dict[str, Any]] = []

        def poll_worker() -> None:
            while not poll_stop.wait(STATUS_POLL_INTERVAL_SECONDS):
                try:
                    status, elapsed = self._http_json(host, "/status")
                    poll_samples.append(status)
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
        connections = disconnects = frames = bytes_received = sequence_gaps = bad_frames = 0
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
                        time.sleep(0.1)
                        continue
                try:
                    header = self._recv_exact(sock, FRAME_HEADER.size)
                    magic, payload_length, sequence, _source_uptime = FRAME_HEADER.unpack(header)
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
                    time.sleep(0.1)
        finally:
            poll_stop.set()
            if poll_thread is not None:
                poll_thread.join(timeout=1.5)
            try:
                end_status, _ = self._http_json(host, "/status")
            except Exception as exc:
                errors.append(f"end-status {type(exc).__name__}: {exc}")
                end_status = dict(poll_samples[-1]) if poll_samples else dict(start_status)
            close_socket()

        elapsed = max(0.001, time.monotonic() - phase_started)
        measured_fps = ((len(arrivals) - 1) / max(0.001, arrivals[-1] - arrivals[0])) if len(arrivals) >= 2 else 0.0
        intervals = [(b - a) * 1000.0 for a, b in zip(arrivals, arrivals[1:])]
        period_ms = 1000.0 / max(1, target_fps)
        stall_threshold = max(500.0, period_ms * 2.5)
        rssi_values: list[int] = []
        for sample in [start_status, *poll_samples, end_status]:
            if sample.get("rssi") is not None:
                value = safe_int(sample.get("rssi"), -127)
                if value > -127:
                    rssi_values.append(value)

        return {
            "target_fps": target_fps,
            "duration_seconds": round(elapsed, 2),
            "frames": frames,
            "bytes_received": bytes_received,
            "throughput_mbps": round(bytes_received * 8.0 / elapsed / 1_000_000.0, 3),
            "measured_fps": round(measured_fps, 2),
            "fps_ratio": round(measured_fps / max(1, target_fps), 3),
            "connections": connections,
            "disconnects": disconnects,
            "sequence_gaps": sequence_gaps,
            "bad_frames": bad_frames,
            "payload_avg_bytes": round(statistics.mean(payload_sizes)) if payload_sizes else 0,
            "payload_min_bytes": min(payload_sizes) if payload_sizes else 0,
            "payload_max_bytes": max(payload_sizes) if payload_sizes else 0,
            "interval_avg_ms": round(statistics.mean(intervals), 1) if intervals else None,
            "interval_p50_ms": round(percentile(intervals, 0.50) or 0.0, 1) if intervals else None,
            "interval_p95_ms": round(percentile(intervals, 0.95) or 0.0, 1) if intervals else None,
            "interval_max_ms": round(max(intervals), 1) if intervals else None,
            "jitter_ms": round(statistics.pstdev(intervals), 1) if len(intervals) >= 2 else 0.0,
            "stall_intervals": sum(1 for interval in intervals if interval > stall_threshold),
            "status_poll_successes": len(poll_latencies),
            "status_poll_failures": len(poll_failures),
            "status_poll_avg_ms": round(statistics.mean(poll_latencies), 1) if poll_latencies else None,
            "status_poll_p95_ms": round(percentile(poll_latencies, 0.95) or 0.0, 1) if poll_latencies else None,
            "status_poll_errors": poll_failures[:8],
            "rssi_avg": round(statistics.mean(rssi_values), 1) if rssi_values else None,
            "rssi_min": min(rssi_values) if rssi_values else None,
            "rssi_max": max(rssi_values) if rssi_values else None,
            "unexpected_send_failures": max(0, safe_int(end_status.get("stream_send_failures")) - safe_int(start_status.get("stream_send_failures"))),
            "deadline_drops": max(0, safe_int(end_status.get("stream_deadline_drops")) - safe_int(start_status.get("stream_deadline_drops"))),
            "slow_frames": max(0, safe_int(end_status.get("transport_slow_frames")) - safe_int(start_status.get("transport_slow_frames"))),
            "wifi_disconnects": max(0, safe_int(end_status.get("wifi_disconnects")) - safe_int(start_status.get("wifi_disconnects"))),
            "wifi_reconnects": max(0, safe_int(end_status.get("wifi_reconnects")) - safe_int(start_status.get("wifi_reconnects"))),
            "device_send_ewma_ms": end_status.get("send_ewma_ms"),
            "device_last_send_ms": end_status.get("last_send_ms"),
            "device_last_capture_ms": end_status.get("last_capture_ms"),
            "device_last_send_errno": end_status.get("last_send_errno"),
            "device_last_send_accepted_bytes": end_status.get("last_send_accepted_bytes"),
            "device_last_frame_bytes": end_status.get("last_frame_bytes"),
            "device_last_frame_width": end_status.get("last_frame_width"),
            "device_last_frame_height": end_status.get("last_frame_height"),
            "errors": errors[:10],
            "_end_status": end_status,
        }

    @staticmethod
    def _public_phase(phase: dict[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in phase.items() if not key.startswith("_")}

    def _run_configured_phase(self, host: str, settings: dict[str, Any], target_fps: int, seconds: float, *, poll_status: bool) -> dict[str, Any]:
        try:
            self._control_action(host, "/stop")
        except Exception:
            pass
        configured = self._control_action(host, "/config", query=self._settings_query(settings, target_fps))
        settings_match, mismatches = self._settings_match(configured.get("settings"), settings)
        started = self._control_action(host, "/start")
        if started.get("session_active") is not True:
            raise OSError("ESP did not confirm session_active=true")
        phase = self._run_stream_phase(host, seconds=seconds, target_fps=target_fps, poll_status=poll_status)
        end_failures = safe_int((phase.get("_end_status") or {}).get("stream_send_failures"))
        stop_error: str | None = None
        try:
            stopped = self._control_action(host, "/stop")
        except Exception as exc:
            stopped = {}
            stop_error = f"{type(exc).__name__}: {exc}"
        time.sleep(0.12)
        try:
            post_stop, _ = self._http_json(host, "/status")
        except Exception:
            post_stop = stopped
        phase["phase_boundary_send_resets"] = max(0, safe_int(post_stop.get("stream_send_failures")) - end_failures)
        phase["config_settings_match"] = settings_match
        phase["config_setting_mismatches"] = mismatches[:8]
        phase["session_started"] = True
        phase["session_stopped"] = post_stop.get("session_active") is False
        phase["stop_error"] = stop_error
        return phase

    @staticmethod
    def _profile_from_status(manager_status: dict[str, Any]) -> dict[str, Any]:
        source_id = manager_status.get("active_source_id")
        if not source_id:
            raise AppError(ErrorCode.CAMERA_NOT_CONNECTED, "Save and select an ESP camera in Camera Sources before running diagnostics.", status_code=409)
        cameras = manager_status.get("cameras") if isinstance(manager_status.get("cameras"), list) else []
        profile = next((item for item in cameras if isinstance(item, dict) and item.get("source_id") == source_id), None)
        if profile is None:
            raise AppError(ErrorCode.CAMERA_NOT_CONNECTED, "The selected ESP camera profile could not be resolved for diagnostics.", status_code=409)
        return dict(profile)

    def _managed_phase(self, *, host: str, source_id: str, settings: dict[str, Any], target_fps: int) -> dict[str, Any]:
        try:
            remote_camera_manager.connect(host=host, source_id=source_id)
            remote_camera_manager.start_stream(settings=settings, target_fps=target_fps)
        except AppError as exc:
            return {"target_fps": target_fps, "frames": 0, "failed_fetches": 0, "reconnects": 0, "session_recoveries": 0, "measured_fps": 0.0, "error": exc.message}
        baseline = remote_camera_manager.status(refresh_device=False)
        base_frames = safe_int(baseline.get("successful_fetches"))
        base_failed = safe_int(baseline.get("failed_fetches"))
        base_reconnects = safe_int(baseline.get("stream_reconnects"))
        base_recoveries = safe_int(baseline.get("session_recoveries"))
        base_bytes = safe_int(baseline.get("stream_bytes_received"))
        started = time.monotonic()
        last = baseline
        while time.monotonic() - started < MANAGED_PHASE_SECONDS:
            last = remote_camera_manager.status(refresh_device=False)
            time.sleep(0.25)
        elapsed = max(0.001, time.monotonic() - started)
        result = {
            "target_fps": target_fps,
            "duration_seconds": round(elapsed, 2),
            "frames": max(0, safe_int(last.get("successful_fetches")) - base_frames),
            "failed_fetches": max(0, safe_int(last.get("failed_fetches")) - base_failed),
            "reconnects": max(0, safe_int(last.get("stream_reconnects")) - base_reconnects),
            "session_recoveries": max(0, safe_int(last.get("session_recoveries")) - base_recoveries),
            "measured_fps": 0.0,
            "throughput_mbps": round(max(0, safe_int(last.get("stream_bytes_received")) - base_bytes) * 8.0 / elapsed / 1_000_000.0, 3),
            "error": str(last.get("last_error")) if last.get("last_error") else None,
        }
        result["measured_fps"] = round(result["frames"] / elapsed, 2)
        result["fps_ratio"] = round(result["measured_fps"] / max(1, target_fps), 3)
        try:
            remote_camera_manager.stop_stream(best_effort=True)
        except Exception:
            pass
        return result

    def _restore_state(self, *, host: str, source_id: str, settings: dict[str, Any], target_fps: int, was_connected: bool, was_streaming: bool, simulation_was_enabled: bool) -> tuple[bool, str | None]:
        try:
            remote_camera_manager.save_profile(host=host, source_id=source_id, settings=settings, target_fps=target_fps, select=True)
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
            return False, f"{type(exc).__name__}: {exc}"

    def run(self) -> dict[str, Any]:
        if not self._run_lock.acquire(blocking=False):
            raise AppError(ErrorCode.INVALID_REQUEST, "A camera diagnostic run is already in progress.", status_code=409)
        run_id = f"camdiag-{uuid4().hex[:10]}"
        started_epoch_ms = int(time.time() * 1000)
        started_mono = time.monotonic()
        checks: list[dict[str, Any]] = []
        restore_context: dict[str, Any] | None = None
        restore_attempted = False
        try:
            initial = remote_camera_manager.status(refresh_device=False)
            profile = self._profile_from_status(initial)
            source_id = str(profile["source_id"])
            host = normalize_private_lan_ipv4(str(profile["host"]))
            settings = dict(profile.get("settings") or {})
            saved_target = safe_int(profile.get("target_fps"), 15)
            was_connected, was_streaming = bool(profile.get("connected")), bool(profile.get("streaming"))
            simulation_was_enabled = bool(camera_frame_service.simulation_enabled)
            restore_context = dict(host=host, source_id=source_id, settings=settings, target_fps=saved_target, was_connected=was_connected, was_streaming=was_streaming, simulation_was_enabled=simulation_was_enabled)
            if simulation_was_enabled:
                camera_frame_service.set_simulation(False)
                remote_camera_manager.sync_after_simulation_change()
            if was_streaming:
                try:
                    remote_camera_manager.stop_stream(best_effort=True)
                except Exception:
                    pass

            # 1) Control/firmware/sensor/Wi-Fi baseline.
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
                time.sleep(0.08)
            successes = len(status_samples)
            last_device = status_samples[-1] if status_samples else {}
            protocol_ok = bool(last_device) and str(last_device.get("protocol") or "") in COMPATIBLE_CAMERA_PROTOCOLS and str(last_device.get("stream_protocol") or "") == FRAME_PROTOCOL
            camera_ready = bool(last_device.get("camera_ready")) if last_device else False
            p50 = round(percentile(control_latencies, .50) or 0.0, 1) if control_latencies else None
            p95 = round(percentile(control_latencies, .95) or 0.0, 1) if control_latencies else None
            control_max = round(max(control_latencies), 1) if control_latencies else None
            control_avg = round(statistics.mean(control_latencies), 1) if control_latencies else None
            control_jitter = round(statistics.pstdev(control_latencies), 1) if len(control_latencies) > 1 else 0.0 if control_latencies else None
            rssis = [safe_int(s.get("rssi"), -127) for s in status_samples if s.get("rssi") is not None]
            rssis = [v for v in rssis if v > -127]
            rssi_min, rssi_max = (min(rssis), max(rssis)) if rssis else (None, None)
            rssi_avg = round(statistics.mean(rssis), 1) if rssis else None
            checks += [
                {"id":"control","category":"functionality","label":"ESP HTTP control","status":"pass" if successes==CONTROL_PROBE_ATTEMPTS else "warn" if successes else "fail","detail":f"{successes}/{CONTROL_PROBE_ATTEMPTS} probes; p50 {p50} ms, p95 {p95} ms","metrics":{"average_ms":control_avg,"p50_ms":p50,"p95_ms":p95,"max_ms":control_max,"jitter_ms":control_jitter,"errors":control_errors[:5]}},
                {"id":"firmware","category":"functionality","label":"Firmware / wire protocol","status":"pass" if protocol_ok else "fail","detail":f"{last_device.get('protocol')} + {last_device.get('stream_protocol')}","metrics":{}},
                {"id":"camera_sensor","category":"functionality","label":"Camera sensor readiness","status":"pass" if camera_ready else "fail","detail":"camera_ready=true" if camera_ready else "camera_ready=false/unavailable","metrics":{}},
                {"id":"wifi","category":"stability","label":"Wi-Fi link margin","status":"warn" if rssi_min is None or rssi_min<=-68 else "pass","detail":f"RSSI average {rssi_avg} dBm, range {rssi_min}..{rssi_max} dBm","metrics":{"bssid":last_device.get('wifi_bssid'),"channel":last_device.get('wifi_channel')}},
            ]

            load_phases: list[dict[str, Any]] = []
            contention_phase: dict[str, Any] = {"target_fps":5,"frames":0,"measured_fps":0.0,"disconnects":0,"bad_frames":0,"status_poll_failures":0}
            stability_phase: dict[str, Any] = {"target_fps":saved_target,"frames":0,"measured_fps":0.0,"disconnects":0,"bad_frames":0}
            managed_phase: dict[str, Any] = {"target_fps":saved_target,"frames":0,"measured_fps":0.0,"failed_fetches":0,"reconnects":0}
            boundary_resets = 0
            settings_match = lifecycle_ok = quality_preserved = image_integrity = False
            after_direct = dict(last_device)

            if successes and protocol_ok and camera_ready:
                # 2) Load ladder using identical saved image settings.
                for target in LOAD_TARGET_FPS:
                    try:
                        phase = self._run_configured_phase(host, settings, target, LOAD_PHASE_SECONDS, poll_status=False)
                    except Exception as exc:
                        phase = {"target_fps":target,"frames":0,"measured_fps":0.0,"disconnects":1,"bad_frames":0,"unexpected_send_failures":0,"deadline_drops":0,"errors":[f"setup {type(exc).__name__}: {exc}"]}
                    load_phases.append(phase)
                    boundary_resets += safe_int(phase.get("phase_boundary_send_resets"))
                    if target == 5:
                        settings_match = bool(phase.get("config_settings_match"))
                        lifecycle_ok = bool(phase.get("session_started")) and bool(phase.get("session_stopped"))
                    if target == 5 and safe_int(phase.get("frames")) < 3:
                        break
                checks += [
                    {"id":"config_roundtrip","category":"functionality","label":"Camera configuration round-trip","status":"pass" if settings_match else "fail","detail":"Saved OV2640 settings echoed correctly." if settings_match else "Saved settings did not round-trip correctly.","metrics":{}},
                    {"id":"session_lifecycle","category":"functionality","label":"Start / stop session lifecycle","status":"pass" if lifecycle_ok else "fail","detail":"ESP confirmed start and stop." if lifecycle_ok else "Session lifecycle confirmation failed.","metrics":{}},
                    {"id":"load_ladder","category":"bottleneck","label":"Current-payload FPS load ladder","status":"pass" if len(load_phases)==3 and all(phase_clean(p) for p in load_phases) else "warn","detail":", ".join(f"{safe_int(p.get('target_fps'))}→{safe_float(p.get('measured_fps')):.2f} FPS" for p in load_phases),"metrics":{"phases":[self._public_phase(p) for p in load_phases]}},
                ]

                # 3) Same-load status-poll contention comparison.
                stable_loads = [p for p in load_phases if phase_clean(p) and phase_ratio(p)>=.70]
                reference = max(stable_loads, key=lambda p:safe_int(p.get("target_fps")), default=load_phases[0])
                contention_target = max(1, safe_int(reference.get("target_fps"),5))
                try:
                    contention_phase = self._run_configured_phase(host, settings, contention_target, CONTENTION_PHASE_SECONDS, poll_status=True)
                    boundary_resets += safe_int(contention_phase.get("phase_boundary_send_resets"))
                except Exception as exc:
                    contention_phase = {"target_fps":contention_target,"frames":0,"measured_fps":0.0,"disconnects":1,"bad_frames":0,"status_poll_failures":1,"unexpected_send_failures":0,"deadline_drops":0,"errors":[str(exc)]}
                same_load_ratio = safe_float(contention_phase.get("measured_fps"))/max(.01,safe_float(reference.get("measured_fps")))
                contention_ok = phase_clean(contention_phase) and safe_int(contention_phase.get("status_poll_failures"))==0 and same_load_ratio>=.75
                checks.append({"id":"control_during_stream","category":"bottleneck","label":"Streaming with /status polling","status":"pass" if contention_ok else "warn","detail":f"{safe_float(contention_phase.get('measured_fps')):.2f} FPS, {safe_int(contention_phase.get('disconnects'))} disconnects, {safe_int(contention_phase.get('status_poll_failures'))} poll failures","metrics":self._public_phase(contention_phase)})

                # 4) Longer saved-target stability phase.
                try:
                    stability_phase = self._run_configured_phase(host, settings, saved_target, STABILITY_PHASE_SECONDS, poll_status=False)
                    boundary_resets += safe_int(stability_phase.get("phase_boundary_send_resets"))
                except Exception as exc:
                    stability_phase = {"target_fps":saved_target,"frames":0,"measured_fps":0.0,"disconnects":1,"bad_frames":0,"sequence_gaps":0,"stall_intervals":0,"unexpected_send_failures":0,"deadline_drops":0,"errors":[str(exc)]}
                stable_ratio = phase_ratio(stability_phase)
                stable_status = "fail" if not phase_clean(stability_phase) or stable_ratio<.5 else "warn" if stable_ratio<.75 or safe_int(stability_phase.get("stall_intervals")) else "pass"
                checks.append({"id":"sustained_stability","category":"stability","label":"Sustained saved-target stability","status":stable_status,"detail":f"{safe_float(stability_phase.get('duration_seconds')):.0f}s, {safe_float(stability_phase.get('measured_fps')):.2f}/{saved_target} FPS, p95 {safe_float(stability_phase.get('interval_p95_ms')):.0f} ms, {safe_int(stability_phase.get('disconnects'))} disconnects","metrics":self._public_phase(stability_phase)})
                end_status = stability_phase.get("_end_status") if isinstance(stability_phase.get("_end_status"),dict) else {}
                after_direct = dict(end_status or last_device)

                expected = FRAME_SIZE_DIMENSIONS.get(str(settings.get("frame_size") or "").upper())
                width,height=safe_int(stability_phase.get("device_last_frame_width")),safe_int(stability_phase.get("device_last_frame_height"))
                dimensions_ok = expected is None or width==0 or height==0 or (width,height)==expected
                image_integrity = safe_int(stability_phase.get("frames"))>0 and safe_int(stability_phase.get("bad_frames"))==0 and dimensions_ok
                checks.append({"id":"image_integrity","category":"functionality","label":"JPEG integrity / expected frame size","status":"pass" if image_integrity else "fail","detail":f"device frame {width}×{height}; expected {expected}","metrics":{}})

                configured_q=safe_int(after_direct.get("configured_jpeg_quality"),safe_int(settings.get("jpeg_quality")))
                effective_q=safe_int(after_direct.get("effective_jpeg_quality"),configured_q)
                configured_size=str(after_direct.get("configured_frame_size") or settings.get("frame_size") or "")
                effective_size=str(after_direct.get("effective_frame_size") or configured_size)
                quality_preserved = configured_q==safe_int(settings.get("jpeg_quality")) and effective_q==configured_q and effective_size==configured_size
                checks.append({"id":"quality_preservation","category":"functionality","label":"Saved image quality / resolution preserved","status":"pass" if quality_preserved else "fail","detail":f"JPEG q={effective_q}/{configured_q}, frame={effective_size}/{configured_size}","metrics":{}})

                # 5) Normal PC Studio managed worker, measured as true phase deltas.
                managed_phase=self._managed_phase(host=host,source_id=source_id,settings=settings,target_fps=saved_target)
                managed_good=safe_int(managed_phase.get("frames"))>=3 and safe_int(managed_phase.get("failed_fetches"))==0 and safe_int(managed_phase.get("reconnects"))==0
                checks.append({"id":"pc_studio_managed","category":"functionality","label":"Normal PC Studio stream worker","status":"pass" if managed_good else "warn" if safe_int(managed_phase.get("frames")) else "fail","detail":f"{safe_int(managed_phase.get('frames'))} frames, {safe_float(managed_phase.get('measured_fps')):.2f} FPS, {safe_int(managed_phase.get('failed_fetches'))} failures, {safe_int(managed_phase.get('reconnects'))} reconnects","metrics":managed_phase})
                contention_reference=reference
            else:
                contention_reference=None
                for cid,label,category in [
                    ("config_roundtrip","Camera configuration round-trip","functionality"),("session_lifecycle","Start / stop session lifecycle","functionality"),("load_ladder","Current-payload FPS load ladder","bottleneck"),("control_during_stream","Streaming with /status polling","bottleneck"),("sustained_stability","Sustained saved-target stability","stability"),("image_integrity","JPEG integrity / expected frame size","functionality"),("quality_preservation","Saved image quality / resolution preserved","functionality"),("pc_studio_managed","Normal PC Studio stream worker","functionality")]:
                    checks.append({"id":cid,"category":category,"label":label,"status":"skip","detail":"Skipped because control/protocol/camera readiness did not pass.","metrics":{}})

            clean_phase=load_phases[0] if load_phases else {"target_fps":5,"frames":0,"disconnects":0,"bad_frames":0}
            analysis=analyze_camera_bottlenecks(
                control_successes=successes,control_failures=len(control_errors),control_p95_ms=p95,control_jitter_ms=control_jitter,
                rssi_min=rssi_min,rssi_max=rssi_max,load_phases=load_phases,contention_phase=contention_phase,contention_reference=contention_reference,
                stability_phase=stability_phase,managed_phase=managed_phase,saved_target_fps=saved_target,
            )
            direct_phases=[*load_phases,contention_phase,stability_phase]
            unexpected_send=sum(safe_int(p.get("unexpected_send_failures")) for p in direct_phases)
            deadlines=sum(safe_int(p.get("deadline_drops")) for p in direct_phases)
            diagnosis=classify_camera_diagnostic(
                control_successes=successes,protocol_ok=protocol_ok,camera_ready=camera_ready,
                clean_frames=safe_int(clean_phase.get("frames")),clean_disconnects=safe_int(clean_phase.get("disconnects")),clean_bad_frames=safe_int(clean_phase.get("bad_frames")),
                polled_frames=safe_int(contention_phase.get("frames")),polled_disconnects=safe_int(contention_phase.get("disconnects")),polled_bad_frames=safe_int(contention_phase.get("bad_frames")),status_poll_failures=safe_int(contention_phase.get("status_poll_failures")),
                managed_frames=safe_int(managed_phase.get("frames")),managed_failed_fetches=safe_int(managed_phase.get("failed_fetches")),send_failures_delta=unexpected_send,deadline_drops_delta=deadlines,rssi_min=rssi_min,
                stability_grade=str(analysis.get("stability_grade")),saved_target_fps=saved_target,estimated_sustainable_fps=safe_float(analysis.get("peak_measured_fps")) or None,phase_boundary_send_resets=boundary_resets,
            )
            if diagnosis["overall"]=="healthy" and analysis["findings"]:
                primary=analysis["findings"][0]
                diagnosis={"overall":"warning","diagnosis_code":"bottleneck_detected","title":"Camera functions, but a measurable bottleneck remains","summary":f"The functional path passed, but the deep test ranked {str(primary['title']).lower()} as the primary bottleneck.","confidence":"medium","likely_causes":[str(primary['title'])],"recommendations":[str(primary['recommendation'])]}

            restore_attempted=True
            state_restored,restore_error=self._restore_state(**restore_context)
            if state_restored:
                try:
                    restored=self._profile_from_status(remote_camera_manager.status(refresh_device=False))
                    mismatches=[]
                    if safe_int(restored.get("target_fps"))!=saved_target:mismatches.append("target_fps")
                    if dict(restored.get("settings") or {})!=settings:mismatches.append("settings")
                    if bool(restored.get("streaming"))!=was_streaming:mismatches.append("streaming")
                    if bool(restored.get("connected"))!=(was_connected or was_streaming):mismatches.append("connected")
                    if bool(camera_frame_service.simulation_enabled)!=simulation_was_enabled:mismatches.append("simulation")
                    if mismatches:
                        state_restored=False;restore_error="Post-restore mismatch: "+", ".join(mismatches)
                except Exception as exc:
                    state_restored=False;restore_error=f"Post-restore verification failed: {exc}"
            checks.append({"id":"state_restore","category":"functionality","label":"Restore previous camera state","status":"pass" if state_restored else "warn","detail":"Previous camera/simulation state restored and verified." if state_restored else f"Restore needs attention: {restore_error}","metrics":{}})
            if not state_restored and diagnosis["overall"]!="failed":
                diagnosis={"overall":"warning","diagnosis_code":"state_restore_failed","title":"Diagnostic completed, but previous camera state was not fully restored","summary":"Evidence was collected but automatic state restoration needs attention.","confidence":"high","likely_causes":["ESP/control state changed or stopped responding during restore"],"recommendations":["Verify the saved profile and reconnect/start manually in Camera Sources."]}

            function_checks=[c for c in checks if c.get("category")=="functionality" and c.get("status")!="skip"]
            function_passes=sum(1 for c in function_checks if c.get("status")=="pass")
            function_score=round(100*function_passes/len(function_checks)) if function_checks else 0
            all_rssi=list(rssis)
            for p in direct_phases:
                for key in ("rssi_min","rssi_max"):
                    if p.get(key) is not None:all_rssi.append(safe_int(p.get(key)))
            metrics={
                "control_successes":successes,"control_failures":len(control_errors),"control_avg_ms":control_avg,"control_p50_ms":p50,"control_p95_ms":p95,"control_max_ms":control_max,"control_jitter_ms":control_jitter,
                "rssi_avg":rssi_avg,"rssi_min":min(all_rssi) if all_rssi else rssi_min,"rssi_max":max(all_rssi) if all_rssi else rssi_max,"wifi_bssid":after_direct.get("wifi_bssid") or last_device.get("wifi_bssid"),"wifi_channel":after_direct.get("wifi_channel") or last_device.get("wifi_channel"),
                "direct_clean_frames":safe_int(clean_phase.get("frames")),"direct_clean_fps":safe_float(clean_phase.get("measured_fps")),"direct_clean_disconnects":safe_int(clean_phase.get("disconnects")),"direct_clean_bad_frames":safe_int(clean_phase.get("bad_frames")),
                "direct_polled_frames":safe_int(contention_phase.get("frames")),"direct_polled_fps":safe_float(contention_phase.get("measured_fps")),"direct_polled_disconnects":safe_int(contention_phase.get("disconnects")),"direct_polled_bad_frames":safe_int(contention_phase.get("bad_frames")),"status_poll_failures":safe_int(contention_phase.get("status_poll_failures")),
                "managed_frames":safe_int(managed_phase.get("frames")),"managed_fps":safe_float(managed_phase.get("measured_fps")),"managed_failed_fetches":safe_int(managed_phase.get("failed_fetches")),"managed_reconnects":safe_int(managed_phase.get("reconnects")),"managed_session_recoveries":safe_int(managed_phase.get("session_recoveries")),
                "device_send_failures_delta":unexpected_send,"device_deadline_drops_delta":deadlines,"phase_boundary_send_resets":boundary_resets,"last_send_errno":stability_phase.get("device_last_send_errno"),"last_send_accepted_bytes":stability_phase.get("device_last_send_accepted_bytes"),"last_frame_bytes":stability_phase.get("device_last_frame_bytes"),"send_ewma_ms":stability_phase.get("device_send_ewma_ms"),"wifi_disconnects":stability_phase.get("wifi_disconnects"),"wifi_reconnects":stability_phase.get("wifi_reconnects"),
                "functionality_score":function_score,"stability_score":analysis["stability_score"],"stability_grade":analysis["stability_grade"],"peak_measured_fps":analysis["peak_measured_fps"],"peak_throughput_mbps":analysis["peak_throughput_mbps"],"estimated_sustainable_target_fps":analysis["estimated_sustainable_target_fps"],
                "stability_target_fps":saved_target,"stability_measured_fps":safe_float(stability_phase.get("measured_fps")),"stability_interval_p95_ms":stability_phase.get("interval_p95_ms"),"stability_interval_max_ms":stability_phase.get("interval_max_ms"),"stability_jitter_ms":stability_phase.get("jitter_ms"),"stability_stall_intervals":safe_int(stability_phase.get("stall_intervals")),"stability_disconnects":safe_int(stability_phase.get("disconnects")),"stability_sequence_gaps":safe_int(stability_phase.get("sequence_gaps")),"stability_bad_frames":safe_int(stability_phase.get("bad_frames")),
            }
            report={
                "run_id":run_id,"started_at_ms":started_epoch_ms,"duration_ms":int(round((time.monotonic()-started_mono)*1000)),"source_id":source_id,"host":host,**diagnosis,"checks":checks,"metrics":metrics,
                "functionality":{"score":function_score,"passed":function_passes,"total":len(function_checks),"config_roundtrip":settings_match,"session_lifecycle":lifecycle_ok},
                "stability":{"grade":analysis["stability_grade"],"score":analysis["stability_score"],"phase":self._public_phase(stability_phase)},
                "bottleneck_analysis":analysis,"load_ladder":[self._public_phase(p) for p in load_phases],"contention_phase":self._public_phase(contention_phase),"managed_phase":managed_phase,
                "device":{"protocol":after_direct.get("protocol") or last_device.get("protocol"),"stream_protocol":after_direct.get("stream_protocol") or last_device.get("stream_protocol"),"firmware_revision":after_direct.get("firmware_revision") or last_device.get("firmware_revision"),"camera_ready":after_direct.get("camera_ready",camera_ready),"rssi":after_direct.get("rssi"),"wifi_bssid":after_direct.get("wifi_bssid"),"wifi_channel":after_direct.get("wifi_channel")},
                "state_restored":state_restored,"restore_error":restore_error,"diagnostic_target_fps":5,"diagnostic_load_targets":list(LOAD_TARGET_FPS),"prototype_only":True,
            }
            logger.info("Camera diagnostic run completed",extra={"run_id":run_id,"source_id":source_id,"host":host,"diagnosis_code":report["diagnosis_code"],"overall":report["overall"],"primary_bottleneck":analysis["primary_bottleneck"],"stability_grade":analysis["stability_grade"],"duration_ms":report["duration_ms"]})
            return report
        finally:
            if restore_context is not None and not restore_attempted:
                try:self._restore_state(**restore_context)
                except Exception:logger.exception("Camera diagnostic emergency state restore failed")
            self._run_lock.release()


# Re-exported from camera_diagnostic_analysis for backward-compatible focused tests.
__all__ = ["CameraDiagnosticService", "camera_diagnostic_service", "classify_camera_diagnostic", "analyze_camera_bottlenecks"]
camera_diagnostic_service = CameraDiagnosticService()
