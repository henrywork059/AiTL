"""Region interiors remain clear; selection uses a brighter outline only."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1] / "apps" / "pc-studio" / "frontend" / "src"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def rule(css: str, selector: str) -> str:
    matches = list(re.finditer(re.escape(selector) + r"\s*\{([^{}]*)\}", css))
    assert matches, f"Missing CSS selector: {selector}"
    return matches[-1].group(1)


def main() -> None:
    editor = read("pages/crosswalkRegionEditor.css")
    normal = rule(editor, ".crosswalk-region-polygon")
    selected = rule(editor, ".crosswalk-region-polygon.is-selected")
    assert "fill: none;" in normal
    assert "stroke: var(--color-primary);" in normal
    assert "fill: none;" in selected
    assert "stroke: #fff5c7;" in selected
    assert "stroke-opacity: 1;" in selected
    assert "stroke-width: 6;" in selected
    assert "stroke-dasharray: 12 5;" in selected
    assert "cursor: grab;" in rule(editor, ".crosswalk-region-vertex")
    assert "stroke: var(--color-primary);" in rule(editor, ".crosswalk-region-vertex")
    crosswalk = read("pages/CrosswalkRegionEditor.tsx")
    assert "onVertexDown(event, region.id, index)" in crosswalk
    assert 'className="crosswalk-region-vertex"' in crosswalk

    live = read("pages/liveInference.css")
    assert "fill: none;" in rule(live, ".live-zone-polygon")
    assert "stroke-width: 3;" in rule(live, ".live-zone-polygon")
    for selector in (".live-zone-pedestrian_waiting", ".live-zone-crossing",
                     ".live-zone-vehicle_queue", ".live-zone-ignore"):
        assert "stroke:" in rule(live, selector)

    simulation = read("styles/components.css")
    assert "fill: none;" in rule(simulation, ".zone")
    assert "stroke-width: 4;" in rule(simulation, ".zone")

    legacy = read("pages/zoneEditor.css")
    assert "fill: none;" in rule(legacy, ".zone-editor-polygon")
    assert "fill: none;" in rule(legacy, ".zone-editor-selected")
    assert "stroke: #fff5c7;" in rule(legacy, ".zone-editor-selected")
    assert "stroke-width: 7;" in rule(legacy, ".zone-editor-selected")
    assert "stroke-dasharray: 12 5;" in rule(legacy, ".zone-editor-selected")
    assert "fill: none;" in rule(legacy, ".zone-draft-line")

    # Dataset object bounding boxes are not region polygons.
    dataset = read("pages/datasetReview.css")
    assert "fill: var(--color-zone-fill);" in rule(dataset, ".manual-label-box")
    print("[PASS] Crosswalk polygons clear; selected outline brighter with handles preserved")
    print("[PASS] Live/simulation and legacy region interiors remain clear")
    print("[PASS] Dataset bounding boxes remain unchanged")


if __name__ == "__main__":
    main()
