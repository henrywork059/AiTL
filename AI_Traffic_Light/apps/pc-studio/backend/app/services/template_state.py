from __future__ import annotations

from typing import Any


PC_STUDIO_PAGES: list[dict[str, Any]] = [
    {"id": "dashboard", "label": "Dashboard", "status": "test-ready"},
    {"id": "live_ai", "label": "Live AI", "status": "test-ready"},
    {"id": "camera_sources", "label": "Camera Sources", "status": "test-ready"},
    {"id": "zone_editor", "label": "Zone Editor", "status": "test-ready"},
    {"id": "traffic_logic", "label": "Traffic Logic", "status": "test-ready"},
    {"id": "dataset_capture", "label": "Dataset Capture", "status": "test-ready"},
    {"id": "dataset_review", "label": "Dataset Review", "status": "test-ready"},
    {"id": "train_export", "label": "Train / Export", "status": "test-ready"},
    {"id": "model_registry", "label": "Model Registry", "status": "test-ready"},
    {"id": "settings", "label": "Settings", "status": "test-ready"},
    {"id": "logs", "label": "Logs", "status": "test-ready"},
]


def get_template_summary() -> dict[str, Any]:
    """Return PC Studio pages and current implementation status."""
    return {
        "version": "0_2_0",
        "mode": "camera_aligned_zones_and_capture_lifecycle_test_ready",
        "pages": PC_STUDIO_PAGES,
        "implementation_note": (
            "All main PC Studio pages expose working prototype behavior: live/camera tools, camera-aligned persistent zones, "
            "Live AI zone/signal overlays, zone-aware simulation decisions, capture deletion, labeling/training/model management, "
            "runtime settings, and real recent logs. Training includes convergence history and early stopping. Model export, automatic labeling, "
            "and physical public-road control remain disabled."
        ),
    }
