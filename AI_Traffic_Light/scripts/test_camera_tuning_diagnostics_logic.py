from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "apps" / "pc-studio" / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.services.camera_tuning_diagnostics import (
    CameraTuningDiagnosticService,
    analyze_tuning_results,
    choose_best_fb_config,
)


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print(f"[PASS] {message}")


def stream_row(
    key: str,
    experiment: str,
    target_fps: int,
    measured_fps: float,
    *,
    fb_count: int = 2,
    grab_mode: str = "latest",
    jpeg_quality: int | None = None,
) -> dict:
    telemetry = {
        "experiment": experiment,
        "target_fps": target_fps,
        "fb_count": fb_count,
        "grab_mode": grab_mode,
        "architecture": "cached_latest_frame" if experiment == "cached_fps" else "direct_httpd",
        "payload_avg_bytes": 16000,
    }
    if jpeg_quality is not None:
        telemetry["jpeg_quality"] = jpeg_quality
    frames = 6
    return {
        "key": key,
        "status": "PASS",
        "requested_frames": frames,
        "frames": frames,
        "bytes_received": frames * 16000,
        "elapsed_ms": max(1.0, (frames - 1) * 1000.0 / max(0.01, measured_fps)),
        "measured_fps": measured_fps,
        "telemetry": telemetry,
    }


def bulk_row(
    key: str,
    experiment: str,
    mbps: float,
    *,
    chunk_bytes: int = 1460,
    requested_bytes: int = 128 * 1024,
) -> dict:
    return {
        "key": key,
        "status": "PASS",
        "requested_frames": 1,
        "frames": 1,
        "bytes_received": requested_bytes,
        "elapsed_ms": requested_bytes * 8.0 / max(0.01, mbps) / 1000.0,
        "measured_fps": None,
        "telemetry": {
            "experiment": experiment,
            "throughput_mbps": mbps,
            "chunk_bytes": chunk_bytes,
            "requested_bytes": requested_bytes,
        },
    }


def fb_rows() -> list[dict]:
    rows: list[dict] = []
    profiles = {
        (1, "when_empty"): (3.0, 4.0, 5.5, 6.0),
        (1, "latest"): (3.0, 4.5, 6.0, 6.5),
        (2, "when_empty"): (3.0, 5.0, 8.0, 9.0),
        (2, "latest"): (3.0, 5.0, 8.5, 11.0),
    }
    for (fb_count, grab_mode), measured in profiles.items():
        for target, fps in zip((3, 5, 10, 15), measured):
            rows.append(
                stream_row(
                    f"fb{fb_count}-{grab_mode}-{target}",
                    "fb_fps",
                    target,
                    fps,
                    fb_count=fb_count,
                    grab_mode=grab_mode,
                )
            )
    return rows


def main() -> int:
    base = fb_rows()
    best = choose_best_fb_config(base)
    check(best["fb_count"] == 2 and best["grab_mode"] == "latest", "R10 selects the strongest framebuffer/grab-mode profile")
    check(best["sustainable_fps"] == 15, "R10 sustainable target uses the 70% target threshold across the FPS ladder")

    service = CameraTuningDiagnosticService()
    service._mjpeg = lambda host, port, path: {"frames": 6, "bytes": 96000, "elapsed_ms": 1000.0}  # type: ignore[method-assign]
    direct_result = service._stream("127.0.0.1", architecture="direct_httpd", target_fps=5, frames=6)
    check(direct_result["requested"] == 6, "R10 calls the inherited three-argument MJPEG helper and preserves requested frame count")
    interval_row = service._stream_row(
        "interval-test",
        "Interval cadence test",
        direct_result,
        target_fps=5,
        telemetry={"experiment": "fb_fps", "fb_count": 2, "grab_mode": "latest", "transport": "test"},
    )
    check(interval_row["measured_fps"] == 5.0, "R10 finite-stream FPS uses completed inter-frame intervals instead of frames/elapsed overcounting")

    cached = [
        stream_row(f"cached-{target}", "cached_fps", target, fps)
        for target, fps in zip((3, 5, 10, 15), (3.0, 5.0, 10.0, 14.0))
    ]
    quality = [
        stream_row("q18", "jpeg_quality", 10, 6.0, jpeg_quality=18),
        stream_row("q24", "jpeg_quality", 10, 8.0, jpeg_quality=24),
        stream_row("q30", "jpeg_quality", 10, 9.0, jpeg_quality=30),
        stream_row("q36", "jpeg_quality", 10, 10.0, jpeg_quality=36),
    ]
    chunks = [
        bulk_row("c1460", "chunk_sweep", 1.0, chunk_bytes=1460),
        bulk_row("c2920", "chunk_sweep", 1.4, chunk_bytes=2920),
        bulk_row("c5840", "chunk_sweep", 2.0, chunk_bytes=5840),
        bulk_row("c11680", "chunk_sweep", 1.7, chunk_bytes=11680),
    ]
    sizes = [
        bulk_row("s32", "transfer_size", 0.8, chunk_bytes=5840, requested_bytes=32 * 1024),
        bulk_row("s128", "transfer_size", 1.5, chunk_bytes=5840, requested_bytes=128 * 1024),
        bulk_row("s512", "transfer_size", 2.0, chunk_bytes=5840, requested_bytes=512 * 1024),
    ]
    repeats = [
        bulk_row("r1", "repeatability", 1.8, chunk_bytes=5840),
        bulk_row("r2", "repeatability", 2.0, chunk_bytes=5840),
        bulk_row("r3", "repeatability", 1.9, chunk_bytes=5840),
    ]

    analysis = analyze_tuning_results(
        base + cached + quality + chunks + sizes + repeats,
        original_quality=24,
        saved_target_fps=10,
        status={"rssi": -40},
    )
    check(analysis["recommended_architecture"] == "cached_latest_frame", "R10 prefers newest-frame caching when matched-target delivery improves")
    check(analysis["recommended_jpeg_quality"] == 24, "R10 keeps the highest JPEG quality that clears the performance threshold")
    check(analysis["best_chunk_bytes"] == 5840, "R10 identifies the best raw TCP application write size")
    check((analysis["chunk_gain_vs_1460"] or 0) >= 1.9, "R10 reports write-batching gain versus 1460-byte writes")
    check((analysis["transfer_size_scaling_ratio"] or 0) > 2.0, "R10 identifies material fixed connection/startup overhead from transfer-size scaling")
    check(not analysis["network_variability"], "stable repeat bulk runs do not falsely flag RF/AP variability")
    check(analysis["recommended_profile"]["fb_count"] == 2 and analysis["recommended_profile"]["grab_mode"] == "latest", "R10 returns a production-prototype framebuffer recommendation")

    variable = analyze_tuning_results(
        base
        + [stream_row(f"cached-v-{target}", "cached_fps", target, fps) for target, fps in zip((3, 5, 10, 15), (3.0, 5.0, 8.5, 11.0))]
        + [bulk_row("vc1460", "chunk_sweep", 2.0, chunk_bytes=1460)]
        + [
            bulk_row("vr1", "repeatability", 0.9),
            bulk_row("vr2", "repeatability", 2.1),
            bulk_row("vr3", "repeatability", 1.3),
        ],
        original_quality=24,
        saved_target_fps=10,
        status={"rssi": -36},
    )
    check(variable["network_variability"], "R10 flags material run-to-run RF/AP/network variation independently of RSSI")
    check(variable["repeatability_spread_ratio"] >= 0.25, "R10 preserves quantitative repeatability spread evidence")

    network_limited = analyze_tuning_results(
        base
        + [bulk_row("nc1460", "chunk_sweep", 0.35, chunk_bytes=1460)]
        + [bulk_row("nr1", "repeatability", 0.32), bulk_row("nr2", "repeatability", 0.34), bulk_row("nr3", "repeatability", 0.33)],
        original_quality=24,
        saved_target_fps=10,
        status={"rssi": -40},
    )
    check(network_limited["classification"] == "network_limited_after_tuning", "sub-1 Mbit/s camera-free controls remain classified as a network/ESP-path limit after tuning")

    firmware_path = ROOT / "apps" / "device-camera" / "esp32-cam" / "arduino" / "AiTL_ESP32_CAM_ARCH_DIAG" / "AiTL_ESP32_CAM_ARCH_DIAG.ino"
    firmware_text = firmware_path.read_text(encoding="utf-8")
    check("tuning_revision\\\":\\\"R10" in firmware_text, "ESP status exposes the R10 tuning revision")
    check("/camera/reinit" in firmware_text, "ESP firmware supports controlled camera reinitialization between FB experiments")
    check("rawBulkChunkBytes" in firmware_text and "DEFAULT_BULK_CHUNK_BYTES" in firmware_text, "ESP firmware supports application write-size sweeps")

    enhanced_path = BACKEND / "app" / "services" / "camera_diagnostic_enhanced.py"
    enhanced_text = enhanced_path.read_text(encoding="utf-8")
    r10_dispatch = enhanced_text.index("tuning_revision == R10_TUNING_REVISION")
    legacy_r9_dispatch = enhanced_text.index("if profile and firmware.startswith(R9_FIRMWARE_PREFIX):", r10_dispatch + 1)
    check(r10_dispatch < legacy_r9_dispatch, "adaptive dispatch checks R10 before the shared legacy R9 firmware marker")
    check("camera_tuning_diagnostic_service.run" in enhanced_text, "one-click Camera Diagnostics invokes the R10 tuning service")

    tuning_path = BACKEND / "app" / "services" / "camera_tuning_diagnostics.py"
    tuning_text = tuning_path.read_text(encoding="utf-8")
    check("finally:" in tuning_text and "R10 RESTORE" in tuning_text, "R10 restoration is protected by a finally path after mid-matrix failures")
    check("completed_frame_intervals" in tuning_text, "R10 report records the corrected finite-stream FPS measurement basis")

    print("\nR10 camera tuning diagnostics offline regression passed. No ESP hardware was required.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
