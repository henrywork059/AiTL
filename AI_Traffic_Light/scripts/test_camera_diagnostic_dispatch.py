from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "apps" / "pc-studio" / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.services.camera_diagnostic_dispatch import BENCHMARK_PREFIX, CameraDiagnosticDispatchService, benchmark_to_report


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print(f"[PASS] {message}")


def sample_result(key: str, *, status: str = "PASS", fps: float = 5.0, production: bool = True) -> dict:
    return {
        "key": key,
        "name": key,
        "transport": "test",
        "status": status,
        "requested_frames": 8,
        "frames": 8 if status == "PASS" else 0,
        "bytes_received": 48000 if status == "PASS" else 0,
        "elapsed_ms": 1600.0,
        "measured_fps": fps if status == "PASS" else 0.0,
        "completion_ratio": 1.0 if status == "PASS" else 0.0,
        "detail": key,
        "production_candidate": production,
    }


def main() -> int:
    raw = {
        "firmware": f"{BENCHMARK_PREFIX}",
        "settings": {"fps": 5, "frame_size": "QVGA", "jpeg_quality": 24},
        "run_context": {"started_at_ms": 1000, "duration_ms": 4000},
        "initial_device": {"rssi": -45, "camera_ready": True},
        "final_device": {"rssi": -44, "camera_ready": True, "send_failures": 1, "deadline_drops": 1},
        "diagnosis": {
            "diagnosis_code": "direct_psram_socket_source_failure",
            "likely_bottleneck": "Direct PSRAM-to-socket sending fails while DRAM staging succeeds.",
            "recommended_key": "dram_copy_send",
            "recommendation": "Use whole-frame internal-DRAM copy + plain send().",
            "ranking": [],
        },
        "analysis_evidence": {
            "hypothesis_ranking": [
                {
                    "hypothesis": "direct PSRAM-to-socket access is implicated",
                    "confidence": "high",
                    "evidence": ["direct send fails while DRAM copy passes"],
                }
            ]
        },
        "results": [
            sample_result("capture_single"),
            sample_result("snapshot_polling"),
            sample_result("direct_sendmsg_1200", status="FAIL"),
            sample_result("direct_send", status="FAIL"),
            sample_result("staged_send"),
            sample_result("dram_copy_send"),
            sample_result("synthetic_send", production=False),
            sample_result("udp"),
            sample_result("dram_copy_send_10", fps=10.0),
            sample_result("dram_copy_send_15", fps=15.0),
        ],
    }
    profile = {"source_id": "esp32_cam_01", "host": "192.168.1.50", "target_fps": 5}
    report = benchmark_to_report(raw, profile, cleanup_ok=True)
    check(report["diagnosis_code"] == "direct_psram_socket_source_failure", "integrated report preserves benchmark diagnosis")
    check(report["candidate_isolation"]["primary_candidate"] == "dram_copy_send", "integrated report exposes recommended transport")
    check(report["candidate_isolation"]["matrix"]["dram_copy_send"] is True, "integrated matrix preserves passing DRAM-copy candidate")
    check(report["candidate_isolation"]["matrix"]["direct_send"] is False, "integrated matrix preserves failed direct-PSRAM candidate")
    check(report["transport_benchmark"] is raw, "full raw benchmark evidence remains attached for detailed analysis")
    check(len(report["load_ladder"]) == 3, "recommended candidate load ladder is surfaced in Camera Diagnostics")

    service = CameraDiagnosticDispatchService()
    service._parse("--- MEMORY-SOURCE ISOLATION ---")
    service._parse("[08] START  +18.4s | ATL1 1460-B DRAM staging + send() | PSRAM copied in small DRAM chunks")
    service._parse("     RUN     3/8  | ATL1 1460-B DRAM staging + send() | seq=43; 6084 B")
    progress = service.progress()
    check(progress["stage"] == "MEMORY-SOURCE ISOLATION", "live progress exposes the current benchmark section")
    check(progress["test_index"] == 8, "live progress exposes the current benchmark test number")
    check(progress["frame_current"] == 3 and progress["frame_total"] == 8, "live progress exposes per-frame completion")
    check("DRAM staging" in str(progress["current_test"]), "live progress exposes the current transport method")

    page = (ROOT / "apps" / "pc-studio" / "frontend" / "src" / "pages" / "CameraDiagnosticsPage.tsx").read_text(encoding="utf-8")
    api = (ROOT / "apps" / "pc-studio" / "frontend" / "src" / "lib" / "cameraDiagnosticsApi.ts").read_text(encoding="utf-8")
    route = (BACKEND / "app" / "routes" / "camera_diagnostics.py").read_text(encoding="utf-8")
    check("Full transport benchmark matrix" in page and "Diagnostic engine" in page, "Camera Diagnostics page renders integrated matrix and live progress")
    check("fetchCameraDiagnosticProgress" in api, "frontend API exposes diagnostic progress polling")
    check('@router.get("/progress")' in route, "backend exposes the diagnostic progress endpoint")

    print("\nIntegrated Camera Diagnostics transport benchmark regression passed without ESP hardware.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
