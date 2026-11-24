"""Hardware-free checks for the additive read-only device contract (Update 10)."""
from __future__ import annotations

import json
from pathlib import Path
import sys

# The source is beside this script when exercising it independently; in the
# repository it is imported from the established backend app/services package.
BACKEND = Path(__file__).resolve().parents[1] / "apps" / "pc-studio" / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))
try:
    from app.services.device_capabilities import project_camera_device
except ModuleNotFoundError:
    from device_capabilities import project_camera_device


def profile(source: str = "camera_a", **overrides: object) -> dict:
    state = {
        "source_id": source,
        "kind": "esp32",
        "connected": False,
        "device_reachable": False,
        "streaming": False,
        "stream_connected": False,
        "paused_for_simulation": False,
        "frame_age_ms": None,
        "frame_stale": False,
        "last_error": None,
        "host": "192.168.7.83",
        "target_fps": 20,
        "settings": {"frame_size": "QVGA", "jpeg_quality": 24},
    }
    state.update(overrides)
    return state


def test_states() -> None:
    cases = [
        ({}, "not_connected", False),
        ({"streaming": True, "stream_connected": True, "frame_age_ms": 100}, "not_connected", False),
        ({"connected": True, "device_reachable": False}, "unreachable", False),
        ({"connected": True, "device_reachable": True}, "connected", False),
        ({"connected": True, "device_reachable": True, "streaming": True}, "reconnecting", False),
        ({"connected": True, "streaming": True, "stream_connected": True}, "waiting_for_frame", False),
        ({"connected": True, "streaming": True, "stream_connected": True, "frame_age_ms": 0}, "streaming", True),
        ({"connected": True, "streaming": True, "stream_connected": True, "frame_age_ms": 5200, "frame_stale": True}, "stale", False),
        ({"connected": True, "streaming": True, "frame_age_ms": 100, "paused_for_simulation": True}, "paused", False),
        ({"connected": True, "streaming": True, "last_error": "timeout"}, "error", False),
        ({"connected": True, "last_error": "unavailable"}, "error", False),
    ]
    for fields, state, fresh in cases:
        result = project_camera_device(profile(**fields))
        assert result["health"]["state"] == state, (fields, result)
        assert result["health"]["frame_fresh"] is fresh
        assert result["capabilities"]["camera_input"]["available"] is fresh
        assert result["physical_output_allowed"] is False
        assert all(result["capabilities"][x]["support"] == "unavailable" and
                   result["capabilities"][x]["available"] is False
                   for x in ("lighting_output", "speaker_output"))


def test_multi_source_and_simulation() -> None:
    camera_a = profile("cam_a", connected=True, device_reachable=True,
                       streaming=True, stream_connected=True, frame_age_ms=100)
    camera_b = profile("cam_b", connected=True, device_reachable=True,
                       streaming=True, stream_connected=False, frame_age_ms=6000,
                       frame_stale=True, last_error="ESP unavailable")
    a, b = project_camera_device(camera_a), project_camera_device(camera_b)
    assert (a["source_id"], a["health"]["state"]) == ("cam_a", "streaming")
    assert (b["source_id"], b["health"]["state"]) == ("cam_b", "error")
    assert camera_a["settings"] == {"frame_size": "QVGA", "jpeg_quality": 24}
    assert a["health"]["last_error"] is None
    assert b["health"]["last_error"] == "ESP unavailable"
    sim = project_camera_device(profile("simulation_camera", kind="simulation", connected=True,
                                        streaming=True, stream_connected=True))
    assert sim["device_type"] == "simulation_camera"
    assert sim["health"]["state"] == "simulated"
    assert sim["health"]["control_connected"] is None
    assert sim["health"]["reachable"] is None
    assert sim["capabilities"]["camera_input"] == {
        "direction": "input", "support": "simulation-only", "available": True,
    }
    sim_idle = project_camera_device(profile("simulation_camera", kind="simulation"))
    assert sim_idle["health"]["state"] == "idle"
    assert sim_idle["capabilities"]["camera_input"]["available"] is False


def test_contract_shape_and_safety() -> None:
    value = project_camera_device(profile(connected=True, device_reachable=True))
    assert value["schema_version"] == 1
    assert value["control_owner"] == "pc_studio"
    assert set(value["capabilities"]) == {"camera_input", "lighting_output", "speaker_output"}
    assert json.loads(json.dumps(value)) == value
    assert "host" not in value and "settings" not in value
    assert value["health"]["frame_age_ms"] is None
    assert project_camera_device(profile(frame_age_ms=-10))["health"]["frame_age_ms"] is None
    assert project_camera_device(profile(frame_age_ms=True))["health"]["frame_age_ms"] is None
    try:
        project_camera_device(profile(kind="drone"))
    except ValueError:
        pass
    else:
        raise AssertionError("Unknown physical module must not be advertised as a camera")


def main() -> int:
    test_states()
    test_multi_source_and_simulation()
    test_contract_shape_and_safety()
    print("[PASS] V0554 pure capability projection: 3 groups, 11 physical states, simulation, independent sources and no physical outputs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
