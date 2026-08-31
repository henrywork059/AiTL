from __future__ import annotations

import socket
import statistics
import time
from typing import Any

from app.services.camera_architecture_diagnostics import (
    HTTPD_PORT,
    RAW_BULK_PORT,
    CameraArchitectureDiagnosticService,
    _transport_row,
)

R10_TUNING_REVISION = "R10"
FPS_TARGETS = (3, 5, 10, 15)
FB_CONFIGS = ((1, "when_empty"), (1, "latest"), (2, "when_empty"), (2, "latest"))
QUALITY_VALUES = (18, 24, 30, 36)
CHUNK_VALUES = (1460, 2920, 5840, 11680)
TRANSFER_SIZES = (32 * 1024, 128 * 1024, 512 * 1024)
STREAM_FRAMES = 6
QUALITY_TARGET_FPS = 10
BULK_SWEEP_BYTES = 128 * 1024
REPEAT_RUNS = 3


def _number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _fps(row: dict[str, Any]) -> float:
    return _number(row.get("measured_fps"))


def _mbps(row: dict[str, Any]) -> float:
    telemetry = row.get("telemetry") if isinstance(row.get("telemetry"), dict) else {}
    return _number(telemetry.get("throughput_mbps"))


def _sustainable_target(rows: list[dict[str, Any]]) -> int:
    sustainable = 0
    for row in rows:
        telemetry = row.get("telemetry") if isinstance(row.get("telemetry"), dict) else {}
        target = int(_number(telemetry.get("target_fps")))
        if row.get("status") == "PASS" and target > 0 and _fps(row) >= target * 0.70:
            sustainable = max(sustainable, target)
    return sustainable


def _fb_group(rows: list[dict[str, Any]], fb_count: int, grab_mode: str) -> list[dict[str, Any]]:
    return [
        row
        for row in rows
        if (row.get("telemetry") or {}).get("experiment") == "fb_fps"
        and int(_number((row.get("telemetry") or {}).get("fb_count"))) == fb_count
        and (row.get("telemetry") or {}).get("grab_mode") == grab_mode
    ]


def choose_best_fb_config(rows: list[dict[str, Any]]) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []
    for fb_count, grab_mode in FB_CONFIGS:
        group = _fb_group(rows, fb_count, grab_mode)
        if not group:
            continue
        sustainable = _sustainable_target(group)
        peak = max((_fps(row) for row in group), default=0.0)
        ratios: list[float] = []
        for row in group:
            target = _number((row.get("telemetry") or {}).get("target_fps"))
            if target > 0:
                ratios.append(min(1.25, _fps(row) / target))
        score = sustainable * 100.0 + (statistics.mean(ratios) if ratios else 0.0) * 10.0 + peak
        candidates.append(
            {
                "fb_count": fb_count,
                "grab_mode": grab_mode,
                "sustainable_fps": sustainable,
                "peak_fps": round(peak, 3),
                "score": round(score, 3),
            }
        )
    if not candidates:
        return {"fb_count": 2, "grab_mode": "latest", "sustainable_fps": 0, "peak_fps": 0.0, "score": 0.0}
    return max(
        candidates,
        key=lambda item: (
            item["sustainable_fps"],
            item["score"],
            item["peak_fps"],
            item["fb_count"],
            item["grab_mode"] == "latest",
        ),
    )


def analyze_tuning_results(
    rows: list[dict[str, Any]],
    *,
    original_quality: int,
    saved_target_fps: int,
    status: dict[str, Any],
) -> dict[str, Any]:
    best_fb = choose_best_fb_config(rows)
    baseline_group = _fb_group(rows, 2, "latest")
    best_group = _fb_group(rows, int(best_fb["fb_count"]), str(best_fb["grab_mode"]))
    baseline_sustainable = _sustainable_target(baseline_group)
    fb_gain = best_fb["sustainable_fps"] / baseline_sustainable if baseline_sustainable > 0 else None

    direct_by_target = {
        int(_number((row.get("telemetry") or {}).get("target_fps"))): _fps(row)
        for row in best_group
    }
    cached_rows = [row for row in rows if (row.get("telemetry") or {}).get("experiment") == "cached_fps"]
    cached_sustainable = _sustainable_target(cached_rows)
    direct_sustainable = int(best_fb["sustainable_fps"])
    cached_gains: list[float] = []
    for row in cached_rows:
        target = int(_number((row.get("telemetry") or {}).get("target_fps")))
        direct = direct_by_target.get(target, 0.0)
        if direct > 0:
            cached_gains.append(_fps(row) / direct)
    median_cached_gain = statistics.median(cached_gains) if cached_gains else 1.0
    architecture = (
        "cached_latest_frame"
        if cached_sustainable > direct_sustainable
        or (cached_sustainable == direct_sustainable and median_cached_gain >= 1.05)
        else "direct_httpd"
    )
    sustainable_fps = max(direct_sustainable, cached_sustainable)

    quality_rows = [
        row
        for row in rows
        if (row.get("telemetry") or {}).get("experiment") == "jpeg_quality" and row.get("status") == "PASS"
    ]
    eligible_quality = [row for row in quality_rows if _fps(row) >= QUALITY_TARGET_FPS * 0.70]
    if eligible_quality:
        # esp32-camera uses lower numeric quality values for higher JPEG quality.
        quality_row = min(
            eligible_quality,
            key=lambda row: int(_number((row.get("telemetry") or {}).get("jpeg_quality"), 99)),
        )
    elif quality_rows:
        quality_row = max(quality_rows, key=_fps)
    else:
        quality_row = {}
    recommended_quality = int(
        _number((quality_row.get("telemetry") or {}).get("jpeg_quality"), original_quality)
    )

    chunk_rows = [row for row in rows if (row.get("telemetry") or {}).get("experiment") == "chunk_sweep"]
    best_chunk_row = max(chunk_rows, key=_mbps, default={})
    best_chunk = int(_number((best_chunk_row.get("telemetry") or {}).get("chunk_bytes"), 1460))
    best_chunk_mbps = _mbps(best_chunk_row)
    baseline_chunk = _mbps(
        next(
            (
                row
                for row in chunk_rows
                if int(_number((row.get("telemetry") or {}).get("chunk_bytes"))) == 1460
            ),
            {},
        )
    )
    chunk_gain = best_chunk_mbps / baseline_chunk if baseline_chunk > 0 else None

    transfer_rows = [row for row in rows if (row.get("telemetry") or {}).get("experiment") == "transfer_size"]
    transfer_points = [
        {
            "bytes": int(_number((row.get("telemetry") or {}).get("requested_bytes"))),
            "mbps": round(_mbps(row), 3),
        }
        for row in transfer_rows
    ]
    small = next((point["mbps"] for point in transfer_points if point["bytes"] == 32 * 1024), 0.0)
    large = next((point["mbps"] for point in transfer_points if point["bytes"] == 512 * 1024), 0.0)
    size_scaling_ratio = large / small if small > 0 else None

    repeat_rows = [row for row in rows if (row.get("telemetry") or {}).get("experiment") == "repeatability"]
    repeat_mbps = [_mbps(row) for row in repeat_rows if _mbps(row) > 0]
    repeat_mean = statistics.mean(repeat_mbps) if repeat_mbps else 0.0
    repeat_spread = (
        (max(repeat_mbps) - min(repeat_mbps)) / repeat_mean
        if len(repeat_mbps) >= 2 and repeat_mean > 0
        else 0.0
    )

    bulk_rows = chunk_rows + transfer_rows + repeat_rows
    best_bulk = max((_mbps(row) for row in bulk_rows), default=0.0)
    network_headroom = (
        "ample"
        if best_bulk >= 5.0
        else "constrained"
        if best_bulk >= 1.0
        else "severely_constrained"
        if best_bulk > 0
        else "unknown"
    )
    default_best = best_fb["fb_count"] == 2 and best_fb["grab_mode"] == "latest"
    fb_sensitive = not default_best and (
        best_fb["sustainable_fps"] > baseline_sustainable or (fb_gain is not None and fb_gain >= 1.25)
    )
    chunk_sensitive = chunk_gain is not None and chunk_gain >= 1.25
    cache_sensitive = median_cached_gain >= 1.25 or cached_sustainable > direct_sustainable
    variable_network = repeat_spread >= 0.25

    if best_bulk > 0 and best_bulk < 1.0:
        classification, confidence = "network_limited_after_tuning", "high"
    elif fb_sensitive:
        classification, confidence = "framebuffer_configuration_sensitive", "high"
    elif cache_sensitive:
        classification, confidence = "capture_send_coupling", "high"
    elif chunk_sensitive:
        classification, confidence = "tcp_write_batching_sensitive", "high"
    else:
        classification, confidence = "tuning_profile_identified", "medium"

    findings = [
        f"Best framebuffer mode: fb_count={best_fb['fb_count']}, grab={best_fb['grab_mode']}; direct HTTPD sustainable target {best_fb['sustainable_fps']} FPS.",
        f"Newest-frame cached architecture sustainable target {cached_sustainable} FPS; median matched-target gain versus direct was {median_cached_gain:.2f}x.",
        f"Best camera-free raw TCP write size was {best_chunk} B at {best_chunk_mbps:.2f} Mbit/s"
        + (f" ({chunk_gain:.2f}x versus 1460 B)." if chunk_gain is not None else "."),
        f"Best tested JPEG quality setting was {recommended_quality}; lower numeric values are higher JPEG quality. This is a diagnostic recommendation only.",
        f"Raw-path repeatability spread was {repeat_spread * 100:.0f}%."
        + (" RF/AP/network variability remains material." if variable_network else ""),
    ]
    if size_scaling_ratio is not None:
        findings.insert(
            3,
            f"512 KiB versus 32 KiB transfer throughput ratio was {size_scaling_ratio:.2f}x; values well above 1 indicate material fixed connection/startup overhead.",
        )
    rssi = _number(status.get("rssi"), -127.0)
    if rssi > -120:
        findings.append(f"Final diagnostic RSSI was {rssi:.0f} dBm.")

    recommended = {
        "fb_count": int(best_fb["fb_count"]),
        "grab_mode": str(best_fb["grab_mode"]),
        "architecture": architecture,
        "jpeg_quality": recommended_quality,
        "sustainable_target_fps": int(sustainable_fps),
        "raw_tcp_chunk_bytes": best_chunk,
        "saved_target_fps": int(saved_target_fps),
    }
    next_actions = {
        "network_limited_after_tuning": "Keep the best framebuffer/cache settings, but treat RF/AP placement as the first limiter. Re-run R10 at the intended model-camera position and on an alternate hotspot before changing production transport.",
        "framebuffer_configuration_sensitive": "Prototype the winning framebuffer/grab configuration in normal AiTL firmware, then validate the same FPS ladder before adopting it.",
        "capture_send_coupling": "Prototype the newest-frame producer/consumer architecture so capture can continue while the network sender skips stale frames.",
        "tcp_write_batching_sensitive": "Prototype the winning TCP write size in the production sender and re-run the camera and bulk ladders to verify the gain survives real JPEG traffic.",
        "tuning_profile_identified": "Use the recommended profile as the next production prototype, then validate 10–15 FPS at the intended physical camera position.",
    }
    return {
        "classification": classification,
        "confidence": confidence,
        "best_fb": best_fb,
        "baseline_fb2_latest_sustainable_fps": baseline_sustainable,
        "fb_sustainable_gain": round(fb_gain, 3) if fb_gain is not None else None,
        "direct_sustainable_fps": direct_sustainable,
        "cached_sustainable_fps": cached_sustainable,
        "cached_median_gain": round(median_cached_gain, 3),
        "recommended_architecture": architecture,
        "recommended_jpeg_quality": recommended_quality,
        "best_chunk_bytes": best_chunk,
        "best_chunk_mbps": round(best_chunk_mbps, 3),
        "chunk_gain_vs_1460": round(chunk_gain, 3) if chunk_gain is not None else None,
        "transfer_size_points": transfer_points,
        "transfer_size_scaling_ratio": round(size_scaling_ratio, 3) if size_scaling_ratio is not None else None,
        "repeatability_mbps": [round(value, 3) for value in repeat_mbps],
        "repeatability_spread_ratio": round(repeat_spread, 3),
        "network_variability": variable_network,
        "best_bulk_mbps": round(best_bulk, 3),
        "network_headroom": network_headroom,
        "rssi": rssi,
        "recommended_profile": recommended,
        "findings": findings,
        "next_action": next_actions[classification],
    }


class CameraTuningDiagnosticService(CameraArchitectureDiagnosticService):
    """R10 diagnostic-only tuning sweep for framebuffer, FPS and transport parameters."""

    def _raw_bulk_tuned(
        self,
        host: str,
        *,
        bytes_requested: int,
        chunk_bytes: int,
        no_delay: bool = True,
    ) -> dict[str, Any]:
        self._http_json(
            host,
            "POST",
            f"/bulk/config?bytes={bytes_requested}&chunk={chunk_bytes}&nodelay={1 if no_delay else 0}",
        )
        received = 0
        started = time.perf_counter()
        with socket.create_connection((host, RAW_BULK_PORT), timeout=8.0) as sock:
            # The 512 KiB scaling point is intentionally allowed to complete on
            # a severely constrained RF path instead of being misclassified as
            # a socket failure after the shorter R9 timeout.
            sock.settimeout(60.0)
            while received < bytes_requested:
                chunk = sock.recv(min(65536, bytes_requested - received))
                if not chunk:
                    break
                received += len(chunk)
        return {"bytes": received, "elapsed_ms": (time.perf_counter() - started) * 1000.0}

    def _stream(
        self,
        host: str,
        *,
        architecture: str,
        target_fps: int,
        frames: int = STREAM_FRAMES,
    ) -> dict[str, Any]:
        if architecture == "cached_latest_frame":
            producer_fps = min(30, max(20, target_fps))
            self._http_json(host, "POST", f"/cache/start?fps={producer_fps}")
            time.sleep(0.20)
            try:
                result = self._mjpeg(
                    host,
                    HTTPD_PORT,
                    f"/cached.mjpeg?frames={frames}&fps={target_fps}",
                )
            finally:
                self._http_json(host, "POST", "/cache/stop")
        else:
            result = self._mjpeg(
                host,
                HTTPD_PORT,
                f"/direct.mjpeg?frames={frames}&fps={target_fps}",
            )
        result["requested"] = frames
        return result

    @staticmethod
    def _stream_row(
        key: str,
        name: str,
        result: dict[str, Any],
        *,
        target_fps: int,
        telemetry: dict[str, Any],
    ) -> dict[str, Any]:
        requested = int(result.get("requested") or STREAM_FRAMES)
        frames = int(result.get("frames") or 0)
        payload_bytes = int(result.get("bytes") or 0)
        elapsed_ms = _number(result.get("elapsed_ms"))
        data = {
            **telemetry,
            "target_fps": target_fps,
            "payload_avg_bytes": round(payload_bytes / frames) if frames else 0,
            "rate_basis": "completed_frame_intervals",
        }
        row = _transport_row(
            key,
            name,
            str(telemetry.get("transport") or "esp_http_server MJPEG"),
            requested,
            frames,
            payload_bytes,
            elapsed_ms,
            f"{frames}/{requested} valid JPEG frames at {target_fps} FPS target.",
            telemetry=data,
        )
        # For a finite paced stream, the first frame can be emitted immediately.
        # frames/elapsed therefore overstates the true cadence, especially for
        # short 3 FPS tests. Use completed inter-frame periods for R10 tuning.
        if frames >= 2 and elapsed_ms > 0:
            row["measured_fps"] = round(1000.0 * (frames - 1) / elapsed_ms, 3)
        return row

    def _bulk_row(
        self,
        host: str,
        *,
        key: str,
        name: str,
        bytes_requested: int,
        chunk_bytes: int,
        experiment: str,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        result = self._raw_bulk_tuned(
            host,
            bytes_requested=bytes_requested,
            chunk_bytes=chunk_bytes,
            no_delay=True,
        )
        received = int(result["bytes"])
        elapsed_ms = _number(result["elapsed_ms"])
        mbps = received * 8.0 / elapsed_ms / 1000.0 if elapsed_ms > 0 else 0.0
        telemetry = {
            "experiment": experiment,
            "throughput_mbps": round(mbps, 3),
            "requested_bytes": bytes_requested,
            "chunk_bytes": chunk_bytes,
            "tcp_nodelay": True,
            **(extra or {}),
        }
        return _transport_row(
            key,
            name,
            "WiFiServer/WiFiClient synthetic TCP",
            1,
            1 if received >= bytes_requested else 0,
            received,
            elapsed_ms,
            f"{received}/{bytes_requested} synthetic bytes received with {chunk_bytes} B writes.",
            telemetry=telemetry,
        )

    def run(self, profile: dict[str, Any], progress=None) -> dict[str, Any]:
        started_ms = int(time.time() * 1000)
        host = str(profile.get("host") or "")
        source_id = str(profile.get("source_id") or "esp32_cam")
        saved_target = max(1, min(30, int(profile.get("target_fps") or 10)))
        saved_settings = profile.get("settings") if isinstance(profile.get("settings"), dict) else {}
        initial = self._http_json(host, "GET", "/status")
        if str(initial.get("tuning_revision") or "") != R10_TUNING_REVISION:
            raise RuntimeError("R10 tuning firmware is required.")

        original_fb = int(_number(initial.get("camera_fb_count"), 2))
        original_grab = str(initial.get("camera_grab_mode") or "latest")
        original_frame = str(initial.get("frame_size") or saved_settings.get("frame_size") or "QVGA")
        original_quality = int(_number(initial.get("jpeg_quality"), saved_settings.get("jpeg_quality", 24)))
        rows: list[dict[str, Any]] = []
        errors: list[str] = []
        restore_errors: list[str] = []
        fatal_error: Exception | None = None

        def step(stage: str, test: str) -> None:
            if progress:
                progress(stage, test)

        def record_error(key: str, name: str, experiment: str, exc: Exception, **telemetry: Any) -> None:
            errors.append(f"{name}: {type(exc).__name__}: {exc}")
            rows.append(
                _transport_row(
                    key,
                    name,
                    "R10 diagnostic",
                    STREAM_FRAMES,
                    0,
                    0,
                    None,
                    f"{type(exc).__name__}: {exc}",
                    telemetry={"experiment": experiment, **telemetry},
                )
            )

        try:
            self._http_json(
                host,
                "POST",
                f"/config?frame_size={original_frame}&jpeg_quality={original_quality}",
            )

            for fb_count, grab_mode in FB_CONFIGS:
                step("R10 FB/FPS", f"Reinitialize camera: FB {fb_count} / {grab_mode}")
                try:
                    mode_status = self._http_json(
                        host,
                        "POST",
                        f"/camera/reinit?fb_count={fb_count}&grab={grab_mode}",
                        timeout=10.0,
                    )
                except Exception as exc:
                    for target in FPS_TARGETS:
                        record_error(
                            f"r10_fb{fb_count}_{grab_mode}_{target}",
                            f"FB {fb_count} / {grab_mode} @ {target} FPS",
                            "fb_fps",
                            exc,
                            fb_count=fb_count,
                            grab_mode=grab_mode,
                            target_fps=target,
                        )
                    continue

                actual_fb = int(_number(mode_status.get("camera_fb_count"), fb_count))
                actual_grab = str(mode_status.get("camera_grab_mode") or grab_mode)
                for target in FPS_TARGETS:
                    step("R10 FB/FPS", f"FB {fb_count} / {grab_mode} @ {target} FPS")
                    key = f"r10_fb{fb_count}_{grab_mode}_{target}"
                    name = f"FB {fb_count} / {grab_mode} @ {target} FPS"
                    try:
                        result = self._stream(host, architecture="direct_httpd", target_fps=target)
                        rows.append(
                            self._stream_row(
                                key,
                                name,
                                result,
                                target_fps=target,
                                telemetry={
                                    "experiment": "fb_fps",
                                    "fb_count": actual_fb,
                                    "grab_mode": actual_grab,
                                    "requested_fb_count": fb_count,
                                    "requested_grab_mode": grab_mode,
                                    "architecture": "direct_httpd",
                                    "transport": "esp_http_server direct MJPEG",
                                },
                            )
                        )
                    except Exception as exc:
                        record_error(
                            key,
                            name,
                            "fb_fps",
                            exc,
                            fb_count=actual_fb,
                            grab_mode=actual_grab,
                            requested_fb_count=fb_count,
                            requested_grab_mode=grab_mode,
                            target_fps=target,
                        )

            best_fb = choose_best_fb_config(rows)
            step("R10 CACHE/FPS", f"Use best FB mode {best_fb['fb_count']} / {best_fb['grab_mode']}")
            self._http_json(
                host,
                "POST",
                f"/camera/reinit?fb_count={best_fb['fb_count']}&grab={best_fb['grab_mode']}",
                timeout=10.0,
            )
            for target in FPS_TARGETS:
                step("R10 CACHE/FPS", f"Newest-frame cache @ {target} FPS")
                key = f"r10_cached_{target}"
                name = f"Cached newest-frame @ {target} FPS"
                try:
                    result = self._stream(host, architecture="cached_latest_frame", target_fps=target)
                    rows.append(
                        self._stream_row(
                            key,
                            name,
                            result,
                            target_fps=target,
                            telemetry={
                                "experiment": "cached_fps",
                                "fb_count": int(best_fb["fb_count"]),
                                "grab_mode": str(best_fb["grab_mode"]),
                                "architecture": "cached_latest_frame",
                                "transport": "FreeRTOS latest-frame cache + esp_http_server",
                            },
                        )
                    )
                except Exception as exc:
                    record_error(
                        key,
                        name,
                        "cached_fps",
                        exc,
                        fb_count=int(best_fb["fb_count"]),
                        grab_mode=str(best_fb["grab_mode"]),
                        target_fps=target,
                    )

            interim = analyze_tuning_results(
                rows,
                original_quality=original_quality,
                saved_target_fps=saved_target,
                status=initial,
            )
            selected_arch = str(interim["recommended_architecture"])
            for quality in sorted(set((*QUALITY_VALUES, original_quality))):
                step("R10 JPEG PAYLOAD", f"JPEG quality {quality} @ {QUALITY_TARGET_FPS} FPS")
                key = f"r10_quality_{quality}"
                name = f"JPEG quality {quality} @ {QUALITY_TARGET_FPS} FPS"
                try:
                    self._http_json(host, "POST", f"/config?jpeg_quality={quality}")
                    result = self._stream(host, architecture=selected_arch, target_fps=QUALITY_TARGET_FPS)
                    rows.append(
                        self._stream_row(
                            key,
                            name,
                            result,
                            target_fps=QUALITY_TARGET_FPS,
                            telemetry={
                                "experiment": "jpeg_quality",
                                "jpeg_quality": quality,
                                "fb_count": int(best_fb["fb_count"]),
                                "grab_mode": str(best_fb["grab_mode"]),
                                "architecture": selected_arch,
                                "transport": selected_arch,
                            },
                        )
                    )
                except Exception as exc:
                    record_error(
                        key,
                        name,
                        "jpeg_quality",
                        exc,
                        jpeg_quality=quality,
                        target_fps=QUALITY_TARGET_FPS,
                    )
            self._http_json(host, "POST", f"/config?jpeg_quality={original_quality}")

            for chunk in CHUNK_VALUES:
                step("R10 TCP BATCHING", f"Raw TCP write size {chunk} B")
                try:
                    rows.append(
                        self._bulk_row(
                            host,
                            key=f"r10_chunk_{chunk}",
                            name=f"Raw TCP chunk {chunk} B",
                            bytes_requested=BULK_SWEEP_BYTES,
                            chunk_bytes=chunk,
                            experiment="chunk_sweep",
                        )
                    )
                except Exception as exc:
                    record_error(
                        f"r10_chunk_{chunk}",
                        f"Raw TCP chunk {chunk} B",
                        "chunk_sweep",
                        exc,
                        chunk_bytes=chunk,
                    )

            chunk_analysis = analyze_tuning_results(
                rows,
                original_quality=original_quality,
                saved_target_fps=saved_target,
                status=initial,
            )
            best_chunk = int(chunk_analysis["best_chunk_bytes"])
            for size in TRANSFER_SIZES:
                step("R10 TRANSFER SIZE", f"Raw TCP {size // 1024} KiB @ {best_chunk} B writes")
                try:
                    rows.append(
                        self._bulk_row(
                            host,
                            key=f"r10_size_{size}",
                            name=f"Raw TCP {size // 1024} KiB",
                            bytes_requested=size,
                            chunk_bytes=best_chunk,
                            experiment="transfer_size",
                        )
                    )
                except Exception as exc:
                    record_error(
                        f"r10_size_{size}",
                        f"Raw TCP {size // 1024} KiB",
                        "transfer_size",
                        exc,
                        requested_bytes=size,
                        chunk_bytes=best_chunk,
                    )

            for repeat in range(1, REPEAT_RUNS + 1):
                step("R10 REPEATABILITY", f"Best raw TCP repeat {repeat}/{REPEAT_RUNS}")
                try:
                    rows.append(
                        self._bulk_row(
                            host,
                            key=f"r10_repeat_{repeat}",
                            name=f"Best raw TCP repeat {repeat}",
                            bytes_requested=BULK_SWEEP_BYTES,
                            chunk_bytes=best_chunk,
                            experiment="repeatability",
                            extra={"repeat_index": repeat},
                        )
                    )
                except Exception as exc:
                    record_error(
                        f"r10_repeat_{repeat}",
                        f"Best raw TCP repeat {repeat}",
                        "repeatability",
                        exc,
                        repeat_index=repeat,
                        chunk_bytes=best_chunk,
                    )
        except Exception as exc:
            fatal_error = exc
        finally:
            step("R10 RESTORE", "Restore original camera settings and framebuffer mode")
            for label, method, path in (
                ("cache stop", "POST", "/cache/stop"),
                ("camera mode", "POST", f"/camera/reinit?fb_count={original_fb}&grab={original_grab}"),
                ("image settings", "POST", f"/config?frame_size={original_frame}&jpeg_quality={original_quality}"),
            ):
                try:
                    self._http_json(host, method, path, timeout=10.0)
                except Exception as exc:
                    restore_errors.append(f"{label}: {exc}")

        final_status: dict[str, Any] = {}
        try:
            final_status = self._http_json(host, "GET", "/status")
        except Exception as exc:
            restore_errors.append(f"final status: {exc}")

        state_restored = bool(
            final_status
            and not restore_errors
            and int(_number(final_status.get("camera_fb_count"), -1)) == original_fb
            and str(final_status.get("camera_grab_mode") or "") == original_grab
            and str(final_status.get("frame_size") or "") == original_frame
            and int(_number(final_status.get("jpeg_quality"), -1)) == original_quality
            and not bool(final_status.get("cache_active"))
        )
        if final_status and not state_restored and not restore_errors:
            restore_errors.append("final ESP status did not exactly match the pre-test camera state")

        if fatal_error is not None:
            if restore_errors:
                raise RuntimeError(
                    f"R10 tuning failed ({type(fatal_error).__name__}: {fatal_error}); restore also failed: {'; '.join(restore_errors)}"
                ) from fatal_error
            raise fatal_error

        analysis = analyze_tuning_results(
            rows,
            original_quality=original_quality,
            saved_target_fps=saved_target,
            status=final_status or initial,
        )
        recommendation = str(analysis["next_action"])
        camera_rows = [
            row
            for row in rows
            if (row.get("telemetry") or {}).get("experiment") in {"fb_fps", "cached_fps", "jpeg_quality"}
        ]
        best_camera_fps = max((_fps(row) for row in camera_rows), default=0.0)
        sustainable = int(analysis["recommended_profile"]["sustainable_target_fps"])
        stability_target = max(1, sustainable or min(saved_target, 15))
        stability_score = round(100.0 * min(1.0, best_camera_fps / stability_target), 1)
        stability_grade = (
            "stable"
            if sustainable >= min(saved_target, 15) and best_camera_fps > 0
            else "degraded"
            if best_camera_fps > 0
            else "unstable"
        )
        passed = sum(1 for row in rows if row.get("status") == "PASS")
        functionality_score = round(100.0 * passed / len(rows), 1) if rows else 0.0

        findings = [
            {
                "id": f"r10-finding-{index + 1}",
                "layer": "camera tuning",
                "severity": "warning" if index == 0 else "info",
                "title": finding,
                "evidence": finding,
                "impact": "Changes fresh-frame throughput or confidence in the selected tuning profile.",
                "recommendation": recommendation,
            }
            for index, finding in enumerate(analysis["findings"])
        ]
        checks = [
            {
                "id": "r10.fb_fps_matrix",
                "category": "bottleneck",
                "label": "Framebuffer / grab-mode / FPS matrix",
                "status": "pass"
                if any((row.get("telemetry") or {}).get("experiment") == "fb_fps" and row.get("status") == "PASS" for row in rows)
                else "fail",
                "detail": f"Best: FB {analysis['best_fb']['fb_count']} / {analysis['best_fb']['grab_mode']} / {analysis['best_fb']['sustainable_fps']} FPS sustainable target.",
                "metrics": analysis["best_fb"],
            },
            {
                "id": "r10.cached_architecture",
                "category": "bottleneck",
                "label": "Newest-frame producer/consumer FPS ladder",
                "status": "pass" if analysis["cached_sustainable_fps"] > 0 else "warn",
                "detail": f"Cached sustainable target: {analysis['cached_sustainable_fps']} FPS; median direct-matched gain {analysis['cached_median_gain']:.2f}x.",
                "metrics": {
                    "cached_sustainable_fps": analysis["cached_sustainable_fps"],
                    "gain": analysis["cached_median_gain"],
                },
            },
            {
                "id": "r10.jpeg_quality",
                "category": "bottleneck",
                "label": "JPEG quality / payload trade-off",
                "status": "pass"
                if any((row.get("telemetry") or {}).get("experiment") == "jpeg_quality" and row.get("status") == "PASS" for row in rows)
                else "warn",
                "detail": f"Recommended diagnostic JPEG quality: {analysis['recommended_jpeg_quality']}.",
                "metrics": {"jpeg_quality": analysis["recommended_jpeg_quality"]},
            },
            {
                "id": "r10.tcp_batching",
                "category": "bottleneck",
                "label": "Raw TCP write-size sweep",
                "status": "pass" if analysis["best_chunk_mbps"] > 0 else "fail",
                "detail": f"Best: {analysis['best_chunk_bytes']} B writes / {analysis['best_chunk_mbps']:.2f} Mbit/s.",
                "metrics": {
                    "chunk_bytes": analysis["best_chunk_bytes"],
                    "mbps": analysis["best_chunk_mbps"],
                    "gain": analysis["chunk_gain_vs_1460"],
                },
            },
            {
                "id": "r10.repeatability",
                "category": "stability",
                "label": "RF / AP / network repeatability",
                "status": "warn" if analysis["network_variability"] else "pass",
                "detail": f"Throughput spread: {analysis['repeatability_spread_ratio'] * 100:.0f}%.",
                "metrics": {
                    "samples_mbps": analysis["repeatability_mbps"],
                    "spread_ratio": analysis["repeatability_spread_ratio"],
                },
            },
            {
                "id": "r10.restore",
                "category": "functionality",
                "label": "Exact diagnostic camera-state restoration",
                "status": "pass" if state_restored else "fail",
                "detail": "Original FB/grab/frame-size/JPEG settings restored."
                if state_restored
                else "; ".join(restore_errors),
                "metrics": {
                    "original_fb": original_fb,
                    "original_grab": original_grab,
                    "original_frame": original_frame,
                    "original_quality": original_quality,
                },
            },
        ]

        selected_experiment = (
            "cached_fps" if analysis["recommended_architecture"] == "cached_latest_frame" else "fb_fps"
        )
        ladder: list[dict[str, Any]] = []
        for target in FPS_TARGETS:
            candidate = next(
                (
                    row
                    for row in rows
                    if (row.get("telemetry") or {}).get("experiment") == selected_experiment
                    and int(_number((row.get("telemetry") or {}).get("target_fps"))) == target
                    and (
                        selected_experiment == "cached_fps"
                        or (
                            int(_number((row.get("telemetry") or {}).get("fb_count")))
                            == int(analysis["best_fb"]["fb_count"])
                            and (row.get("telemetry") or {}).get("grab_mode")
                            == analysis["best_fb"]["grab_mode"]
                        )
                    )
                ),
                {},
            )
            if candidate:
                elapsed_ms = max(1.0, _number(candidate.get("elapsed_ms")))
                ladder.append(
                    {
                        "target_fps": target,
                        "duration_seconds": round(elapsed_ms / 1000.0, 2),
                        "frames": int(candidate.get("frames") or 0),
                        "bytes_received": int(candidate.get("bytes_received") or 0),
                        "throughput_mbps": round(
                            int(candidate.get("bytes_received") or 0) * 8.0 / elapsed_ms / 1000.0,
                            3,
                        ),
                        "measured_fps": _fps(candidate),
                        "fps_ratio": round(_fps(candidate) / target, 3),
                        "connections": 1,
                        "disconnects": 0 if candidate.get("status") == "PASS" else 1,
                        "sequence_gaps": 0,
                        "bad_frames": 0,
                        "payload_avg_bytes": (candidate.get("telemetry") or {}).get("payload_avg_bytes") or 0,
                        "errors": [],
                    }
                )
        phase = next(
            (item for item in ladder if item["target_fps"] == sustainable),
            ladder[-1]
            if ladder
            else {
                "target_fps": stability_target,
                "duration_seconds": 0,
                "frames": 0,
                "bytes_received": 0,
                "throughput_mbps": 0.0,
                "measured_fps": 0.0,
                "fps_ratio": 0.0,
                "connections": 0,
                "disconnects": 0,
                "sequence_gaps": 0,
                "bad_frames": 0,
                "errors": errors,
            },
        )

        metrics = {
            "control_successes": 1,
            "control_failures": 0,
            "control_avg_ms": None,
            "control_p50_ms": None,
            "control_p95_ms": None,
            "control_max_ms": None,
            "control_jitter_ms": None,
            "rssi_avg": analysis["rssi"],
            "rssi_min": analysis["rssi"],
            "rssi_max": analysis["rssi"],
            "wifi_bssid": final_status.get("bssid"),
            "wifi_channel": final_status.get("channel"),
            "direct_clean_frames": max((int(row.get("frames") or 0) for row in camera_rows), default=0),
            "direct_clean_fps": best_camera_fps,
            "direct_clean_disconnects": 0,
            "direct_clean_bad_frames": 0,
            "direct_polled_frames": 0,
            "direct_polled_fps": 0.0,
            "direct_polled_disconnects": 0,
            "direct_polled_bad_frames": 0,
            "status_poll_failures": 0,
            "managed_frames": 0,
            "managed_fps": 0.0,
            "managed_failed_fetches": 0,
            "managed_reconnects": 0,
            "managed_session_recoveries": 0,
            "device_send_failures_delta": 0,
            "device_deadline_drops_delta": 0,
            "phase_boundary_send_resets": 0,
            "last_send_errno": None,
            "last_send_accepted_bytes": None,
            "last_frame_bytes": final_status.get("httpd_direct_last_bytes"),
            "send_ewma_ms": final_status.get("httpd_direct_last_send_ms"),
            "wifi_disconnects": None,
            "wifi_reconnects": None,
            "functionality_score": functionality_score,
            "stability_score": stability_score,
            "stability_grade": stability_grade,
            "peak_measured_fps": best_camera_fps,
            "peak_throughput_mbps": analysis["best_bulk_mbps"],
            "estimated_sustainable_target_fps": sustainable,
            "stability_target_fps": stability_target,
            "stability_measured_fps": _number(phase.get("measured_fps")),
            "stability_interval_p95_ms": None,
            "stability_interval_max_ms": None,
            "stability_jitter_ms": None,
            "stability_stall_intervals": 0,
            "stability_disconnects": int(phase.get("disconnects") or 0),
            "stability_sequence_gaps": 0,
            "stability_bad_frames": 0,
        }

        return {
            "run_id": f"cam-tune-{int(time.time() * 1000):x}",
            "started_at_ms": started_ms,
            "duration_ms": int(time.time() * 1000) - started_ms,
            "source_id": source_id,
            "host": host,
            "overall": "healthy"
            if sustainable >= min(saved_target, 15)
            else "warning"
            if best_camera_fps > 0
            else "failed",
            "diagnosis_code": analysis["classification"],
            "title": "R10 camera framebuffer / FPS tuning",
            "summary": f"Recommended FB {analysis['best_fb']['fb_count']} / {analysis['best_fb']['grab_mode']}, {analysis['recommended_architecture']}, JPEG quality {analysis['recommended_jpeg_quality']}, {sustainable} FPS sustainable target; raw TCP peaked at {analysis['best_bulk_mbps']:.2f} Mbit/s.",
            "confidence": analysis["confidence"],
            "likely_causes": [analysis["classification"].replace("_", " ")],
            "recommendations": [recommendation],
            "checks": checks,
            "metrics": metrics,
            "functionality": {
                "score": functionality_score,
                "passed": passed,
                "total": len(rows),
                "config_roundtrip": True,
                "session_lifecycle": state_restored,
            },
            "stability": {"grade": stability_grade, "score": stability_score, "phase": phase},
            "bottleneck_analysis": {
                "primary_bottleneck": analysis["classification"],
                "findings": findings,
                "estimated_sustainable_target_fps": sustainable,
                "peak_measured_fps": best_camera_fps,
                "peak_throughput_mbps": analysis["best_bulk_mbps"],
                "stability_grade": stability_grade,
                "stability_score": stability_score,
                "saved_target_fps": saved_target,
            },
            "candidate_isolation": {
                "supported": True,
                "primary_candidate": analysis["classification"],
                "findings": [],
                "ruled_out": [],
                "matrix": {str(row.get("key")): row.get("status") == "PASS" for row in rows},
            },
            "candidate_phases": {str(row.get("key")): row for row in rows},
            "load_ladder": ladder,
            "contention_phase": phase,
            "managed_phase": {
                "target_fps": saved_target,
                "duration_seconds": 0,
                "frames": 0,
                "failed_fetches": 0,
                "reconnects": 0,
                "session_recoveries": 0,
                "measured_fps": 0.0,
                "throughput_mbps": 0.0,
                "fps_ratio": 0.0,
                "error": "R10 firmware is diagnostic-only; the production managed worker is intentionally skipped.",
            },
            "device": final_status,
            "state_restored": state_restored,
            "restore_error": None if state_restored else "; ".join(restore_errors),
            "diagnostic_target_fps": saved_target,
            "diagnostic_load_targets": list(FPS_TARGETS),
            "prototype_only": True,
            "pipeline_timing": None,
            "tuning_analysis": analysis,
            "transport_benchmark": {
                "schema_version": 2,
                "benchmark_revision": "R10 FB/FPS tuning",
                "firmware": initial.get("firmware"),
                "host": host,
                "environment_label": "selected-camera-network",
                "settings": {
                    "frame_size": original_frame,
                    "jpeg_quality": original_quality,
                    "fps_targets": list(FPS_TARGETS),
                    "stream_frames": STREAM_FRAMES,
                    "fps_measurement": "completed_frame_intervals",
                },
                "diagnosis": {
                    "diagnosis_code": analysis["classification"],
                    "likely_bottleneck": analysis["classification"].replace("_", " "),
                    "recommended_key": analysis["recommended_architecture"],
                    "recommendation": recommendation,
                    "ranking": [],
                },
                "analysis_evidence": {"tuning_analysis": analysis},
                "results": rows,
            },
        }


camera_tuning_diagnostic_service = CameraTuningDiagnosticService()

__all__ = [
    "R10_TUNING_REVISION",
    "CameraTuningDiagnosticService",
    "analyze_tuning_results",
    "camera_tuning_diagnostic_service",
    "choose_best_fb_config",
]
