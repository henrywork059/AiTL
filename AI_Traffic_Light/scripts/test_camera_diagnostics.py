from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "apps" / "pc-studio" / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.services.camera_diagnostic_analysis import EXPECTED_CONTROL_PROBES, analyze_camera_bottlenecks
from app.services.camera_diagnostics import CONTROL_PROBE_ATTEMPTS, classify_camera_diagnostic


def diagnose(**overrides):
    values = {
        "control_successes": EXPECTED_CONTROL_PROBES,
        "protocol_ok": True,
        "camera_ready": True,
        "clean_frames": 25,
        "clean_disconnects": 0,
        "clean_bad_frames": 0,
        "polled_frames": 25,
        "polled_disconnects": 0,
        "polled_bad_frames": 0,
        "status_poll_failures": 0,
        "managed_frames": 25,
        "managed_failed_fetches": 0,
        "send_failures_delta": 0,
        "deadline_drops_delta": 0,
        "rssi_min": -55,
        "stability_grade": "stable",
        "saved_target_fps": 10,
        "estimated_sustainable_fps": 10.0,
        "phase_boundary_send_resets": 0,
    }
    values.update(overrides)
    return classify_camera_diagnostic(**values)


def phase(target: int, measured: float, **overrides):
    values = {
        "target_fps": target,
        "frames": max(1, round(measured * 5)),
        "measured_fps": measured,
        "fps_ratio": measured / max(1, target),
        "throughput_mbps": measured * 0.045,
        "disconnects": 0,
        "bad_frames": 0,
        "sequence_gaps": 0,
        "unexpected_send_failures": 0,
        "deadline_drops": 0,
        "stall_intervals": 0,
        "interval_p95_ms": 1000 / max(0.1, measured),
        "device_send_ewma_ms": 20,
        "device_last_capture_ms": 5,
        "status_poll_failures": 0,
    }
    values.update(overrides)
    return values


def analyze(**overrides):
    values = {
        "control_successes": EXPECTED_CONTROL_PROBES,
        "control_failures": 0,
        "control_p95_ms": 80.0,
        "control_jitter_ms": 10.0,
        "rssi_min": -55,
        "rssi_max": -51,
        "load_phases": [phase(5, 4.9), phase(10, 9.4), phase(15, 12.0)],
        "contention_phase": phase(10, 9.0),
        "contention_reference": phase(10, 9.4),
        "stability_phase": phase(10, 9.2),
        "managed_phase": {
            "target_fps": 10,
            "frames": 90,
            "measured_fps": 9.0,
            "throughput_mbps": 0.40,
            "failed_fetches": 0,
            "reconnects": 0,
            "session_recoveries": 0,
        },
        "saved_target_fps": 10,
    }
    values.update(overrides)
    return analyze_camera_bottlenecks(**values)


def main() -> int:
    assert CONTROL_PROBE_ATTEMPTS == EXPECTED_CONTROL_PROBES
    print("[PASS] diagnostic regression derives probe count from the production source of truth")

    healthy = diagnose(phase_boundary_send_resets=2)
    assert healthy["diagnosis_code"] == "healthy_now"
    assert "excluded" in healthy["summary"]
    print("[PASS] diagnostic-induced phase-boundary TCP resets are excluded from spontaneous failure classification")

    stalled = diagnose(clean_frames=2, clean_disconnects=3, send_failures_delta=2)
    assert stalled["diagnosis_code"] == "esp_camera_tcp_send_stall"
    print("[PASS] active direct-stream ESP send failures identify sender/backpressure stalls")

    invalid_jpeg = diagnose(clean_bad_frames=1)
    assert invalid_jpeg["diagnosis_code"] == "direct_camera_stream_failure"
    print("[PASS] invalid JPEG evidence fails direct-stream functionality")

    contention = diagnose(polled_frames=3, polled_disconnects=2, status_poll_failures=2)
    assert contention["diagnosis_code"] == "control_stream_contention"
    print("[PASS] failure introduced by concurrent /status polling identifies control/data contention")

    integration = diagnose(managed_frames=1, managed_failed_fetches=3)
    assert integration["diagnosis_code"] == "pc_studio_stream_integration"
    print("[PASS] direct success plus managed-worker failure identifies PC Studio integration")

    unstable = diagnose(stability_grade="unstable")
    assert unstable["diagnosis_code"] == "stream_stability_failure"
    print("[PASS] longer-run instability is not hidden by short functional checks")

    degraded = diagnose(stability_grade="degraded")
    assert degraded["diagnosis_code"] == "stream_stability_degraded"
    print("[PASS] degraded sustained timing is reported separately from complete failure")

    capacity = diagnose(saved_target_fps=15, estimated_sustainable_fps=10)
    assert capacity["diagnosis_code"] == "throughput_capacity_limited"
    print("[PASS] saved FPS above measured capacity is reported as a throughput warning")

    control_flaky = diagnose(control_successes=EXPECTED_CONTROL_PROBES - 1)
    assert control_flaky["diagnosis_code"] == "control_plane_instability"
    weak = diagnose(rssi_min=-79)
    assert weak["diagnosis_code"] == "wifi_margin_low"
    print("[PASS] intermittent control and weak Wi-Fi remain distinct warning categories")

    unreachable = diagnose(control_successes=0)
    assert unreachable["diagnosis_code"] == "control_unreachable"
    incompatible = diagnose(protocol_ok=False)
    assert incompatible["diagnosis_code"] == "firmware_incompatible"
    not_ready = diagnose(camera_ready=False)
    assert not_ready["diagnosis_code"] == "camera_not_ready"
    print("[PASS] control/protocol/sensor failures short-circuit stream classification correctly")

    saturated = analyze(load_phases=[phase(5, 4.9), phase(10, 8.8), phase(15, 9.4)])
    assert any(item["id"] == "payload_capacity" for item in saturated["findings"])
    assert saturated["estimated_sustainable_target_fps"] == 10
    print("[PASS] 5/10/15 FPS load ladder detects current-payload throughput saturation")

    slow_control = analyze(control_p95_ms=900.0)
    assert any(item["id"] == "control_latency" for item in slow_control["findings"])
    print("[PASS] control p95 latency exposes control-plane bottlenecks")

    polled_slow = analyze(contention_phase=phase(10, 5.5))
    assert any(item["id"] == "control_stream_contention" for item in polled_slow["findings"])
    print("[PASS] same-load comparison detects status-poll throughput contention")

    sender_pressure = analyze(stability_phase=phase(10, 9.0, device_send_ewma_ms=95))
    assert any(item["id"] == "send_time_pressure" for item in sender_pressure["findings"])
    print("[PASS] ESP send time is compared with the frame-period budget")

    unstable_analysis = analyze(stability_phase=phase(10, 3.0, disconnects=2, unexpected_send_failures=1))
    assert unstable_analysis["stability_grade"] == "unstable"
    assert unstable_analysis["stability_score"] < 80
    print("[PASS] sustained failures lower the stability grade and score")

    managed_slow = analyze(managed_phase={
        "target_fps": 10, "frames": 40, "measured_fps": 4.0, "throughput_mbps": 0.2,
        "failed_fetches": 0, "reconnects": 0, "session_recoveries": 0,
    })
    assert any(item["id"] == "managed_worker_throughput" for item in managed_slow["findings"])
    print("[PASS] direct-vs-managed comparison can expose a PC Studio receive bottleneck")

    service_text = (BACKEND / "app" / "services" / "camera_diagnostics.py").read_text(encoding="utf-8")
    analysis_text = (BACKEND / "app" / "services" / "camera_diagnostic_analysis.py").read_text(encoding="utf-8")
    route_text = (BACKEND / "app" / "routes" / "camera_diagnostics.py").read_text(encoding="utf-8")
    api_text = (ROOT / "apps" / "pc-studio" / "frontend" / "src" / "lib" / "cameraDiagnosticsApi.ts").read_text(encoding="utf-8")
    page_text = (ROOT / "apps" / "pc-studio" / "frontend" / "src" / "pages" / "CameraDiagnosticsPage.tsx").read_text(encoding="utf-8")

    for marker in ("LOAD_TARGET_FPS = (5, 10, 15)", "STABILITY_PHASE_SECONDS = 20.0", "phase_boundary_send_resets", "_managed_phase"):
        assert marker in service_text, marker
    for marker in ("analyze_camera_bottlenecks", "stability_score", "payload_capacity", "control_stream_contention"):
        assert marker in analysis_text, marker
    assert '@router.post("/run")' in route_text
    assert "CameraBottleneckAnalysis" in api_text
    assert "Deep one-click camera test" in page_text
    assert "FPS / throughput load ladder" in page_text
    assert "Diagnostic boundary resets excluded" in page_text
    print("[PASS] V038 R3 deep-diagnostic service/API/UI surfaces are wired")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
