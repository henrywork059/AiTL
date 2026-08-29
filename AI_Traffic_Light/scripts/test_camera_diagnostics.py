from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "apps" / "pc-studio" / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.services.camera_diagnostics import classify_camera_diagnostic


def diagnose(**overrides):
    values = {
        "control_successes": 3,
        "protocol_ok": True,
        "camera_ready": True,
        "clean_frames": 28,
        "clean_disconnects": 0,
        "clean_bad_frames": 0,
        "polled_frames": 27,
        "polled_disconnects": 0,
        "polled_bad_frames": 0,
        "status_poll_failures": 0,
        "managed_frames": 24,
        "managed_failed_fetches": 0,
        "send_failures_delta": 0,
        "deadline_drops_delta": 0,
        "rssi_min": -62,
    }
    values.update(overrides)
    return classify_camera_diagnostic(**values)


def main() -> int:
    assert diagnose()["diagnosis_code"] == "healthy_now"
    print("[PASS] fully working control/direct/polled/managed path reports healthy-now")

    stalled = diagnose(
        clean_frames=1,
        clean_disconnects=4,
        send_failures_delta=4,
        deadline_drops_delta=4,
    )
    assert stalled["diagnosis_code"] == "esp_camera_tcp_send_stall"
    assert stalled["confidence"] == "high"
    print("[PASS] direct camera stream failure plus ESP send deadlines identifies ESP camera/TCP sender stall")


    invalid_jpeg = diagnose(clean_bad_frames=1)
    assert invalid_jpeg["diagnosis_code"] == "direct_camera_stream_failure"
    print("[PASS] invalid direct JPEG evidence fails the direct camera stream check")

    contention = diagnose(
        clean_frames=28,
        clean_disconnects=0,
        polled_frames=3,
        polled_disconnects=4,
        status_poll_failures=3,
    )
    assert contention["diagnosis_code"] == "control_stream_contention"
    print("[PASS] stream failure introduced only by /status polling identifies control/data contention")

    integration = diagnose(
        clean_frames=28,
        clean_disconnects=0,
        polled_frames=27,
        polled_disconnects=0,
        managed_frames=1,
        managed_failed_fetches=3,
    )
    assert integration["diagnosis_code"] == "pc_studio_stream_integration"
    print("[PASS] direct path success plus managed-worker failure identifies PC Studio integration")


    control_flaky = diagnose(control_successes=2)
    assert control_flaky["diagnosis_code"] == "control_plane_instability"
    assert control_flaky["overall"] == "warning"
    print("[PASS] intermittent control probes are separated from an otherwise healthy image path")

    weak = diagnose(rssi_min=-79)
    assert weak["diagnosis_code"] == "wifi_margin_low"
    assert weak["overall"] == "warning"
    print("[PASS] weak RSSI is reported as a warning when transport itself still passes")

    unreachable = diagnose(control_successes=0)
    assert unreachable["diagnosis_code"] == "control_unreachable"
    print("[PASS] missing ESP control response is classified before stream tests")

    incompatible = diagnose(protocol_ok=False)
    assert incompatible["diagnosis_code"] == "firmware_incompatible"
    print("[PASS] incompatible camera/wire protocol is classified before stream tests")

    not_ready = diagnose(camera_ready=False)
    assert not_ready["diagnosis_code"] == "camera_not_ready"
    print("[PASS] camera sensor readiness failure is classified before stream tests")

    route_text = (BACKEND / "app" / "routes" / "camera_diagnostics.py").read_text(encoding="utf-8")
    service_text = (BACKEND / "app" / "services" / "camera_diagnostics.py").read_text(encoding="utf-8")
    app_text = (ROOT / "apps" / "pc-studio" / "frontend" / "src" / "App.tsx").read_text(encoding="utf-8")
    nav_text = (ROOT / "apps" / "pc-studio" / "frontend" / "src" / "constants" / "appNavigation.ts").read_text(encoding="utf-8")

    assert '@router.post("/run")' in route_text
    assert "CameraDiagnosticService" in service_text
    assert 'case "camera_diagnostics"' in app_text
    assert 'shortLabel: "Camera Test"' in nav_text
    print("[PASS] V038 route/service/page/navigation surfaces are wired")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
