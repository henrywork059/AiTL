"""Static integration guards for camera-to-crosswalk background routing."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
def source(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")

def main() -> None:
    worker = source("apps/pc-studio/backend/app/services/multi_camera_inference.py")
    adapter = source("apps/pc-studio/backend/app/services/crosswalk_observations.py")
    controllers = source("apps/pc-studio/backend/app/services/crosswalk_signals.py")
    scenario = source("apps/pc-studio/backend/app/services/signal_rules.py")
    adjustments = source("apps/pc-studio/frontend/src/pages/LiveSignalAdjustmentsPage.tsx")
    network = source("apps/pc-studio/frontend/src/components/CrosswalkNetworkPanel.tsx")
    assert "crosswalk_signal_service.ingest_camera_results(" in worker
    assert "virtual_preview=virtual_preview" in worker
    assert "virtual_preview_enabled" in controllers
    assert "snapshot = dict(self._results)" in worker
    assert 'camera_side_" + side + "_id"' in adapter
    assert "MAX_FRAME_AGE_MS = 5000" in adapter
    assert "MAX_SIDE_SKEW_MS = 2000" in adapter
    assert "region_class_counts" in adapter
    assert 'available_metrics": []' in adapter
    assert "controller.clear_observation()" in controllers
    assert 'observation_provenance": "unavailable"' in controllers
    assert "available_metrics" in scenario
    assert "fetchCrosswalks()" in adjustments
    assert 'crosswalk.id + ":" + region.id' in adjustments
    assert "crosswalkSignal?.observation_provenance" in network
    assert '"coordination_enabled": running and emergency_routes_enabled' in controllers
    assert '"hardware_actuation_enabled": False' in controllers
    print("[PASS] background camera routing, stale guards, safe regional class counts and UI wiring")


if __name__ == "__main__":
    main()
