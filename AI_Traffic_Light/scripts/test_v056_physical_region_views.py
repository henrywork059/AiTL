"""One physical region has two camera-specific polygons and counts."""
from copy import deepcopy
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "pc-studio" / "backend"))

from app.core.error_codes import ErrorCode
from app.core.exceptions import AppError
from app.services.crosswalks import CrosswalkService
from app.services.traffic_logic import count_crosswalk_regions

TOP = [[100, 60], [300, 60], [300, 220], [100, 220]]
BOTTOM = [[100, 460], [300, 460], [300, 660], [100, 660]]


def detected(source: str) -> dict:
    return {
        "source_id": source, "image_width": 1280, "image_height": 720,
        "detections": [
            {"class_name": "person", "box_xyxy": [150, 80, 190, 120]},
            {"class_name": "car", "box_xyxy": [150, 510, 190, 550]},
        ],
    }


def main() -> None:
    region = {"id": "region_1", "label": "Region 1", "vertices": TOP,
              "vertices_by_side": {"a": TOP, "b": BOTTOM}}
    crosswalk = {"id": "crosswalk_1", "label": "Gate", "location": "",
                 "camera_side_a_id": "cam_a", "camera_side_b_id": "cam_b",
                 "regions": [region]}
    payload = {"schema_version": 1, "crosswalks": [crosswalk]}
    with tempfile.TemporaryDirectory(prefix="aitl_physical_regions_") as folder:
        service = CrosswalkService(config_path=Path(folder) / "crosswalks.json")
        assert service.save(payload) == payload
        assert CrosswalkService(config_path=service._path).get() == payload
        cam_a = count_crosswalk_regions(detected("cam_a"), [crosswalk])
        cam_b = count_crosswalk_regions(detected("cam_b"), [crosswalk])
        assert list(cam_a) == ["crosswalk_1:a:region_1"]
        assert list(cam_b) == ["crosswalk_1:b:region_1"]
        a = cam_a["crosswalk_1:a:region_1"]
        b = cam_b["crosswalk_1:b:region_1"]
        assert a["class_counts"] == {"person": 1} and a["total"] == 1
        assert b["class_counts"] == {"car": 1} and b["total"] == 1
        assert a["physical_region_id"] == b["physical_region_id"] == "crosswalk_1:region_1"
        assert a["camera_region_id"] != b["camera_region_id"]
        assert count_crosswalk_regions(detected("unknown"), [crosswalk]) == {}
        assert count_crosswalk_regions(None, [crosswalk]) == {}

        # Side B geometry errors are rejected without replacing the saved config.
        bad = deepcopy(payload)
        bad["crosswalks"][0]["regions"][0]["vertices_by_side"]["b"] = [[0, 0], [1, 1], [0, 1], [1, 0]]
        try:
            service.save(bad)
        except AppError as error:
            assert error.code == ErrorCode.CROSSWALK_INVALID and error.status_code == 422
        else:
            raise AssertionError("Invalid Side B polygon accepted")
        assert service.get() == payload

        # Older shared polygons continue to count from either camera.
        shared = [{**region, "vertices_by_side": {}}]
        shared[0].pop("vertices_by_side")
        assert count_crosswalk_regions(detected("cam_b"), [{**crosswalk, "regions": shared}])[
            "crosswalk_1:b:region_1"
        ]["class_counts"] == {"person": 1}

        # Previously saved one-sided V054 regions must stay limited to that side.
        legacy = [{**region, "camera_side": "a"}]
        assert count_crosswalk_regions(detected("cam_b"), [{**crosswalk, "regions": legacy}]) == {}

    editor = (ROOT / "apps/pc-studio/frontend/src/pages/CrosswalkRegionEditor.tsx").read_text(encoding="utf-8")
    assert "Backend region ID" not in editor
    assert "vertices_by_side:" in editor and "verticesForSide(region, sideKey)" in editor
    assert 'onClick={() => setSide("camera_side_a_id")}' in editor
    assert 'onClick={() => setSide("camera_side_b_id")}' in editor
    print("[PASS] One physical region has independent top/bottom camera polygons and class counts")
    print("[PASS] Separate camera IDs, shared physical ID, validation and legacy compatibility")
    print("[PASS] Region Editor hides backend IDs and retains selection while switching views")


if __name__ == "__main__":
    main()
