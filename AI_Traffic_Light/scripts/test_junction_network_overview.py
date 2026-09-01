from pathlib import Path
import sys
import tempfile

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "apps" / "pc-studio" / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.exceptions import AppError
from app.services.intersection_network import IntersectionNetworkService
from app.services.junction_network_overview import JunctionNetworkOverviewService


class FakeFrame:
    source_id = "esp_a"


class FakeCameraManager:
    def status(self, *, refresh_device: bool = False) -> dict:
        assert refresh_device is False
        return {
            "active_source_id": "esp_a",
            "registry_warning": None,
            "cameras": [
                {
                    "source_id": "esp_a",
                    "host": "192.168.1.10",
                    "target_fps": 15,
                    "settings": {},
                    "last_used_ms": 100,
                    "selected": True,
                    "connected": True,
                    "device_reachable": True,
                    "streaming": True,
                    "stream_connected": True,
                    "measured_fps": 11.8,
                    "last_success_at_ms": 12345,
                    "last_error": None,
                },
                {
                    "source_id": "esp_b",
                    "host": "192.168.1.11",
                    "target_fps": 15,
                    "settings": {},
                    "last_used_ms": 90,
                    "selected": False,
                    "connected": False,
                    "device_reachable": False,
                    "streaming": False,
                    "stream_connected": False,
                    "measured_fps": 0.0,
                    "last_success_at_ms": None,
                    "last_error": "camera offline",
                },
            ],
        }


class CountingOverviewService(JunctionNetworkOverviewService):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.remote_camera_projection_count = 0

    def _remote_camera_view(self, camera: dict) -> dict:  # type: ignore[override]
        self.remote_camera_projection_count += 1
        return JunctionNetworkOverviewService._remote_camera_view(camera)


def fake_traffic_state() -> dict:
    return {
        "phase": "pedestrian_green",
        "pedestrians_waiting": 3,
        "pedestrians_crossing": 1,
        "vehicles_waiting": 5,
        "pedestrians_total": 4,
        "vehicles_total": 9,
        "decision": "follow_simulation_signal",
        "decision_reason": "Prototype test decision",
        "extension_seconds": 3,
        "data_source": "live_zone_evaluation",
        "evaluated_at_ms": 20000,
        "source_timestamp_ms": 19950,
        "evaluated_frame_number": 42,
        "zone_counts": {},
        "zone_class_counts": {},
        "region_counts": {},
        "tracking": {},
        "signal_policy": {
            "mode": "adaptive",
            "winning_scenario_id": "scenario_busy",
            "winning_scenario_label": "Busy crossing",
            "scenario_status": [],
            "service_request": {"active": True, "service": "pedestrian"},
            "test_inputs": {},
        },
        "prototype_only": True,
    }


def main() -> int:
    with tempfile.TemporaryDirectory() as temporary:
        config_path = Path(temporary) / "intersections.json"
        network = IntersectionNetworkService(config_path=config_path)

        saved = network.save(
            {
                "schema_version": 1,
                "active_intersection_id": "junction_a",
                "intersections": [
                    {
                        "id": "junction_a",
                        "label": "Junction A",
                        "enabled": True,
                        "source_ids": ["esp_a", "esp_b"],
                        "primary_source_id": "esp_a",
                        "zone_ids": [],
                        "signal_profile": "Normal",
                        "position": {"x": 25, "y": 50},
                    },
                    {
                        "id": "junction_b",
                        "label": "Junction B",
                        "enabled": True,
                        "source_ids": [],
                        "primary_source_id": None,
                        "zone_ids": [],
                        "signal_profile": "Normal",
                        "position": {"x": 75, "y": 50},
                    },
                ],
                "links": [
                    {
                        "id": "link_ab",
                        "enabled": True,
                        "source_intersection_id": "junction_a",
                        "destination_intersection_id": "junction_b",
                        "source_approach": "eastbound",
                        "destination_approach": "westbound",
                        "travel_time_seconds": 12,
                    }
                ],
            }
        )

        assert saved["intersections"][0]["source_ids"] == ["esp_a", "esp_b"]
        assert saved["intersections"][0]["primary_source_id"] == "esp_a"
        assert saved["intersections"][0]["position"] == {"x": 25.0, "y": 50.0}

        # Backward-compatible schema-1 configs without V0311 layout/primary
        # metadata receive deterministic defaults instead of failing to load.
        migrated = network.save(
            {
                "schema_version": 1,
                "active_intersection_id": "junction_a",
                "intersections": [
                    {
                        "id": "junction_a",
                        "label": "Junction A",
                        "enabled": True,
                        "source_ids": ["esp_a", "esp_b"],
                        "zone_ids": [],
                        "signal_profile": "Normal",
                    },
                    {
                        "id": "junction_b",
                        "label": "Junction B",
                        "enabled": True,
                        "source_ids": [],
                        "zone_ids": [],
                        "signal_profile": "Normal",
                    },
                ],
                "links": [],
            }
        )
        assert migrated["intersections"][0]["primary_source_id"] == "esp_a"
        assert migrated["intersections"][0]["position"] != migrated["intersections"][1]["position"]

        # Restore the richer graph for the live-overview assertions.
        network.save(saved)

        duplicate = {**saved, "intersections": [dict(item) for item in saved["intersections"]]}
        duplicate["intersections"][1]["source_ids"] = ["esp_a"]
        duplicate["intersections"][1]["primary_source_id"] = "esp_a"
        try:
            network.save(duplicate)
            raise AssertionError("one source must not be assignable to two junctions")
        except AppError:
            pass

        overview_service = CountingOverviewService(
            network_service=network,
            camera_manager=FakeCameraManager(),  # type: ignore[arg-type]
            traffic_state_provider=fake_traffic_state,
            frame_provider=lambda: FakeFrame(),
            simulation_provider=lambda: False,
        )
        overview = overview_service.overview()

        assert overview_service.remote_camera_projection_count == 2, (
            "each saved ESP camera should be projected once per overview, then reused for assignment"
        )
        assert overview["multi_camera_assignment"] is True
        assert overview["simultaneous_multi_junction_inference"] is False
        assert overview["observation_intersection_id"] == "junction_a"
        assert overview["source_mapping_matched"] is True
        assert overview["summary"]["junction_count"] == 2
        assert overview["summary"]["assigned_esp_camera_count"] == 2
        assert overview["summary"]["reachable_esp_camera_count"] == 1

        junction_a = next(item for item in overview["junctions"] if item["id"] == "junction_a")
        junction_b = next(item for item in overview["junctions"] if item["id"] == "junction_b")

        assert junction_a["camera_count"] == 2
        assert junction_a["reachable_camera_count"] == 1
        assert junction_a["live"]["available"] is True
        assert junction_a["live"]["vehicle"]["load"] == "heavy"
        assert junction_a["live"]["pedestrian"]["load"] == "heavy"
        assert any(item["type"] == "ranked_scenario" for item in junction_a["events"])
        assert any(item["type"] == "pedestrian_service" for item in junction_a["events"])
        assert any(item["code"] == "camera_error" for item in junction_a["warnings"])

        assert junction_b["live"]["available"] is False
        assert junction_b["live"]["vehicle"]["load"] == "unavailable"
        assert junction_b["event_count"] == 0
        assert any(item["code"] == "no_source_assigned" for item in junction_b["warnings"])

    route_source = (BACKEND_ROOT / "app" / "routes" / "traffic.py").read_text(encoding="utf-8")
    assert '@router.get("/network/overview")' in route_source
    assert "junction_network_overview_service.overview()" in route_source

    print("[PASS] junction positions and multi-camera assignments remain persistent")
    print("[PASS] each ESP camera view is projected once per overview and reused")
    print("[PASS] overview exposes camera health plus live load/events only for the shared selected pipeline junction")
    print("[PASS] unavailable junctions remain explicit and simultaneous multi-junction inference is not claimed")
    print("[PASS] /api/traffic/network/overview route remains wired through the dedicated service")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
