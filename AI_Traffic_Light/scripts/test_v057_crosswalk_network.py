"""Persistent crossing-to-crossing connections; no manually created nodes."""
from copy import deepcopy
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "pc-studio" / "backend"))

from app.core.error_codes import ErrorCode
from app.core.exceptions import AppError
from app.services.crosswalks import CrosswalkService


def crosswalk(name: str) -> dict:
    return {"id": name, "label": name, "location": "",
            "camera_side_a_id": None, "camera_side_b_id": None, "regions": []}


def main() -> None:
    a = crosswalk("crosswalk_a")
    b = crosswalk("crosswalk_b")
    old = {"schema_version": 1, "crosswalks": [a]}
    with tempfile.TemporaryDirectory(prefix="aitl_crossing_network_") as temp:
        path = Path(temp) / "crosswalks.json"
        svc = CrosswalkService(config_path=path)
        assert svc.save(old) == old
        assert CrosswalkService(config_path=path).get() == old

        graph = {"positions": {"crosswalk_a": {"x": 20, "y": 40},
                               "crosswalk_b": {"x": 80, "y": 60}},
                 "links": [{"id": "link_1", "source_crosswalk_id": "crosswalk_a",
                            "destination_crosswalk_id": "crosswalk_b",
                            "source_edge": "2", "destination_edge": "4"}]}
        config = {"schema_version": 1, "crosswalks": [a, b], "network": graph}
        assert svc.save(config) == config
        assert CrosswalkService(config_path=path).get() == config

        # Adding a crossing creates a visual node automatically without a position record.
        third = deepcopy(config)
        third["crosswalks"].append(crosswalk("crosswalk_c"))
        assert svc.save(third)["crosswalks"][-1]["id"] == "crosswalk_c"
        svc.save(config)

        bad_inputs = []
        same = deepcopy(config)
        same["network"]["links"].append({**graph["links"][0], "id": "link_2"})
        bad_inputs.append(same)
        backwards = deepcopy(config)
        backwards["network"]["links"].append({**graph["links"][0],
            "id": "link_2", "source_crosswalk_id": "crosswalk_b",
            "destination_crosswalk_id": "crosswalk_a",
            "source_edge": "4", "destination_edge": "2"})
        bad_inputs.append(backwards)
        for x in (-1, 101, float("nan")):
            sample = deepcopy(config)
            sample["network"]["positions"]["crosswalk_a"]["x"] = x
            bad_inputs.append(sample)
        for field, value in (("destination_crosswalk_id", "deleted"),
                             ("destination_crosswalk_id", "crosswalk_a"),
                             ("source_edge", "5")):
            sample = deepcopy(config)
            sample["network"]["links"][0][field] = value
            bad_inputs.append(sample)
        for sample in bad_inputs:
            try:
                svc.save(sample)
            except AppError as error:
                assert error.code == ErrorCode.CROSSWALK_INVALID and error.status_code == 422
            else:
                raise AssertionError("Invalid Network graph accepted")
            assert svc.get() == config
        assert CrosswalkService(config_path=path).get() == config

    src = ROOT / "apps" / "pc-studio" / "frontend" / "src"
    nav = (src / "constants/appNavigation.ts").read_text(encoding="utf-8")
    panel = (src / "components/CrosswalkNetworkPanel.tsx").read_text(encoding="utf-8")
    page = (src / "pages/JunctionNetworkPage.tsx").read_text(encoding="utf-8")
    assert 'label: "Network"' in nav
    traffic = nav.split('id: "traffic", label: "Traffic"', 1)[1].split("] }", 1)[0]
    assert traffic.index("PAGE_DETAILS.crosswalks") < traffic.index("PAGE_DETAILS.junction_network")
    assert "<CrosswalkNetworkPanel" in page
    assert "crosswalks.map((crosswalk" in panel
    assert "Connect crossings" in panel and "Save network" in panel
    assert "fetchCrosswalks()" in panel and "saveCrosswalks(" in panel
    assert "observation_provenance" in panel and "crosswalk_region_counts" in panel
    print("[PASS] Network graph persistence, data-integrity checks and legacy compatibility")
    print("[PASS] Crosswalks above Network; auto crossing boxes, connections and monitoring")


if __name__ == "__main__":
    main()
