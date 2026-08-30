from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "apps" / "pc-studio" / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.services.camera_diagnostic_dispatch import benchmark_to_report, build_pipeline_timing_analysis


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print(f"[PASS] {message}")


def result(key: str, *, fps: float, frames: int = 8, requested: int = 8, send_ms: float = 0.0,
           capture_ms: float = 0.0, interval_ms: float | None = None, production: bool = True) -> dict:
    samples = []
    if requested >= 2:
        for index in range(1, min(frames, 4) + 1):
            samples.append({
                "frame_count": index,
                "last_capture_ms": capture_ms,
                "last_send_ms": send_ms,
                "last_frame_bytes": 18500,
            })
    telemetry = {
        "device_after": {
            "last_capture_ms": capture_ms,
            "last_send_ms": send_ms,
            "last_frame_bytes": 18500,
            "last_accepted_bytes": 18516,
            "last_errno": 0,
            "rssi": -45,
            "internal_free": 120000,
            "internal_largest": 100000,
        },
        "status_poll": {"samples": samples, "successes": len(samples), "failures": 0},
    }
    if interval_ms is not None:
        telemetry["interval_ms"] = {"avg": interval_ms, "p95": interval_ms, "max": interval_ms}
    return {
        "key": key,
        "name": key,
        "transport": "ATL1/TCP",
        "status": "PASS",
        "requested_frames": requested,
        "frames": frames,
        "bytes_received": frames * 18516,
        "elapsed_ms": max(1.0, frames / max(0.01, fps) * 1000.0),
        "measured_fps": fps,
        "completion_ratio": frames / requested if requested else 0.0,
        "status_poll_successes": len(samples),
        "status_poll_failures": 0,
        "packet_loss": None,
        "detail": "synthetic regression row",
        "telemetry": telemetry,
        "production_candidate": production,
    }


def main() -> int:
    raw = {
        "schema_version": 3,
        "benchmark_revision": "R5",
        "firmware": "aitl-0_3_8-r5-transport-benchmark",
        "settings": {"fps": 3, "frame_size": "QVGA", "jpeg_quality": 24},
        "diagnosis": {
            "diagnosis_code": "sendmsg_specific_failure",
            "likely_bottleneck": "sendmsg failure already isolated",
            "recommended_key": "dram_copy_send",
            "recommendation": "Use DRAM copy + plain send().",
            "ranking": [],
        },
        "analysis_evidence": {
            "hypothesis_ranking": [
                {"hypothesis": "sendmsg implicated", "confidence": "high", "evidence": ["plain send passes"]}
            ]
        },
        "initial_device": {"rssi": -45},
        "final_device": {"rssi": -46},
        "run_context": {"duration_ms": 10000, "started_at_ms": 1000},
        "results": [
            result("capture_single", fps=2.8, frames=1, requested=1, send_ms=0, capture_ms=390),
            result("snapshot_polling", fps=0.3, send_ms=0, capture_ms=400, interval_ms=3300),
            result("direct_send", fps=1.02, send_ms=160, capture_ms=410, interval_ms=980),
            result("dram_copy_send", fps=1.10, send_ms=190, capture_ms=405, interval_ms=910),
            result("synthetic_send", fps=3.0, send_ms=3, capture_ms=0, interval_ms=333, production=False),
            result("dram_copy_send_10", fps=1.05, send_ms=200, capture_ms=405, interval_ms=950),
            result("dram_copy_send_15", fps=0.98, send_ms=210, capture_ms=405, interval_ms=1020),
        ],
    }
    capture_probe = {
        "attempts": 4,
        "successes": 4,
        "failures": 0,
        "request_ms": {"count": 4, "avg": 1200.0, "p95": 1250.0, "max": 1250.0},
        "esp_capture_ms": {"count": 4, "avg": 400.0, "p95": 410.0, "max": 410.0},
        "request_minus_capture_ms": {"count": 4, "avg": 800.0, "p95": 840.0, "max": 840.0},
        "records": [],
        "errors": [],
    }

    timing = build_pipeline_timing_analysis(raw, capture_probe)
    check(timing["candidate_key"] == "dram_copy_send", "timing analysis follows the recommended production candidate")
    check(timing["dominant_remaining_stage"] == "camera_capture_wait", "timing analysis can identify camera acquisition as the remaining dominant stage")
    check(timing["unexplained_ms"] > 250, "timing analysis preserves the unaccounted portion of the frame interval")
    check(any("DRAM copy does not create" in item for item in timing["conclusions"]), "timing analysis can rule out DRAM copy as the main FPS ceiling")
    check(any("Synthetic internal-DRAM" in item for item in timing["conclusions"]), "timing analysis compares real camera data with the synthetic control")

    raw["pipeline_timing_analysis"] = timing
    report = benchmark_to_report(raw, {"source_id": "esp32_cam_01", "host": "192.168.1.20", "target_fps": 3}, True)
    check(report["stability"]["score"] < 100, "degraded throughput no longer reports a misleading 100% stability score")
    check(report["bottleneck_analysis"]["estimated_sustainable_target_fps"] == 0, "a target below 70% measured capacity is no longer reported as sustainable")
    check(report["bottleneck_analysis"]["peak_measured_fps"] < 2.0, "single /capture latency is excluded from live-stream peak FPS")
    check(report["pipeline_timing"]["dominant_remaining_stage"] == "camera_capture_wait", "pipeline timing evidence is propagated to the Camera Diagnostics report")

    print("\nCamera diagnostic timing-analysis regression passed. No ESP hardware was required.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
