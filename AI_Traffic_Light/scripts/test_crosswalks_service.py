"""Verify crosswalk persistence and opposite-side camera validation."""
from copy import deepcopy
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "pc-studio" / "backend"))

from app.core.error_codes import ErrorCode  # noqa: E402
from app.core.exceptions import AppError  # noqa: E402
from app.services.crosswalks import CrosswalkService  # noqa: E402


def invalid(service: CrosswalkService, payload: dict) -> None:
    try:
        service.save(payload)
    except AppError as exc:
        assert exc.code == ErrorCode.CROSSWALK_INVALID and exc.status_code == 422
    else:
        raise AssertionError("Invalid crosswalk data was accepted.")


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="aitl_crosswalks_") as temporary:
        path = Path(temporary) / "crosswalks.json"
        service = CrosswalkService(config_path=path)
        assert service.get() == {"schema_version": 1, "crosswalks": []}
        assert not path.exists()
        item = {
            "id": "crosswalk_1", "label": "School entrance", "location": "Main gate",
            "camera_side_a_id": "esp32_cam_01", "camera_side_b_id": "esp32_cam_02",
            "regions": [{"id": "waiting_a", "label": "Waiting A", "vertices": [[300, 150], [600, 150], [600, 330], [300, 330]]}],
        }
        config = {"schema_version": 1, "crosswalks": [item, {
            "id": "crosswalk_2", "label": "Rear road", "location": "",
            "camera_side_a_id": None, "camera_side_b_id": None, "regions": [],
        }]}
        assert service.save(config) == config
        assert path.exists()
        assert CrosswalkService(config_path=path).get() == config
        for bad in (
            {"crosswalks": [item, item]},
            {"crosswalks": [{**item, "camera_side_b_id": "esp32_cam_01"}]},
            {"crosswalks": [{**item, "id": "1bad"}]},
            {"crosswalks": [{**item, "label": ""}]},
            {"crosswalks": [{**item, "camera_side_a_id": "bad id"}]},
            {"crosswalks": "invalid"},
            {"crosswalks": [{**item, "regions": [{**item["regions"][0], "vertices": [[5, 5], [10, 10], [5, 10], [10, 5]]}]}]},
            {"crosswalks": [{**item, "regions": [{**item["regions"][0], "vertices": [[1, 1], [2, 2], [3, 3]]}]}]},
            {"crosswalks": [{**item, "regions": [{**item["regions"][0], "vertices": [[0, 0], [1281, 0], [1281, 721], [0, 721]]}]}]},
            {"crosswalks": [{**item, "regions": [item["regions"][0], item["regions"][0]]}]},
        ):
            invalid(service, {**deepcopy(config), **bad})
            assert CrosswalkService(config_path=path).get() == config
        legacy = {"schema_version": 1, "crosswalks": [{key: value for key, value in item.items() if key != "regions"}]}
        assert service.save(legacy)["crosswalks"][0]["regions"] == []
        edited = deepcopy(config)
        edited["crosswalks"][0]["regions"][0]["vertices"][0] = [280, 140]
        assert service.save(edited)["crosswalks"][0]["regions"][0]["vertices"][0] == [280, 140]
        assert CrosswalkService(config_path=path).get() == edited
        assert service.save({"schema_version": 1, "crosswalks": []})["crosswalks"] == []
    print("[PASS] crosswalk create/edit/delete, persistence and distinct camera-side validation")


if __name__ == "__main__":
    main()
