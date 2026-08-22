from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "apps" / "pc-studio" / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.services.network_policy_arbiter import POLICY_PRIORITIES  # noqa: E402
from app.services.network_simulation_experiments import _BenchmarkSignalRulesService  # noqa: E402
from app.services.signal_rules import PHASE_SEQUENCE, signal_rules_service  # noqa: E402


def _controller(root: Path, name: str) -> _BenchmarkSignalRulesService:
    config = signal_rules_service.defaults()
    config["mode"] = "fixed"
    config["dry_run"] = False
    config_path = root / f"{name}_signal_rules.json"
    history_path = root / f"{name}_history.jsonl"
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    return _BenchmarkSignalRulesService(config_path=config_path, history_path=history_path)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="aitl_v031_request_lifecycle_") as temporary:
        root = Path(temporary)
        controller = _controller(root, "lifecycle")

        # Put the controller in vehicle yellow so neither requested service is
        # currently active. Higher-priority pedestrian starvation service must
        # not be replaced by a lower-priority ordinary vehicle request.
        with controller._lock:
            controller._phase_index = 1
            controller._cycle_started_clock = 0.0
            controller._initialize_phase_locked(0.0)
            created = controller._request_service_locked(
                "pedestrian",
                clock_s=0.0,
                source="pedestrian_max_wait",
                priority=POLICY_PRIORITIES["pedestrian_max_wait"],
                reason="test pedestrian starvation request",
            )
            assert created is True
            replaced = controller._request_service_locked(
                "vehicle",
                clock_s=0.0,
                source="network_cooperation",
                priority=POLICY_PRIORITIES["network_cooperation"],
                reason="test lower-priority vehicle request",
            )
            assert replaced is False

        status = controller.snapshot_state(0.0)
        request = status["service_request"]
        assert request["active"] is True
        assert request["service"] == "pedestrian"
        assert request["source"] == "pedestrian_max_wait"
        assert request["priority"] == POLICY_PRIORITIES["pedestrian_max_wait"]

        profile = controller.get_config()["profiles"][controller.get_config()["active_profile"]]
        yellow = float(profile["phases"]["vehicle_yellow"]["base_seconds"])
        all_red = float(profile["phases"]["all_red_to_pedestrian"]["base_seconds"])
        pedestrian_start = yellow + all_red + 0.1
        served = controller.snapshot_state(pedestrian_start)
        assert served["phase_key"] == "pedestrian_green"
        assert served["service_request"]["active"] is False
        assert served["pending_request"] is None

        event_types = [event.get("event_type") for event in controller.history(100)["events"]]
        assert "service_request_started" in event_types
        assert "service_request_suppressed" in event_types
        assert "service_request_satisfied" in event_types

        # signal_state() is the mutating/evaluating tick. snapshot_state() must
        # not perform a second ranked-scenario evaluation at the same clock.
        snapshot_controller = _controller(root, "snapshot")
        evaluations = 0
        original_evaluate = snapshot_controller._evaluate_rules_locked

        def counted(clock: float, *, apply: bool) -> None:
            nonlocal evaluations
            evaluations += 1
            original_evaluate(clock, apply=apply)

        snapshot_controller._evaluate_rules_locked = counted  # type: ignore[method-assign]
        snapshot_controller.set_benchmark_clock(0.0)
        snapshot_controller.observe(
            {
                "pedestrians_waiting": 0,
                "pedestrians_crossing": 0,
                "vehicles_waiting": 2,
                "zone_class_counts": {},
                "data_source": "network_simulation_experiment",
            }
        )
        snapshot_controller.signal_state(0.0)
        snapshot_controller.snapshot_state(0.0)
        assert evaluations == 1

        assert dict(PHASE_SEQUENCE)[served["phase_key"]] == served["phase"]

    print("V031 network service-request lifecycle regression OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
