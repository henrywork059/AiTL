"""FastAPI contract checks for V017 zones, traffic, settings, and real logs."""
from __future__ import annotations

import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "apps" / "pc-studio" / "backend"
sys.path.insert(0, str(BACKEND_ROOT))


def main() -> int:
    with TemporaryDirectory(prefix="aitl-v017-api-") as temporary_directory:
        temporary_root = Path(temporary_directory)
        os.environ["AITL_ZONE_CONFIG"] = str(temporary_root / "zones.json")
        os.environ["AITL_RUNTIME_SETTINGS"] = str(temporary_root / "runtime_settings.json")

        from fastapi.testclient import TestClient  # noqa: E402
        from app.main import app  # noqa: E402

        client = TestClient(app)

        zones = client.get("/api/zones/active", headers={"X-Request-ID": "req_zones"})
        assert zones.status_code == 200
        zones_payload = zones.json()
        assert zones_payload["ok"] is True
        assert zones_payload["meta"]["request_id"] == "req_zones"
        assert zones_payload["data"]["editable"] is True
        assert len(zones_payload["data"]["zones"]) >= 4

        saved_zones = client.put(
            "/api/zones/active",
            json={"zones": zones_payload["data"]["zones"][:3]},
        )
        assert saved_zones.status_code == 200
        assert saved_zones.json()["data"]["source"] == "persisted"

        invalid_zone = client.put(
            "/api/zones/active",
            json={"zones": [{"id": "bad", "type": "crossing", "label": "Bad", "polygon": [[0, 0], [1, 1]]}]},
        )
        assert invalid_zone.status_code == 422
        assert invalid_zone.json()["error"]["code"] == "ATL-ZONE-001"

        settings = client.put(
            "/api/settings/runtime",
            json={
                "default_confidence": 0.2,
                "live_poll_interval_ms": 800,
                "training_patience": 6,
                "log_level": "INFO",
            },
        )
        assert settings.status_code == 200
        assert settings.json()["data"]["training_patience"] == 6
        assert client.get("/api/settings/runtime").json()["data"]["default_confidence"] == 0.2

        traffic = client.get("/api/traffic/state")
        assert traffic.status_code == 200
        assert traffic.json()["data"]["prototype_only"] is True
        assert traffic.json()["data"]["decision"] in {
            "await_live_detections",
            "hold_pedestrian_phase",
            "prepare_pedestrian_green",
            "extend_vehicle_green",
            "hold_vehicle_green",
        }

        logs = client.get("/api/logs/recent?limit=20")
        assert logs.status_code == 200
        assert logs.json()["data"]["status"] == "ready"
        assert isinstance(logs.json()["data"]["logs"], list)
        assert logs.headers.get("x-request-id")

    print("[PASS] zone API persists validated polygons and uses stable errors")
    print("[PASS] runtime settings API persists active values")
    print("[PASS] traffic API returns simulation-only live-zone state")
    print("[PASS] recent-log API returns real buffered records and request IDs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
