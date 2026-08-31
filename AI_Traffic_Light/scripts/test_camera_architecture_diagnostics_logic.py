from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "apps" / "pc-studio" / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.services.camera_architecture_diagnostics import analyze_architecture_results


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print(f"[PASS] {message}")


def stream_row(key: str, fps: float) -> dict:
    frames = 8
    elapsed_ms = 1000.0 * frames / max(0.01, fps)
    return {
        "key": key,
        "status": "PASS",
        "requested_frames": frames,
        "frames": frames,
        "bytes_received": frames * 18000,
        "elapsed_ms": elapsed_ms,
        "measured_fps": fps,
        "telemetry": {},
    }


def bulk_row(key: str, mbps: float) -> dict:
    return {
        "key": key,
        "status": "PASS",
        "requested_frames": 1,
        "frames": 1,
        "bytes_received": 512 * 1024,
        "elapsed_ms": (512 * 1024 * 8.0) / max(0.01, mbps) / 1000.0,
        "measured_fps": None,
        "telemetry": {"throughput_mbps": mbps},
    }


def rows(manual: float, direct: float, cached: float, httpd_bulk: float, raw_no_delay: float, raw_nagle: float) -> list[dict]:
    return [
        stream_row("r9_manual_mjpeg", manual),
        stream_row("r9_httpd_direct_mjpeg", direct),
        stream_row("r9_httpd_cached_mjpeg", cached),
        bulk_row("r9_httpd_bulk", httpd_bulk),
        bulk_row("r9_raw_bulk_nodelay", raw_no_delay),
        bulk_row("r9_raw_bulk_nagle", raw_nagle),
    ]


def main() -> int:
    healthy_status = {"reset_reason": "poweron", "rssi": -45}

    manual_regression = analyze_architecture_results(rows(1.0, 10.0, 11.0, 8.0, 7.5, 7.2), healthy_status, 10)
    check(manual_regression["classification"] == "manual_socket_sender_regression", "fast old-style HTTPD versus slow manual WiFiClient isolates a sender regression")
    check(manual_regression["httpd_vs_manual_ratio"] >= 1.5, "HTTPD/manual improvement ratio is preserved")
    check(any("manual WiFiClient" in layer for layer in manual_regression["likely_layers"]), "manual sender layer is named when HTTPD wins decisively")

    coupling = analyze_architecture_results(rows(1.0, 2.0, 10.0, 8.0, 8.0, 7.8), healthy_status, 10)
    check(coupling["classification"] == "capture_send_coupling", "Pi-style cached producer/consumer isolates capture-send serialization when it beats direct HTTPD")
    check(coupling["cached_vs_direct_ratio"] >= 1.5, "cached/direct improvement ratio is preserved")

    common_network = analyze_architecture_results(rows(1.0, 1.1, 1.0, 0.3, 0.25, 0.28), healthy_status, 10)
    check(common_network["classification"] == "common_network_or_esp_stack_bottleneck", "slow camera-free bulk identifies a common ESP/network/PC path bottleneck")
    check(common_network["bulk_headroom"] == "severely_constrained", "sub-1 Mbit/s bulk is classified as severely constrained")

    camera_specific = analyze_architecture_results(rows(1.0, 1.1, 1.2, 10.0, 9.0, 9.2), healthy_status, 10)
    check(camera_specific["classification"] == "camera_or_jpeg_pipeline_specific", "healthy camera-free bulk with universally slow camera streams isolates camera/JPEG-specific work")
    check(camera_specific["bulk_headroom"] == "ample", "5+ Mbit/s camera-free TCP is recognized as ample headroom")

    nagle = analyze_architecture_results(rows(1.0, 1.1, 1.2, 3.0, 6.0, 2.0), healthy_status, 10)
    check((nagle["nagle_sensitivity_ratio"] or 0) >= 0.25, "large NODELAY/Nagle throughput difference is measured")
    check(any("Nagle" in layer or "packetization" in layer for layer in nagle["likely_layers"]), "TCP packetization/Nagle sensitivity becomes a named candidate")

    brownout = analyze_architecture_results(rows(1.0, 1.1, 1.2, 0.4, 0.5, 0.5), {"reset_reason": "brownout", "rssi": -45}, 10)
    check(brownout["power_evidence"] == "brownout_detected", "ESP brownout reset promotes power integrity to concrete evidence")
    check(any("power" in layer.lower() for layer in brownout["likely_layers"]), "power supply/cable/regulator layer is reported after brownout")

    strong_rssi = analyze_architecture_results(rows(1.0, 1.1, 1.2, 0.4, 0.5, 0.5), healthy_status, 10)
    check(any("Weak signal strength is unlikely" in finding for finding in strong_rssi["findings"]), "strong RSSI rules out weak signal strength without ruling out interference/AP behavior")

    firmware_path = ROOT / "apps" / "device-camera" / "esp32-cam" / "arduino" / "AiTL_ESP32_CAM_ARCH_DIAG" / "AiTL_ESP32_CAM_ARCH_DIAG.ino"
    firmware_text = firmware_path.read_text(encoding="utf-8")
    check("aitl-0_3_8-r9-architecture-benchmark" in firmware_text, "R9 firmware exposes a unique adaptive-dispatch marker")
    check("#include <esp_http_server.h>" in firmware_text and "httpd_resp_send_chunk" in firmware_text, "R9 physically benchmarks the older esp_http_server chunked sender")
    check("CAMERA_GRAB_LATEST" in firmware_text and "config.fb_count = 2" in firmware_text, "R9 restores the older two-buffer latest-frame camera architecture")
    check("cacheCaptureTask" in firmware_text and "/cached.mjpeg" in firmware_text, "R9 contains an independent Pi-style latest-frame producer/consumer path")
    check("/bulk.bin" in firmware_text and "RAW_BULK_PORT" in firmware_text, "R9 contains camera-free HTTPD and raw TCP bulk controls")
    check("TCP_NODELAY" in firmware_text and "rawBulkNoDelay" in firmware_text, "R9 can compare raw TCP with Nagle disabled and enabled")
    check("ESP_RST_BROWNOUT" in firmware_text, "R9 exposes software brownout reset evidence without claiming voltage measurement")

    enhanced_path = BACKEND / "app" / "services" / "camera_diagnostic_enhanced.py"
    enhanced_text = enhanced_path.read_text(encoding="utf-8")
    check("R9_FIRMWARE_PREFIX" in enhanced_text and "camera_architecture_diagnostic_service.run" in enhanced_text, "one-click Camera Diagnostics automatically dispatches R9 firmware")
    check("run_alternative_followup" in enhanced_text, "existing R5 to R8 alternative follow-up remains wired")

    print("\nR9 camera architecture diagnostics offline regression passed. No ESP hardware was required.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
