from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
import tempfile

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "apps" / "pc-studio" / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from app.core.exceptions import AppError  # noqa: E402
from app.services.signal_rules import SignalRulesService  # noqa: E402


def main() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        service = SignalRulesService(
            config_path=root / "signal_rules.json",
            history_path=root / "decisions.jsonl",
        )

        defaults = service.get_config()
        assert defaults["schema_version"] == 1
        assert defaults["active_profile"] == "Normal"
        assert defaults["profiles"]["Normal"]["phases"]["vehicle_green"]["base_seconds"] == 12.0

        test_config = deepcopy(defaults)
        test_config["mode"] = "test"
        saved = service.save_config(test_config)
        assert saved["mode"] == "test"
        assert (root / "signal_rules.json").is_file()

        service.set_test_inputs({"vehicles_waiting": 8})
        state = service.signal_state(0.0)
        assert state["phase"] == "vehicle_green"
        service.signal_state(2.1)
        state = service.signal_state(2.2)
        assert "heavy_vehicle_queue" in state["active_rules"]
        assert state["effective_duration_seconds"] == 17.0

        service.reset_runtime(0.0)
        service.set_test_inputs({"vehicles_waiting": 0, "pedestrians_waiting": 6})
        service.signal_state(0.0)
        service.signal_state(2.1)
        state = service.signal_state(2.2)
        assert "heavy_pedestrian_demand" in state["active_rules"]
        assert state["effective_duration_seconds"] <= 9.0
        assert state["effective_duration_seconds"] >= 8.0

        service.set_test_inputs({"incident_person_fallen": True})
        state = service.signal_state(2.3)
        assert state["phase"] == "all_red"
        assert state["incident_hold"] is True
        service.clear_incident()
        recovered = service.signal_state(20.0)
        assert recovered["incident_hold"] is False
        assert recovered["elapsed_seconds"] == 0.0

        # Manual accessibility/incident sources must not control Adaptive/Fixed mode.
        adaptive_config = deepcopy(service.get_config())
        adaptive_config["mode"] = "adaptive"
        service.save_config(adaptive_config)
        service.set_test_inputs({"mobility_assistance": True, "incident_person_fallen": True})
        adaptive_state = service.signal_state(21.0)
        assert adaptive_state["incident_hold"] is False
        assert adaptive_state["test_inputs"]["mobility_assistance"] is True
        # Re-saving Adaptive clears manual-only test inputs.
        service.save_config(adaptive_config)
        cleared_manual = service.signal_state(22.0)
        assert cleared_manual["test_inputs"]["mobility_assistance"] is False
        assert cleared_manual["test_inputs"]["incident_person_fallen"] is False

        test_again = deepcopy(service.get_config())
        test_again["mode"] = "test"
        service.save_config(test_again)

        # Saving while the simulation clock is already advanced must re-anchor the
        # current protected phase instead of replaying elapsed time from clock zero.
        running_config = deepcopy(service.get_config())
        service.save_config(running_config)
        reanchored = service.signal_state(50.0)
        assert reanchored["phase"] in {"vehicle_green", "vehicle_yellow", "all_red", "pedestrian_green", "pedestrian_flashing"}
        assert reanchored["elapsed_seconds"] == 0.0

        # The camera simulation regression suite intentionally seeks its private
        # clock backwards. The stateful controller must rebuild from cycle start
        # instead of retaining a phase whose start time is now in the future.
        service.reset_runtime(0.0)
        forward = service.signal_state(12.2)
        assert forward["phase"] == "vehicle_yellow"
        rewound = service.signal_state(0.2)
        assert rewound["phase"] == "vehicle_green"
        assert rewound["elapsed_seconds"] == 0.2

        preview = service.preview({
            "phase_key": "vehicle_green",
            "vehicles_waiting": 10,
            "pedestrians_waiting": 0,
        })
        assert preview["effective_duration_seconds"] >= 12.0
        assert preview["prototype_only"] is True

        invalid = deepcopy(defaults)
        invalid["profiles"]["Normal"]["phases"]["vehicle_yellow"]["min_seconds"] = 0.5
        try:
            service.save_config(invalid)
        except AppError:
            pass
        else:
            raise AssertionError("protected phase minimum must reject invalid configuration")

        history = service.history(50)
        assert history["count"] > 0
        cleared = service.clear_history()
        assert cleared["cleared"] is True

    print("signal rules service tests passed")


if __name__ == "__main__":
    main()
