"""Filesystem-isolated checks for manual labels and the managed YOLO dataset builder."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "apps" / "pc-studio" / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from app.core.error_codes import ErrorCode  # noqa: E402
from app.core.exceptions import AppError  # noqa: E402
from app.services.dataset_labeling import DatasetLabelingService  # noqa: E402


CLASSES = {
    "classes": [
        {"id": 0, "name": "person", "category": "pedestrian"},
        {"id": 1, "name": "car", "category": "vehicle"},
        {"id": 2, "name": "bus", "category": "vehicle"},
        {"id": 3, "name": "truck", "category": "vehicle"},
        {"id": 4, "name": "motorcycle", "category": "vehicle"},
        {"id": 5, "name": "bicycle", "category": "vehicle"},
    ]
}


def write_capture(dataset_root: Path, capture_id: str, *, session: str, quality: str) -> None:
    image_path = dataset_root / "captures" / session / "images" / f"{capture_id}.png"
    metadata_path = dataset_root / "captures" / session / "metadata" / f"{capture_id}.json"
    image_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    image_path.write_bytes(b"\x89PNG\r\n\x1a\nfixture")
    metadata = {
        "capture_id": capture_id,
        "session_id": session,
        "source_id": "test",
        "origin": "simulation",
        "content_type": "image/png",
        "width": 100,
        "height": 80,
        "source_frame_number": 1,
        "source_received_at_ms": 1,
        "captured_at_ms": 1,
        "size_bytes": image_path.stat().st_size,
        "quality_tag": quality,
        "note": "label test",
        "image_path": image_path.relative_to(dataset_root).as_posix(),
        "metadata_path": metadata_path.relative_to(dataset_root).as_posix(),
    }
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")


def main() -> int:
    with TemporaryDirectory(prefix="aitl-label-test-") as temporary_directory:
        root = Path(temporary_directory)
        dataset_root = root / "datasets"
        class_schema = root / "classes.default.json"
        class_schema.write_text(json.dumps(CLASSES), encoding="utf-8")

        write_capture(dataset_root, "capture_positive", session="acceptance", quality="useful")
        write_capture(dataset_root, "capture_negative", session="acceptance", quality="unreviewed")
        write_capture(dataset_root, "capture_bad", session="acceptance", quality="bad")

        service = DatasetLabelingService(dataset_root=dataset_root, class_schema_path=class_schema)
        positive = service.save_labels(
            "capture_positive",
            [{"class_id": 0, "box_xyxy": [10, 8, 60, 48]}],
        )
        assert positive["labels"][0]["class_name"] == "person"
        negative = service.save_labels("capture_negative", [])
        assert negative["reviewed"] is True and negative["labels"] == []
        service.save_labels(
            "capture_bad",
            [{"class_id": 1, "box_xyxy": [20, 10, 70, 50]}],
        )

        capture_list = service.list_captures()
        assert capture_list["total"] == 3
        assert len(capture_list["classes"]) == 6
        assert all(item["labeled"] for item in capture_list["captures"])

        try:
            service.save_labels(
                "capture_positive",
                [{"class_id": 0, "box_xyxy": [-1, 0, 20, 20]}],
            )
            raise AssertionError("Out-of-bounds label should fail")
        except AppError as exc:
            assert exc.code == ErrorCode.DATASET_LABEL_INVALID

        before = service.training_dataset_status()
        assert before["labeled_frame_count"] == 3
        assert before["eligible_frame_count"] == 2
        assert before["excluded_bad_count"] == 1
        assert before["ready"] is False

        built = service.build_training_dataset(validation_fraction=0.2)
        assert built["ready"] is True
        assert built["train_count"] == 1 and built["val_count"] == 1
        assert (dataset_root / "yolo" / "data.yaml").is_file()
        assert (dataset_root / "yolo" / "manifest.json").is_file()
        copied_images = list((dataset_root / "yolo" / "images").glob("*/*"))
        assert len(copied_images) == 2
        assert all("capture_bad" not in path.name for path in copied_images)
        label_files = list((dataset_root / "yolo" / "labels").glob("*/*.txt"))
        assert len(label_files) == 2
        label_text = "\n".join(path.read_text(encoding="utf-8") for path in label_files)
        assert "0 0.350000 0.350000 0.500000 0.500000" in label_text

        service.save_labels(
            "capture_positive",
            [{"class_id": 0, "box_xyxy": [12, 8, 60, 48]}],
        )
        stale = service.training_dataset_status()
        assert stale["ready"] is False and stale["stale"] is True
        rebuilt = service.build_training_dataset(validation_fraction=0.2)
        assert rebuilt["ready"] is True and rebuilt["stale"] is False

    print("[PASS] manual labels persist with shared class names")
    print("[PASS] reviewed zero-box negative frames remain eligible")
    print("[PASS] bad-quality captures are excluded from YOLO builds")
    print("[PASS] managed train/validation split and normalized labels are generated")
    print("[PASS] label edits mark the managed dataset stale until rebuilt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
