from __future__ import annotations

from typing import Any


PC_STUDIO_PAGES: list[dict[str, Any]] = [
    {"id": "dashboard", "label": "Dashboard", "status": "template"},
    {"id": "live_ai", "label": "Live AI", "status": "template"},
    {"id": "camera_sources", "label": "Camera Sources", "status": "template"},
    {"id": "zone_editor", "label": "Zone Editor", "status": "template"},
    {"id": "traffic_logic", "label": "Traffic Logic", "status": "template"},
    {"id": "dataset_capture", "label": "Dataset Capture", "status": "template"},
    {"id": "dataset_review", "label": "Dataset Review", "status": "template"},
    {"id": "train_export", "label": "Train / Export", "status": "template"},
    {"id": "model_registry", "label": "Model Registry", "status": "template"},
    {"id": "settings", "label": "Settings", "status": "template"},
    {"id": "logs", "label": "Logs", "status": "template"},
]


def get_template_summary() -> dict[str, Any]:
    """Return planned PC Studio pages and placeholder implementation status."""
    return {
        "version": "0_0_4",
        "mode": "template_only",
        "pages": PC_STUDIO_PAGES,
        "implementation_note": "This endpoint confirms app shape only. Real camera, AI, dataset, and training logic are intentionally not implemented yet.",
    }
