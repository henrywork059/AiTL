"""V0512 opt-in virtual emergency corridor regression; no hardware actuation."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/pc-studio/backend"))

from app.core.exceptions import AppError  # noqa: E402
from app.services.crosswalks import CrosswalkService  # noqa: E402
from app.services.crosswalk_signals import CrosswalkSignalService  # noqa: E402
from app.services.signal_rules import SignalRulesService  # noqa: E402

POLYGON = [[0, 0], [1280, 0], [1280, 720], [0, 720]]


def crosswalk(identity: str, camera: str) -> dict:
    return {
        "id": identity, "label": identity, "location": "",
        "camera_side_a_id": camera, "camera_side_b_id": None,
        "regions": [{"id": "region_1", "label": "Road", "camera_side": "a",
                     "vertices": POLYGON, "vertices_by_side": {"a": POLYGON}}],
    }


def detected(source: str, frame_number: int, classes: list[str]) -> dict:
    timestamp = int(time.time() * 1000)
    return {
        "source_id": source, "model_id": "demo", "error": None,
        "frame": {
            "source_id": source, "timestamp_ms": timestamp,
            "source_frame_number": frame_number, "image_width": 1280, "image_height": 720,
            "detections": [
                {"class_name": label, "box_xyxy": [100 + i * 60, 100, 140 + i * 60, 200]}
                for i, label in enumerate(classes)
            ],
        },
    }


def main() -> None:
    with TemporaryDirectory(prefix="aitl-emergency-") as temp:
        root = Path(temp)
        crosses = CrosswalkService(config_path=root / "crosswalks.json")
        items = [crosswalk("cross_a", "sim_a"), crosswalk("cross_b", "sim_b")]
        route = {
            "id": "link_1", "source_crosswalk_id": "cross_a",
            "destination_crosswalk_id": "cross_b", "source_edge": "1", "destination_edge": "3",
        }

        def save_links(links: list[dict]) -> None:
            crosses.save({"schema_version": 1, "crosswalks": items,
                          "network": {"positions": {}, "links": links}})

        save_links([route])
        rules = SignalRulesService(config_path=root / "rules.json", history_path=root / "global.jsonl")
        config = rules.get_config()
        config["mode"] = "fixed"
        rules.save_config(config)
        clock = [100.0]
        service = CrosswalkSignalService(
            crosswalks=crosses, shared_rules=rules,
            clock=lambda: clock[0], history_root=root / "crosswalk_history",
        )
        service.ingest_camera_results({"sim_a": detected("sim_a", 1, ["ambulance"])},
                                      simulation_enabled=True, model_id="demo")
        clock[0] += 1.1
        service.ingest_camera_results({"sim_a": detected("sim_a", 2, ["ambulance"])},
                                      simulation_enabled=True, model_id="demo")
        assert service.status(simulation_enabled=True)["crosswalks"]["cross_b"]["emergency_priority"] is None

        route["emergency_route"] = "source_to_destination"
        save_links([route])
        clock[0] += 1.1
        service.ingest_camera_results({"sim_a": detected("sim_a", 3, ["ambulance"])},
                                      simulation_enabled=True, model_id="demo")
        status = service.status(simulation_enabled=True)
        priority = status["crosswalks"]["cross_b"]["emergency_priority"]
        assert priority and priority["source_crosswalk_id"] == "cross_a", status
        target = status["crosswalks"]["cross_b"]["signal"]
        assert target["vehicle_go"] is True and target["emergency_priority_active"], target
        assert target["effective_duration_seconds"] <= 30
        assert status["hardware_actuation_enabled"] is False

        # Must never skip the protected pedestrian clearance after an emergency request.
        protected = SignalRulesService(config_path=rules.config_path, history_path=root / "protected.jsonl")
        protected.signal_state(26.0)
        assert protected.request_simulated_emergency_vehicle(26.0, "cross_a") is True
        next_state = protected.signal_state(26.1)
        assert next_state["phase"] == "pedestrian_flashing" and next_state["vehicle_go"] is False

        duplicate = {**route, "id": "link_2", "source_edge": "2", "destination_edge": "4"}
        try:
            save_links([route, duplicate])
        except AppError as exc:
            assert exc.status_code == 422
        else:
            raise AssertionError("Multiple ambiguous emergency routes were accepted")
        service.status(simulation_enabled=False, virtual_preview=False)
        assert service.status(simulation_enabled=False)["crosswalks"]["cross_b"]["signal"] is None

    print("[PASS] emergency corridor opt-in, protected clearance and unique route validation")
    print("[PASS] priority remains a software-only virtual signal request")


if __name__ == "__main__":
    main()
