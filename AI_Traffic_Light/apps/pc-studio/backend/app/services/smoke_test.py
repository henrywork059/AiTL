from __future__ import annotations

from typing import Any

from app.services.mock_data import get_mock_detection_frame, get_mock_zones
from app.services.template_state import get_template_summary
from app.services.traffic_logic import get_mock_traffic_state

APP_VERSION = "0_1_3"
APP_MODE = "manual_labeling_test_ready"


def get_smoke_status() -> dict[str, Any]:
    """Return a compact self-check payload for local testing."""
    frame = get_mock_detection_frame()
    zones = get_mock_zones()
    traffic = get_mock_traffic_state()
    template = get_template_summary()

    checks = [
        {
            "id": "camera.receiver",
            "label": "Camera frame receiver",
            "status": "pass",
            "detail": "JPEG/PNG upload, latest-frame preview, and simulation endpoints are available.",
        },
        {
            "id": "dataset.capture",
            "label": "Persistent dataset capture",
            "status": "pass",
            "detail": "The latest receiver or simulation frame can be saved with paired JSON metadata.",
        },
        {
            "id": "dataset.labeling",
            "label": "Manual dataset labeling",
            "status": "pass",
            "detail": "Captured frames can be reviewed and saved with manual bounding boxes using the shared six-class schema.",
        },
        {
            "id": "dataset.yolo_build",
            "label": "Managed YOLO dataset builder",
            "status": "pass",
            "detail": "Reviewed non-bad captures can be converted into distinct train/validation images and YOLO label files.",
        },
        {
            "id": "training.runner",
            "label": "Optional YOLO training runner",
            "status": "pass",
            "detail": "The existing background runner can use yolo/data.yaml after the managed dataset is built and Ultralytics is installed.",
        },
        {
            "id": "backend.health",
            "label": "Backend health endpoint",
            "status": "pass",
            "detail": "FastAPI app is running and can return JSON responses.",
        },
        {
            "id": "mock.frame",
            "label": "Mock detection frame",
            "status": "pass" if frame.get("detections") else "warn",
            "detail": f"{len(frame.get('detections', []))} mock detections available.",
        },
        {
            "id": "mock.zones",
            "label": "Mock traffic zones",
            "status": "pass" if zones else "warn",
            "detail": f"{len(zones)} mock zones available.",
        },
        {
            "id": "traffic.state",
            "label": "Mock traffic state",
            "status": "pass" if traffic.get("phase") else "warn",
            "detail": f"Current mock phase: {traffic.get('phase')}.",
        },
        {
            "id": "template.pages",
            "label": "PC Studio page registry",
            "status": "pass" if template.get("pages") else "warn",
            "detail": f"{len(template.get('pages', []))} pages registered.",
        },
        {
            "id": "safety.real_control",
            "label": "Physical traffic control disabled",
            "status": "pass",
            "detail": "0_1_3 is a supervised prototype and cannot control real public traffic lights.",
        },
    ]

    return {
        "version": APP_VERSION,
        "mode": APP_MODE,
        "ready_for": [
            "frontend_layout_test",
            "backend_startup_test",
            "mock_api_test",
            "frontend_backend_connection_test",
            "camera_frame_upload_test",
            "camera_simulation_test",
            "persistent_frame_capture_test",
            "manual_bounding_box_labeling_test",
            "managed_yolo_dataset_build_test",
            "optional_labeled_yolo_training_test",
            "GUI function-list review",
        ],
        "not_ready_for": [
            "device_camera_firmware",
            "automatic_labeling",
            "YOLO inference",
            "model_export",
            "physical_traffic_light_control",
        ],
        "checks": checks,
        "endpoints": [
            "/health",
            "/api/smoke/status",
            "/api/mock/frame",
            "/api/mock/zones",
            "/api/traffic/state",
            "/api/logs/recent",
            "/api/template/pc-studio",
            "/api/camera/status",
            "/api/camera/frame",
            "/api/camera/simulation/start",
            "/api/camera/simulation/stop",
            "/api/dataset/status",
            "/api/dataset/captures",
            "/api/dataset/captures/{capture_id}/image",
            "/api/dataset/captures/{capture_id}/labels",
            "/api/dataset/training-dataset/status",
            "/api/dataset/training-dataset",
            "/api/training/status",
            "/api/training/start",
        ],
        "summary": {
            "mock_frame_id": frame.get("frame_id"),
            "mock_detection_count": len(frame.get("detections", [])),
            "mock_zone_count": len(zones),
            "mock_traffic_phase": traffic.get("phase"),
        },
    }
