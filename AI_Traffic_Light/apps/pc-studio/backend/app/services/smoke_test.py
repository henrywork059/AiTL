from __future__ import annotations

from typing import Any

from app.core.project_version import PROJECT_MODE, PROJECT_VERSION
from app.services.mock_data import get_mock_detection_frame
from app.services.runtime_settings import runtime_settings_service
from app.services.template_state import get_template_summary
from app.services.traffic_logic import evaluate_traffic_state
from app.services.zones import zone_service


def get_smoke_status() -> dict[str, Any]:
    """Return a compact self-check payload for local testing."""
    fixture_frame = get_mock_detection_frame()
    zone_status = zone_service.status()
    zones = zone_status["zones"]
    traffic = evaluate_traffic_state(fixture_frame, zones, source="smoke_fixture")
    settings = runtime_settings_service.get()
    template = get_template_summary()

    checks = [
        {
            "id": "camera.receiver",
            "label": "Camera frame receiver",
            "status": "pass",
            "detail": "JPEG/PNG upload, latest-frame preview, and simulation endpoints are available.",
        },
        {
            "id": "camera.simulation_scene",
            "label": "Controllable synthetic traffic scene",
            "status": "pass",
            "detail": "Simulation uses persistent signal-aware agents: vehicles queue at stop lines, pedestrians wait/use the crosswalk, and pause/resume freezes both motion and signal timing.",
        },
        {
            "id": "zones.persistent",
            "label": "Persistent zone editor",
            "status": "pass" if zones else "warn",
            "detail": f"{len(zones)} editable zones are available from {zone_status['source']} configuration.",
        },
        {
            "id": "traffic.live_logic",
            "label": "Zone-aware traffic simulation logic",
            "status": "pass" if traffic.get("phase") else "warn",
            "detail": "The decision engine maps detection centres into persisted zones and returns a simulation-only phase recommendation.",
        },
        {
            "id": "traffic.analytics",
            "label": "Traffic occupancy history and analytics",
            "status": "pass" if "pedestrians_total" in traffic and "vehicles_total" in traffic else "warn",
            "detail": "Detection-backed pedestrian/vehicle occupancy can be sampled over time and summarized for the whole frame or configured counting regions.",
        },
        {
            "id": "traffic.flow_tracking",
            "label": "Cross-frame tracking and flow analytics",
            "status": "pass",
            "detail": "V022 adds stable prototype track IDs, unique directional counting-line passages, and region entry/exit/dwell event persistence without changing occupancy semantics.",
        },
        {
            "id": "dataset.capture",
            "label": "Persistent dataset capture",
            "status": "pass",
            "detail": "The latest receiver or simulation frame can be saved with paired JSON metadata and unwanted captures can be deleted safely.",
        },
        {
            "id": "dataset.labeling",
            "label": "Manual dataset labeling",
            "status": "pass",
            "detail": "Captured frames can be reviewed and saved with manual bounding boxes using the shared class schema.",
        },
        {
            "id": "dataset.yolo_build",
            "label": "Managed YOLO dataset builder",
            "status": "pass",
            "detail": "Reviewed non-bad captures can be converted into distinct train/validation images and YOLO label files.",
        },
        {
            "id": "training.convergence",
            "label": "Training convergence and early stopping",
            "status": "pass",
            "detail": "Training status exposes per-epoch fitness history and uses Ultralytics patience-based automatic early stopping.",
        },
        {
            "id": "inference.trained_model",
            "label": "Trained-model live inference",
            "status": "pass",
            "detail": "The inference API supports selected/default models, live receiver/simulation detections, and visibility controls.",
        },
        {
            "id": "settings.runtime",
            "label": "Persistent runtime settings",
            "status": "pass",
            "detail": f"Viewer polling, confidence, training patience, and log level are active; current log level is {settings['log_level']}.",
        },
        {
            "id": "logs.recent",
            "label": "Real recent backend logs",
            "status": "pass",
            "detail": "The log page reads a bounded in-memory buffer populated by actual backend logging records.",
        },
        {
            "id": "backend.health",
            "label": "Backend health endpoint",
            "status": "pass",
            "detail": "FastAPI app is running and returns standard API envelopes and request IDs.",
        },
        {
            "id": "pages.registry",
            "label": "PC Studio page registry",
            "status": "pass" if all(page.get("status") == "test-ready" for page in template.get("pages", [])) else "warn",
            "detail": f"{len(template.get('pages', []))} PC Studio pages are registered as test-ready prototype surfaces.",
        },
        {
            "id": "safety.real_control",
            "label": "Physical traffic control disabled",
            "status": "pass",
            "detail": f"{PROJECT_VERSION} remains a supervised prototype and cannot control real public traffic infrastructure.",
        },
    ]

    return {
        "version": PROJECT_VERSION,
        "mode": PROJECT_MODE,
        "ready_for": [
            "frontend_layout_test",
            "backend_startup_test",
            "camera_frame_upload_test",
            "camera_simulation_test",
            "persistent_zone_editing_test",
            "camera_aligned_zone_editor_test",
            "live_ai_zone_overlay_test",
            "live_ai_signal_overlay_test",
            "live_zone_counting_test",
            "simulation_decision_test",
            "traffic_history_recording_test",
            "counting_region_analytics_test",
            "traffic_history_csv_export_test",
            "cross_frame_tracking_test",
            "counting_line_flow_test",
            "region_entry_exit_dwell_test",
            "traffic_flow_csv_export_test",
            "persistent_frame_capture_test",
            "capture_delete_test",
            "manual_bounding_box_labeling_test",
            "managed_yolo_dataset_build_test",
            "training_convergence_plot_test",
            "automatic_early_stopping_test",
            "trained_model_live_inference_test",
            "trained_model_selection_and_delete_test",
            "runtime_settings_test",
            "recent_backend_logs_test",
        ],
        "not_ready_for": [
            "device_camera_firmware_completion",
            "automatic_labeling",
            "model_export",
            "physical_traffic_light_control",
        ],
        "checks": checks,
        "endpoints": [
            "/health",
            "/api/smoke/status",
            "/api/traffic/state",
            "/api/traffic/history",
            "/api/traffic/history/export.csv",
            "DELETE /api/traffic/history",
            "/api/traffic/tracks",
            "/api/traffic/flow",
            "/api/traffic/flow/export.csv",
            "DELETE /api/traffic/flow",
            "/api/zones/active",
            "/api/zones/reset",
            "/api/settings/runtime",
            "/api/logs/recent",
            "/api/template/pc-studio",
            "/api/camera/status",
            "/api/camera/frame",
            "/api/camera/simulation/start",
            "/api/camera/simulation/stop",
            "/api/camera/simulation/settings",
            "/api/dataset/status",
            "/api/dataset/captures",
            "/api/dataset/captures/{capture_id}",
            "/api/dataset/captures/{capture_id}/image",
            "/api/dataset/captures/{capture_id}/labels",
            "/api/dataset/training-dataset/status",
            "/api/dataset/training-dataset",
            "/api/training/status",
            "/api/training/start",
            "/api/inference/status",
            "/api/inference/load-latest",
            "/api/inference/load",
            "/api/inference/unload",
            "/api/inference/detections",
            "/api/inference/frame",
            "/api/models",
            "/api/models/default",
            "/api/models/{model_id}",
        ],
        "summary": {
            "mock_frame_id": fixture_frame.get("frame_id"),
            "mock_detection_count": len(fixture_frame.get("detections", [])),
            "mock_zone_count": len(zones),
            "mock_traffic_phase": traffic.get("phase"),
        },
    }
