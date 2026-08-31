from __future__ import annotations

import http.client
import json
import re
import socket
import time
import uuid
from collections.abc import Callable
from typing import Any

ProgressCallback = Callable[[str, str], None]
R9_FIRMWARE_PREFIX = "aitl-0_3_8-r9-architecture-benchmark"
MANUAL_MJPEG_PORT = 84
HTTPD_PORT = 85
RAW_BULK_PORT = 87
BULK_BYTES = 512 * 1024


def _number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _row(rows: list[dict[str, Any]], key: str) -> dict[str, Any]:
    return next((item for item in rows if item.get("key") == key), {})


def _fps(rows: list[dict[str, Any]], key: str) -> float:
    return _number(_row(rows, key).get("measured_fps"))


def _mbps(rows: list[dict[str, Any]], key: str) -> float:
    telemetry = _row(rows, key).get("telemetry")
    return _number(telemetry.get("throughput_mbps")) if isinstance(telemetry, dict) else 0.0


def analyze_architecture_results(
    rows: list[dict[str, Any]],
    status: dict[str, Any],
    target_fps: int,
) -> dict[str, Any]:
    """Turn R9 measurements into one evidence-based bottleneck classification."""
    target = max(1, int(target_fps))
    manual = _fps(rows, "r9_manual_mjpeg")
    direct = _fps(rows, "r9_httpd_direct_mjpeg")
    cached = _fps(rows, "r9_httpd_cached_mjpeg")
    httpd_bulk = _mbps(rows, "r9_httpd_bulk")
    raw_nodelay = _mbps(rows, "r9_raw_bulk_nodelay")
    raw_nagle = _mbps(rows, "r9_raw_bulk_nagle")
    best_bulk = max(httpd_bulk, raw_nodelay, raw_nagle)
    best_camera = max(manual, direct, cached)
    httpd_vs_manual = direct / manual if manual > 0 else None
    cached_vs_direct = cached / direct if direct > 0 else None
    bulk_pair_max = max(raw_nodelay, raw_nagle)
    nagle_delta = abs(raw_nodelay - raw_nagle) / bulk_pair_max if bulk_pair_max > 0 else None
    target_floor = target * 0.70

    if 0 < best_bulk < 1.0:
        classification, confidence = "common_network_or_esp_stack_bottleneck", "high"
    elif manual > 0 and direct >= target_floor and direct >= manual * 1.5:
        classification, confidence = "manual_socket_sender_regression", "high"
    elif direct > 0 and cached >= target_floor and cached >= direct * 1.5:
        classification, confidence = "capture_send_coupling", "high"
    elif best_bulk >= 5.0 and best_camera < target * 0.35:
        classification, confidence = "camera_or_jpeg_pipeline_specific", "high"
    elif max(direct, cached) >= target_floor:
        classification, confidence = "httpd_architecture_healthy", "medium"
    else:
        classification = "mixed_architecture_bottleneck"
        confidence = "medium" if rows else "low"

    bulk_headroom = (
        "ample" if best_bulk >= 5.0 else
        "constrained" if best_bulk >= 1.0 else
        "severely_constrained" if best_bulk > 0 else
        "unknown"
    )

    findings: list[str] = []
    likely_layers: list[str] = []
    if bulk_headroom == "ample":
        findings.append(
            f"Camera-free TCP reached {best_bulk:.2f} Mbit/s, so the common ESP-to-PC path has substantial throughput headroom."
        )
    elif bulk_headroom == "severely_constrained":
        findings.append(
            f"Camera-free TCP reached only {best_bulk:.2f} Mbit/s, reproducing the slowdown without OV2640 capture or JPEG framebuffer traffic."
        )
        likely_layers.extend(["ESP Wi-Fi/lwIP", "access point/router", "PC TCP receive path", "power integrity"])

    if httpd_vs_manual is not None:
        findings.append(f"Old-style esp_http_server MJPEG ran at {httpd_vs_manual:.2f}x the manual WiFiClient MJPEG rate.")
        if httpd_vs_manual >= 1.5:
            likely_layers.append("manual WiFiClient/raw-socket sender implementation")
    if cached_vs_direct is not None:
        findings.append(f"Pi-style latest-frame caching ran at {cached_vs_direct:.2f}x the direct esp_http_server rate.")
        if cached_vs_direct >= 1.5:
            likely_layers.append("capture/send serialization and framebuffer hold time")
    if nagle_delta is not None:
        findings.append(f"Raw camera-free TCP changed by {nagle_delta * 100:.0f}% between TCP_NODELAY on and off.")
        if nagle_delta >= 0.25:
            likely_layers.append("TCP packetization/Nagle sensitivity")

    reset_reason = str(status.get("reset_reason") or "unknown")
    power_evidence = "brownout_detected" if reset_reason == "brownout" else "no_software_brownout_evidence"
    if power_evidence == "brownout_detected":
        findings.append("The ESP reports a brownout reset, so power integrity is a concrete candidate until the supply path is corrected.")
        likely_layers.append("ESP power supply / cable / regulator")
    else:
        findings.append(
            f"ESP reset reason is '{reset_reason}'. No software brownout reset is visible; this does not rule out voltage sag that did not reset the chip."
        )

    rssi = _number(status.get("rssi"), -127.0)
    if rssi >= -60:
        findings.append(
            f"RSSI is strong at {rssi:.0f} dBm. Weak signal strength is unlikely, although interference or AP scheduling can still reduce throughput."
        )
    elif rssi > -120:
        likely_layers.append("2.4 GHz RF link quality")

    next_actions = {
        "common_network_or_esp_stack_bottleneck": "Repeat R9 on a phone/PC hotspot and a known-good 5 V supply. If camera-free bulk stays below 1 Mbit/s, inspect ESP lwIP/Wi-Fi configuration before camera code.",
        "manual_socket_sender_regression": "Use esp_http_server as the leading production transport candidate; stop optimizing the manual send/select loop unless ATL1 remains necessary for another requirement.",
        "capture_send_coupling": "Adopt the newest-frame producer/consumer architecture so capture continues independently and stale frames are skipped when networking falls behind.",
        "camera_or_jpeg_pipeline_specific": "Networking is healthy without the camera. Instrument JPEG framebuffer location, copy time and framebuffer-hold time instead of changing router settings.",
        "httpd_architecture_healthy": "Promote the best esp_http_server architecture only to the next production prototype and validate stable 10–15 FPS before any release promotion.",
        "mixed_architecture_bottleneck": "No single layer is isolated. Repeat the same R9 comparison on another AP and known-good 5 V supply, then instrument only the path that remains slow.",
    }
    methods = [
        {"method": "manual WiFiClient MJPEG", "tested": True, "purpose": "Current/R5-style Arduino writer control."},
        {"method": "esp_http_server direct MJPEG", "tested": True, "purpose": "Reproduces the older V035 server architecture."},
        {"method": "esp_http_server cached latest-frame MJPEG", "tested": True, "purpose": "Pi-style decoupled producer/consumer architecture."},
        {"method": "esp_http_server camera-free bulk", "tested": True, "purpose": "Removes camera/JPEG work from the network path."},
        {"method": "raw WiFiClient camera-free bulk / TCP_NODELAY on", "tested": True, "purpose": "Arduino TCP control without camera payloads."},
        {"method": "raw WiFiClient camera-free bulk / Nagle on", "tested": True, "purpose": "Tests TCP_NODELAY/Nagle sensitivity."},
        {"method": "ATL1 DRAM-copy plain send", "tested": False, "purpose": "Already measured by R5; compare its historical result instead of duplicating it."},
        {"method": "UDP JPEG", "tested": False, "purpose": "R5 was lossy; retain as a freshness-first fallback rather than the leading candidate."},
    ]
    recommended_key = "r9_httpd_cached_mjpeg" if cached >= direct else "r9_httpd_direct_mjpeg"
    return {
        "classification": classification,
        "confidence": confidence,
        "target_fps": target,
        "manual_mjpeg_fps": round(manual, 3),
        "httpd_direct_mjpeg_fps": round(direct, 3),
        "cached_mjpeg_fps": round(cached, 3),
        "httpd_bulk_mbps": round(httpd_bulk, 3),
        "raw_bulk_nodelay_mbps": round(raw_nodelay, 3),
        "raw_bulk_nagle_mbps": round(raw_nagle, 3),
        "best_camera_fps": round(best_camera, 3),
        "best_bulk_mbps": round(best_bulk, 3),
        "bulk_headroom": bulk_headroom,
        "httpd_vs_manual_ratio": round(httpd_vs_manual, 3) if httpd_vs_manual is not None else None,
        "cached_vs_direct_ratio": round(cached_vs_direct, 3) if cached_vs_direct is not None else None,
        "nagle_sensitivity_ratio": round(nagle_delta, 3) if nagle_delta is not None else None,
        "reset_reason": reset_reason,
        "power_evidence": power_evidence,
        "rssi": rssi,
        "recommended_key": recommended_key,
        "findings": findings,
        "likely_layers": list(dict.fromkeys(likely_layers)),
        "methods_assessed": methods,
        "next_action": next_actions[classification],
    }


def _transport_row(
    key: str,
    name: str,
    transport: str,
    requested_frames: int,
    frames: int,
    bytes_received: int,
    elapsed_ms: float | None,
    detail: str,
    *,
    telemetry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    measured_fps = 1000.0 * frames / elapsed_ms if elapsed_ms and elapsed_ms > 0 and frames > 0 else None
    completion = frames / requested_frames if requested_frames > 0 else (1.0 if bytes_received > 0 else 0.0)
    return {
        "key": key,
        "name": name,
        "transport": transport,
        "status": "PASS" if completion >= 0.999 else "FAIL",
        "requested_frames": requested_frames,
        "frames": frames,
        "bytes_received": bytes_received,
        "elapsed_ms": round(elapsed_ms, 3) if elapsed_ms is not None else None,
        "measured_fps": round(measured_fps, 3) if measured_fps is not None else None,
        "completion_ratio": round(completion, 4),
        "packet_loss": None,
        "detail": detail,
        "telemetry": telemetry or {},
        "production_candidate": key in {"r9_httpd_direct_mjpeg", "r9_httpd_cached_mjpeg"},
    }


def _parse_mjpeg(body: bytes) -> tuple[int, int]:
    pattern = re.compile(br"Content-Length:\s*(\d+)\r\n\r\n", re.IGNORECASE)
    frames = total = position = 0
    while True:
        match = pattern.search(body, position)
        if match is None:
            break
        length = int(match.group(1))
        start, end = match.end(), match.end() + length
        if length <= 0 or end > len(body):
            break
        jpeg = body[start:end]
        if len(jpeg) >= 4 and jpeg[:2] == b"\xff\xd8" and jpeg[-2:] == b"\xff\xd9":
            frames += 1
            total += length
        position = end + 2
    return frames, total


class CameraArchitectureDiagnosticService:
    def _http_json(self, host: str, method: str, path: str, *, port: int = 80, timeout: float = 8.0) -> dict[str, Any]:
        connection = http.client.HTTPConnection(host, port, timeout=timeout)
        try:
            connection.request(method, path, headers={"Connection": "close", "Cache-Control": "no-cache"})
            response = connection.getresponse()
            payload = response.read()
            if not 200 <= response.status < 300:
                raise RuntimeError(f"HTTP {response.status} {path}: {payload[:200]!r}")
            return json.loads(payload.decode("utf-8")) if payload else {}
        finally:
            connection.close()

    def _mjpeg(self, host: str, port: int, path: str) -> dict[str, Any]:
        connection = http.client.HTTPConnection(host, port, timeout=15.0)
        started = time.perf_counter()
        try:
            connection.request("GET", path, headers={"Connection": "close", "Cache-Control": "no-cache"})
            response = connection.getresponse()
            if response.status != 200:
                raise RuntimeError(f"HTTP {response.status}: {response.read(512)!r}")
            body = response.read(4 * 1024 * 1024)
        finally:
            elapsed_ms = (time.perf_counter() - started) * 1000.0
            connection.close()
        frames, payload_bytes = _parse_mjpeg(body)
        return {"frames": frames, "bytes": payload_bytes, "elapsed_ms": elapsed_ms}

    def _httpd_bulk(self, host: str, bytes_requested: int) -> dict[str, Any]:
        connection = http.client.HTTPConnection(host, HTTPD_PORT, timeout=15.0)
        started = time.perf_counter()
        try:
            connection.request("GET", f"/bulk.bin?bytes={bytes_requested}", headers={"Connection": "close"})
            response = connection.getresponse()
            if response.status != 200:
                raise RuntimeError(f"HTTP bulk status {response.status}")
            body = response.read(bytes_requested + 65536)
        finally:
            elapsed_ms = (time.perf_counter() - started) * 1000.0
            connection.close()
        return {"bytes": len(body), "elapsed_ms": elapsed_ms}

    def _raw_bulk(self, host: str, bytes_requested: int, no_delay: bool) -> dict[str, Any]:
        self._http_json(host, "POST", f"/bulk/config?bytes={bytes_requested}&nodelay={1 if no_delay else 0}")
        received = 0
        started = time.perf_counter()
        with socket.create_connection((host, RAW_BULK_PORT), timeout=8.0) as sock:
            sock.settimeout(12.0)
            while received < bytes_requested:
                chunk = sock.recv(min(65536, bytes_requested - received))
                if not chunk:
                    break
                received += len(chunk)
        return {"bytes": received, "elapsed_ms": (time.perf_counter() - started) * 1000.0}

    @staticmethod
    def _progress(callback: ProgressCallback | None, stage: str, name: str) -> None:
        if callback:
            callback(stage, name)

    def run(self, profile: dict[str, Any], progress: ProgressCallback | None = None) -> dict[str, Any]:
        started_ms = int(time.time() * 1000)
        host = str(profile.get("host") or "")
        source_id = str(profile.get("source_id") or "esp32_cam")
        saved_target = max(1, min(30, int(profile.get("target_fps") or 10)))
        target = max(3, min(15, saved_target))
        settings = profile.get("settings") if isinstance(profile.get("settings"), dict) else {}
        frame_size = str(settings.get("frame_size") or "QVGA")
        jpeg_quality = int(settings.get("jpeg_quality") or 24)
        requested_frames = 8
        rows: list[dict[str, Any]] = []
        errors: list[str] = []

        self._progress(progress, "R9 PREFLIGHT", "Probe architecture benchmark firmware")
        initial = self._http_json(host, "GET", "/status")
        firmware = str(initial.get("firmware") or "")
        if not firmware.startswith(R9_FIRMWARE_PREFIX):
            raise RuntimeError(f"R9 architecture firmware required, got {firmware or 'unknown firmware'}")
        self._http_json(host, "POST", f"/config?frame_size={frame_size}&jpeg_quality={jpeg_quality}")
        self._http_json(host, "POST", "/cache/stop")

        def add_stream(key: str, name: str, transport: str, port: int, path: str, detail: str) -> None:
            try:
                result = self._mjpeg(host, port, path)
                rows.append(_transport_row(key, name, transport, requested_frames, result["frames"], result["bytes"], result["elapsed_ms"], detail))
            except Exception as exc:
                errors.append(f"{name}: {exc}")
                rows.append(_transport_row(key, name, transport, requested_frames, 0, 0, None, str(exc)))

        self._progress(progress, "R9 SERVER A/B", "Manual WiFiClient MJPEG")
        self._http_json(host, "POST", f"/manual/config?frames={requested_frames}&fps={target}")
        add_stream(
            "r9_manual_mjpeg", "Manual WiFiClient MJPEG", "WiFiServer/WiFiClient + multipart MJPEG",
            MANUAL_MJPEG_PORT, "/stream", "Current/R5-style manual Arduino stream writer.",
        )

        self._progress(progress, "R9 SERVER A/B", "Old-style esp_http_server direct MJPEG")
        add_stream(
            "r9_httpd_direct_mjpeg", "Old-style esp_http_server direct MJPEG", "esp_http_server/httpd_resp_send_chunk",
            HTTPD_PORT, f"/direct.mjpeg?frames={requested_frames}&fps={target}", "V035-style direct capture then HTTPD chunk send.",
        )

        self._progress(progress, "R9 PRODUCER/CONSUMER", "Pi-style latest-frame cache + esp_http_server")
        try:
            self._http_json(host, "POST", f"/cache/start?fps={max(target, 15)}")
            time.sleep(0.25)
            add_stream(
                "r9_httpd_cached_mjpeg", "Pi-style cached latest-frame MJPEG", "FreeRTOS producer cache + esp_http_server",
                HTTPD_PORT, f"/cached.mjpeg?frames={requested_frames}&fps={target}",
                "Capture runs independently; sender transmits only the newest cached JPEG and may skip stale frames.",
            )
        finally:
            try:
                self._http_json(host, "POST", "/cache/stop")
            except Exception as exc:
                errors.append(f"cache stop: {exc}")

        self._progress(progress, "R9 CAMERA-FREE CONTROL", "esp_http_server bulk TCP")
        try:
            result = self._httpd_bulk(host, BULK_BYTES)
            mbps = result["bytes"] * 8.0 / result["elapsed_ms"] / 1000.0 if result["elapsed_ms"] > 0 else 0.0
            rows.append(_transport_row(
                "r9_httpd_bulk", "esp_http_server camera-free bulk", "esp_http_server synthetic binary",
                1, int(result["bytes"] >= BULK_BYTES), result["bytes"], result["elapsed_ms"],
                "No OV2640 capture or JPEG framebuffer participates.",
                telemetry={"throughput_mbps": round(mbps, 3), "requested_bytes": BULK_BYTES},
            ))
        except Exception as exc:
            errors.append(f"HTTPD bulk: {exc}")
            rows.append(_transport_row("r9_httpd_bulk", "esp_http_server camera-free bulk", "esp_http_server synthetic binary", 1, 0, 0, None, str(exc), telemetry={"throughput_mbps": 0.0}))

        for no_delay, key, label in (
            (True, "r9_raw_bulk_nodelay", "Raw WiFiClient bulk / TCP_NODELAY on"),
            (False, "r9_raw_bulk_nagle", "Raw WiFiClient bulk / Nagle on"),
        ):
            self._progress(progress, "R9 CAMERA-FREE CONTROL", label)
            try:
                result = self._raw_bulk(host, BULK_BYTES, no_delay)
                mbps = result["bytes"] * 8.0 / result["elapsed_ms"] / 1000.0 if result["elapsed_ms"] > 0 else 0.0
                rows.append(_transport_row(
                    key, label, "WiFiServer/WiFiClient synthetic binary",
                    1, int(result["bytes"] >= BULK_BYTES), result["bytes"], result["elapsed_ms"],
                    "Camera-free raw Arduino TCP sender.",
                    telemetry={"throughput_mbps": round(mbps, 3), "requested_bytes": BULK_BYTES, "tcp_nodelay": no_delay},
                ))
            except Exception as exc:
                errors.append(f"{label}: {exc}")
                rows.append(_transport_row(key, label, "WiFiServer/WiFiClient synthetic binary", 1, 0, 0, None, str(exc), telemetry={"throughput_mbps": 0.0, "tcp_nodelay": no_delay}))

        self._progress(progress, "R9 ANALYSIS", "Classify architecture and network bottleneck")
        final_status = self._http_json(host, "GET", "/status")
        analysis = analyze_architecture_results(rows, final_status, target)
        best_fps = _number(analysis["best_camera_fps"])
        target_ratio = best_fps / target if target else 0.0
        stability_grade = "stable" if target_ratio >= 0.70 else "degraded" if best_fps > 0 else "unstable"
        stability_score = round(min(100.0, max(0.0, target_ratio * 100.0)), 1)
        passed_rows = sum(row.get("status") == "PASS" for row in rows)
        functionality_score = round(100.0 * passed_rows / len(rows), 1) if rows else 0.0
        overall = "healthy" if target_ratio >= 0.70 else "warning" if best_fps > 0 else "failed"
        recommendation = str(analysis["next_action"])
        run_id = f"cam-arch-{uuid.uuid4().hex[:10]}"

        phase = {
            "target_fps": target,
            "duration_seconds": None,
            "frames": max((int(row.get("frames") or 0) for row in rows[:3]), default=0),
            "bytes_received": max((int(row.get("bytes_received") or 0) for row in rows[:3]), default=0),
            "throughput_mbps": 0.0,
            "measured_fps": best_fps,
            "fps_ratio": round(target_ratio, 3),
            "connections": 3,
            "disconnects": 0,
            "sequence_gaps": 0,
            "bad_frames": 0,
            "errors": errors,
        }
        checks = []
        for check_id, label, key in (
            ("manual_sender", "Manual WiFiClient MJPEG", "r9_manual_mjpeg"),
            ("httpd_direct", "Old-style esp_http_server MJPEG", "r9_httpd_direct_mjpeg"),
            ("cached_latest", "Pi-style latest-frame MJPEG", "r9_httpd_cached_mjpeg"),
            ("httpd_bulk", "Camera-free HTTPD bulk", "r9_httpd_bulk"),
            ("raw_bulk_nodelay", "Camera-free raw TCP / NODELAY", "r9_raw_bulk_nodelay"),
            ("raw_bulk_nagle", "Camera-free raw TCP / Nagle", "r9_raw_bulk_nagle"),
        ):
            row = _row(rows, key)
            checks.append({
                "id": f"r9.{check_id}", "category": "bottleneck", "label": label,
                "status": "pass" if row.get("status") == "PASS" else "fail",
                "detail": str(row.get("detail") or ""),
                "metrics": {"fps": row.get("measured_fps"), **(row.get("telemetry") or {})},
            })
        checks.append({
            "id": "r9.power_reset", "category": "stability", "label": "ESP reset / brownout evidence",
            "status": "warn" if analysis["power_evidence"] == "brownout_detected" else "pass",
            "detail": f"Reset reason: {analysis['reset_reason']}", "metrics": {"reset_reason": analysis["reset_reason"]},
        })

        metrics = {
            "control_successes": 1, "control_failures": 0, "control_avg_ms": None, "control_p50_ms": None,
            "control_p95_ms": None, "control_max_ms": None, "control_jitter_ms": None,
            "rssi_avg": analysis["rssi"], "rssi_min": analysis["rssi"], "rssi_max": analysis["rssi"],
            "wifi_bssid": final_status.get("bssid"), "wifi_channel": final_status.get("channel"),
            "direct_clean_frames": int(_row(rows, "r9_httpd_direct_mjpeg").get("frames") or 0),
            "direct_clean_fps": analysis["httpd_direct_mjpeg_fps"], "direct_clean_disconnects": 0, "direct_clean_bad_frames": 0,
            "direct_polled_frames": 0, "direct_polled_fps": 0.0, "direct_polled_disconnects": 0, "direct_polled_bad_frames": 0,
            "status_poll_failures": 0, "managed_frames": 0, "managed_fps": 0.0, "managed_failed_fetches": 0,
            "managed_reconnects": 0, "managed_session_recoveries": 0, "device_send_failures_delta": 0,
            "device_deadline_drops_delta": 0, "phase_boundary_send_resets": 0, "last_send_errno": None,
            "last_send_accepted_bytes": None, "last_frame_bytes": final_status.get("httpd_direct_last_bytes"),
            "send_ewma_ms": final_status.get("httpd_direct_last_send_ms"), "wifi_disconnects": None, "wifi_reconnects": None,
            "functionality_score": functionality_score, "stability_score": stability_score, "stability_grade": stability_grade,
            "peak_measured_fps": best_fps, "peak_throughput_mbps": analysis["best_bulk_mbps"],
            "estimated_sustainable_target_fps": target if target_ratio >= 0.70 else 0,
            "stability_target_fps": target, "stability_measured_fps": best_fps, "stability_interval_p95_ms": None,
            "stability_interval_max_ms": None, "stability_jitter_ms": None, "stability_stall_intervals": 0,
            "stability_disconnects": 0, "stability_sequence_gaps": 0, "stability_bad_frames": 0,
        }
        findings = [
            {
                "id": f"r9-finding-{index + 1}", "layer": "camera transport",
                "severity": "warning" if index == 0 else "info", "title": finding, "evidence": finding,
                "impact": "May limit fresh-frame delivery to PC Studio.", "recommendation": recommendation,
            }
            for index, finding in enumerate(analysis["findings"])
        ]
        managed_phase = {
            "target_fps": target, "duration_seconds": 0, "frames": 0, "failed_fetches": 0, "reconnects": 0,
            "session_recoveries": 0, "measured_fps": 0.0, "throughput_mbps": 0.0, "fps_ratio": 0.0,
            "error": "R9 firmware is diagnostic-only; the production managed worker is intentionally skipped.",
        }
        transport_benchmark = {
            "schema_version": 2,
            "benchmark_revision": "R9 architecture",
            "firmware": firmware,
            "host": host,
            "environment_label": "selected-camera-network",
            "settings": {"frame_size": frame_size, "jpeg_quality": jpeg_quality, "fps": target},
            "diagnosis": {
                "diagnosis_code": analysis["classification"],
                "likely_bottleneck": ", ".join(analysis["likely_layers"]) or analysis["classification"],
                "recommended_key": analysis["recommended_key"],
                "recommendation": recommendation,
                "ranking": [],
            },
            "analysis_evidence": {"architecture_analysis": analysis},
            "results": rows,
            "architecture_analysis": analysis,
        }
        return {
            "run_id": run_id, "started_at_ms": started_ms, "duration_ms": int(time.time() * 1000) - started_ms,
            "source_id": source_id, "host": host, "overall": overall, "diagnosis_code": analysis["classification"],
            "title": "R9 camera architecture bottleneck isolation",
            "summary": f"Best camera path reached {best_fps:.2f}/{target} FPS; camera-free TCP peaked at {analysis['best_bulk_mbps']:.2f} Mbit/s. Classification: {analysis['classification'].replace('_', ' ')}.",
            "confidence": analysis["confidence"],
            "likely_causes": analysis["likely_layers"] or [analysis["classification"].replace("_", " ")],
            "recommendations": [recommendation], "checks": checks, "metrics": metrics,
            "functionality": {"score": functionality_score, "passed": passed_rows, "total": len(rows), "config_roundtrip": True, "session_lifecycle": True},
            "stability": {"grade": stability_grade, "score": stability_score, "phase": phase},
            "bottleneck_analysis": {
                "primary_bottleneck": analysis["classification"], "findings": findings,
                "estimated_sustainable_target_fps": target if target_ratio >= 0.70 else 0,
                "peak_measured_fps": best_fps, "peak_throughput_mbps": analysis["best_bulk_mbps"],
                "stability_grade": stability_grade, "stability_score": stability_score, "saved_target_fps": saved_target,
            },
            "candidate_isolation": {"supported": True, "primary_candidate": analysis["classification"], "findings": [], "ruled_out": [], "matrix": {}},
            "candidate_phases": {row["key"]: row for row in rows}, "load_ladder": [], "contention_phase": phase,
            "managed_phase": managed_phase, "device": final_status,
            "state_restored": not bool(final_status.get("cache_active")),
            "restore_error": None if not final_status.get("cache_active") else "cache producer remained active",
            "diagnostic_target_fps": target, "diagnostic_load_targets": [target], "prototype_only": True,
            "pipeline_timing": None, "architecture_analysis": analysis, "transport_benchmark": transport_benchmark,
        }


camera_architecture_diagnostic_service = CameraArchitectureDiagnosticService()
