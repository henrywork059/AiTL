from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
import tempfile

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "apps" / "pc-studio" / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from app.core.error_codes import ErrorCode  # noqa: E402
from app.core.exceptions import AppError  # noqa: E402
from app.services.decision_context import build_decision_context  # noqa: E402
from app.services.intersection_network import IntersectionNetworkService  # noqa: E402


def expect_invalid(service: IntersectionNetworkService, config: dict) -> None:
    try:
        service.save(config)
    except AppError as exc:
        assert exc.code == ErrorCode.TRAFFIC_NETWORK_INVALID
    else:
        raise AssertionError("Invalid intersection network configuration should be rejected.")


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="aitl_network_test_") as temporary:
        path = Path(temporary) / "intersections.json"
        service = IntersectionNetworkService(config_path=path)

        defaults = service.get()
        assert defaults["schema_version"] == 1
        assert defaults["active_intersection_id"] == "intersection_main"
        resolved = service.resolve_source("unknown_camera")
        assert resolved["intersection_id"] == "intersection_main"
        assert resolved["source_mapping_matched"] is False

        config = {
            "schema_version": 1,
            "active_intersection_id": "intersection_a",
            "intersections": [
                {
                    "id": "intersection_a",
                    "label": "Intersection A",
                    "enabled": True,
                    "source_ids": ["camera_a"],
                    "zone_ids": ["a_queue"],
                    "signal_profile": "Normal",
                },
                {
                    "id": "intersection_b",
                    "label": "Intersection B",
                    "enabled": True,
                    "source_ids": ["camera_b", "1camera_b"],
                    "zone_ids": ["b_queue"],
                    "signal_profile": "Vehicle Priority",
                },
                {
                    "id": "intersection_c",
                    "label": "Intersection C",
                    "enabled": False,
                    "source_ids": [],
                    "zone_ids": [],
                    "signal_profile": "Normal",
                },
            ],
            "links": [
                {
                    "id": "a_to_b",
                    "enabled": True,
                    "source_intersection_id": "intersection_a",
                    "destination_intersection_id": "intersection_b",
                    "source_approach": "eastbound",
                    "destination_approach": "westbound",
                    "travel_time_seconds": 12.5,
                },
                {
                    "id": "b_to_c",
                    "enabled": True,
                    "source_intersection_id": "intersection_b",
                    "destination_intersection_id": "intersection_c",
                    "source_approach": "southbound",
                    "destination_approach": "northbound",
                    "travel_time_seconds": 18,
                },
            ],
        }
        saved = service.save(config)
        assert path.is_file()
        assert saved == service.get()
        assert service.resolve_source("camera_b")["intersection_id"] == "intersection_b"
        assert service.resolve_source("1camera_b")["intersection_id"] == "intersection_b"
        context_b = service.context("intersection_b")
        assert context_b["neighbor_count"] == 2
        assert {item["neighbor_intersection_id"] for item in context_b["neighbors"]} == {
            "intersection_a",
            "intersection_c",
        }
        assert context_b["cooperative_control_active"] is False

        reloaded = IntersectionNetworkService(config_path=path)
        assert reloaded.get() == saved

        duplicate_source = deepcopy(config)
        duplicate_source["intersections"][2]["source_ids"] = ["camera_a"]
        expect_invalid(service, duplicate_source)

        missing_target = deepcopy(config)
        missing_target["links"][0]["destination_intersection_id"] = "missing"
        expect_invalid(service, missing_target)

        self_link = deepcopy(config)
        self_link["links"][0]["destination_intersection_id"] = "intersection_a"
        expect_invalid(service, self_link)

        resolution = service.resolve_source("camera_a")
        traffic_state = {
            "phase": "vehicle_green",
            "decision": "follow_simulation_signal",
            "recommended_phase": "vehicle_green",
            "recommended_decision": "extend_vehicle_green",
            "pedestrians_waiting": 2,
            "pedestrians_crossing": 0,
            "vehicles_waiting": 5,
            "vehicles_total": 7,
            "evaluated_frame_number": 42,
            "source_timestamp_ms": 123456,
            "signal_policy": {
                "mode": "adaptive",
                "base_duration_seconds": 12.0,
                "effective_duration_seconds": 17.0,
                "seconds_remaining": 9.0,
                "pending_request": "vehicle",
                "winning_scenario_id": "busy_queue",
                "winning_scenario_label": "Busy queue",
                "scenario_status": [
                    {
                        "scenario_id": "busy_queue",
                        "conditions": [
                            {
                                "source": "zone_class_count",
                                "label": "car in a_queue",
                                "operator": "gte",
                                "threshold": 4,
                                "observed": 5,
                                "matched": True,
                                "available": True,
                            }
                        ],
                    }
                ],
                "test_inputs": {},
            },
        }
        decision = build_decision_context(
            traffic_state,
            network_resolution=resolution,
            simulation_enabled=True,
        )
        assert decision["intersection_id"] == "intersection_a"
        assert decision["observation_provenance"] == "simulation"
        assert decision["scenario"]["id"] == "busy_queue"
        assert decision["scenario"]["conditions"][0]["observed"] == 5
        assert decision["neighbor_context"][0]["neighbor_intersection_id"] == "intersection_b"
        assert decision["emergency_context"]["active"] is False
        assert decision["cooperative_control_active"] is False
        assert decision["decision_id"].startswith("dec_")
        assert "highest-ranked eligible scenario" in decision["explanation"]

    print("intersection network foundation tests passed")


if __name__ == "__main__":
    main()
