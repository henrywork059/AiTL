from __future__ import annotations

from typing import Any


PC_STUDIO_PAGES: list[dict[str, Any]] = [
    {"id": "dashboard", "label": "Dashboard", "status": "test-ready"},
    {"id": "live_ai", "label": "Live AI", "status": "mock"},
    {"id": "camera_sources", "label": "Camera Sources", "status": "test-ready"},
    {"id": "zone_editor", "label": "Zone Editor", "status": "template"},
    {"id": "traffic_logic", "label": "Traffic Logic", "status": "mock"},
    {"id": "dataset_capture", "label": "Dataset Capture", "status": "test-ready"},
    {"id": "dataset_review", "label": "Dataset Review", "status": "test-ready"},
    {"id": "train_export", "label": "Train / Export", "status": "test-ready"},
    {"id": "model_registry", "label": "Model Registry", "status": "template"},
    {"id": "settings", "label": "Settings", "status": "template"},
    {"id": "logs", "label": "Logs", "status": "mock"},
]


def get_template_summary() -> dict[str, Any]:
    """Return PC Studio pages and current implementation status."""
    return {
        "version": "0_1_3",
        "mode": "manual_labeling_test_ready",
        "pages": PC_STUDIO_PAGES,
        "implementation_note": "The app can capture, manually label, and build a managed YOLO dataset. Optional YOLO training uses labeled data; automatic labeling, live inference, and physical traffic control remain disabled.",
    }
