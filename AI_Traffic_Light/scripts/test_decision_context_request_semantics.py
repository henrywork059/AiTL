from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "apps" / "pc-studio" / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.services.decision_context import _active_requested_service, _category, build_decision_context  # noqa: E402


def _network_resolution() -> dict:
    return {
        "intersection_id": "A",
        "intersection_label": "A",
        "source_id": "cam_a",
        "source_mapping_matched": True,
        "network_context": {"neighbors": []},
    }


def main() -> int:
    legacy_signal = {"pending_request": "pedestrian", "winning_scenario_id": None}
    state = {"pedestrians_waiting": 2, "pedestrians_crossing": 0, "vehicles_waiting": 0}
    assert _active_requested_service(legacy_signal) is None
    assert _category(legacy_signal, state) == "pedestrian_observation"

    lifecycle_signal = {
        "pending_request": "pedestrian",
        "service_request": {"active": True, "service": "pedestrian"},
        "winning_scenario_id": None,
    }
    assert _active_requested_service(lifecycle_signal) == "pedestrian"
    assert _category(lifecycle_signal, state) == "pedestrian_service"

    inactive_signal = {
        "pending_request": "vehicle",
        "service_request": {"active": False, "service": "vehicle"},
        "winning_scenario_id": None,
    }
    assert _active_requested_service(inactive_signal) is None

    legacy_context = build_decision_context(
        {**state, "phase": "vehicle_green", "signal_policy": legacy_signal},
        network_resolution=_network_resolution(),
        simulation_enabled=True,
    )
    assert legacy_context["requested_service"] is None
    assert legacy_context["category"] == "pedestrian_observation"

    lifecycle_context = build_decision_context(
        {**state, "phase": "vehicle_green", "signal_policy": lifecycle_signal},
        network_resolution=_network_resolution(),
        simulation_enabled=True,
    )
    assert lifecycle_context["requested_service"] == "pedestrian"
    assert lifecycle_context["category"] == "pedestrian_service"

    print("V031 decision-context request semantics regression OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
