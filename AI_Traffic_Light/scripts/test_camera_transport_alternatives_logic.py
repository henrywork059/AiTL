from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "apps" / "pc-studio" / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.services.camera_transport_alternatives import analyze_alternatives, extract_reference_size


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print(f"[PASS] {message}")


def row(key: str, fps: float, *, payload: int = 18000, actual_rcvbuf: int = 262144) -> dict:
    return {
        "key": key,
        "name": key,
        "transport": "ATL1/TCP",
        "status": "PASS",
        "requested_frames": 4,
        "frames": 4,
        "bytes_received": 4 * (payload + 16),
        "elapsed_ms": 4000.0 / max(0.01, fps),
        "measured_fps": fps,
        "completion_ratio": 1.0,
        "status_poll_successes": 0,
        "status_poll_failures": 0,
        "packet_loss": None,
        "detail": "offline regression",
        "telemetry": {"payload_bytes": payload, "actual_rcvbuf": actual_rcvbuf},
        "production_candidate": False,
    }


def raw_report() -> dict:
    real_sizes = [17600, 18100, 17900, 18300, 18000, 17750]
    return {
        "reference_frame_bytes": 5000,
        "settings": {"fps": 3},
        "results": [
            {
                "key": "dram_copy_send",
                "name": "real DRAM copy",
                "status": "PASS",
                "requested_frames": 8,
                "frames": 8,
                "bytes_received": sum(real_sizes) + 16 * len(real_sizes),
                "measured_fps": 1.0,
                "production_candidate": True,
                "telemetry": {"frame_size_bytes": real_sizes},
            },
            {
                "key": "direct_send",
                "name": "direct send",
                "status": "PASS",
                "requested_frames": 8,
                "frames": 8,
                "bytes_received": 8 * 18016,
                "measured_fps": 0.95,
                "production_candidate": True,
                "telemetry": {"frame_size_bytes": [18000] * 8},
            },
            {"key": "mjpeg_10", "name": "MJPEG", "status": "PASS", "requested_frames": 8, "frames": 8, "measured_fps": 1.05, "production_candidate": True, "telemetry": {}},
            {"key": "staged_1460", "name": "staged 1460", "status": "PASS", "requested_frames": 6, "frames": 6, "measured_fps": 0.9, "production_candidate": True, "telemetry": {}},
            {"key": "staged_2920", "name": "staged 2920", "status": "PASS", "requested_frames": 6, "frames": 6, "measured_fps": 1.1, "production_candidate": True, "telemetry": {}},
        ],
    }


def main() -> int:
    raw = raw_report()
    reference = extract_reference_size(raw)
    check(17500 <= reference <= 18250, "reference payload comes from the median real streaming JPEG, not the first small /capture")

    rows = [
        row("alt_synthetic_5000", 3.0, payload=5000),
        row("alt_synthetic_10000", 2.0, payload=10000),
        row("alt_synthetic_15000", 1.3, payload=15000),
        row(f"alt_synthetic_{reference}", 1.05, payload=reference),
        row("alt_synthetic_20000", 0.9, payload=20000),
        row("alt_synthetic_25000", 0.7, payload=25000),
        row("alt_rcvbuf_16384", 0.98, actual_rcvbuf=32768),
        row("alt_rcvbuf_65536", 1.00, actual_rcvbuf=131072),
        row("alt_rcvbuf_262144", 1.02, actual_rcvbuf=524288),
        row("alt_rcvbuf_1048576", 1.01, actual_rcvbuf=2097152),
        row("alt_fast_drain", 1.02),
        row("alt_slow_drain", 0.60),
    ]
    analysis = analyze_alternatives(raw, rows, reference)
    check(analysis["classification"] == "payload_size_or_common_tcp_path", "exact-size synthetic matching real FPS identifies payload-size/common TCP limitation")
    check(not analysis["receiver_buffer_sensitive"], "small receive-buffer FPS spread rules out PC SO_RCVBUF as the primary limiter")
    check(analysis["drain_sensitive"], "artificially slow receiver drain is recognized as backpressure-sensitive")
    check(any("WiFiClient.write" in finding for finding in analysis["findings"]), "existing MJPEG evidence is used to assess Arduino WiFiClient.write() as an alternative")
    check(any(item["method"] == "raw lwIP tcp_write/tcp_output" for item in analysis["methods_assessed"]), "raw lwIP is retained as a future lower-level A/B option")
    check(any(item["method"] == "WebSocket" for item in analysis["methods_assessed"]), "WebSocket remains explicitly assessed rather than silently ignored")

    camera_specific_rows = list(rows)
    for item in camera_specific_rows:
        if item["key"] == f"alt_synthetic_{reference}":
            item["measured_fps"] = 3.0
    camera_specific = analyze_alternatives(raw, camera_specific_rows, reference)
    check(camera_specific["classification"] == "real_camera_payload_path_specific", "fast exact-size synthetic data isolates a real-camera/data-path-specific ceiling")

    route_text = (BACKEND / "app" / "routes" / "camera_diagnostics.py").read_text(encoding="utf-8")
    enhanced_text = (BACKEND / "app" / "services" / "camera_diagnostic_enhanced.py").read_text(encoding="utf-8")
    check("camera_diagnostic_enhanced_service" in route_text, "Camera Diagnostics route uses the enhanced R8 service")
    check("run_alternative_followup" in enhanced_text, "R8 alternative follow-up is wired after the R5 report")

    print("\nCamera transport alternatives offline regression passed. No ESP hardware was required.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
