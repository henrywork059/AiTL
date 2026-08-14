from __future__ import annotations

from typing import Any


PC_STUDIO_PAGES: list[dict[str, Any]] = [
    {"id": "dashboard", "label": "Dashboard", "status": "test-ready"},
    {"id": "live_ai", "label": "Live AI", "status": "test-ready"},
    {"id": "camera_sources", "label": "Camera Sources", "status": "test-ready"},
    {"id": "zone_editor", "label": "Zone Editor", "status": "template"},
    {"id": "traffic_logic", "label": "Traffic Logic", "status": "mock"},
    {"id": "dataset_capture", "label": "Dataset Capture", "status": "test-ready"},
    {"id": "dataset_review", "label": "Dataset Review", "status": "test-ready"},
    {"id": "train_export", "label": "Train / Export", "status": "test-ready"},
    {"id": "model_registry", "label": "Model Registry", "status": "test-ready"},
    {"id": "settings", "label": "Settings", "status": "template"},
    {"id": "logs", "label": "Logs", "status": "mock"},
]


def get_template_summary() -> dict[str, Any]:
    """Return PC Studio pages and current implementation status."""
    return {
        "version": "0_1_6",
        "mode": "simulation_scene_controls_test_ready",
        "pages": PC_STUDIO_PAGES,
        "implementation_note": "The app can receive/simulate and capture frames, manually label data, build/train a managed YOLO dataset, manage trained models, run live receiver/simulation inference, and adjust or freeze the synthetic scene. Automatic labeling, live zone counting, and physical traffic control remain disabled.",
    }
