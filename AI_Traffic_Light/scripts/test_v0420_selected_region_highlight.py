"""The selected-region contract: fully clear interiors and emphasized borders."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1] / "apps" / "pc-studio" / "frontend" / "src"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def declaration(css: str, selector: str) -> str:
    rules = re.findall(re.escape(selector) + r"\s*\{([^{}]+)\}", css)
    assert rules, selector
    return "\n".join(rules)


def check_selected(css: str, plain: str, active: str, width: int) -> None:
    normal = declaration(css, plain)
    selected = declaration(css, active)
    assert "fill: none;" in normal
    assert "fill: none;" in selected
    assert "rgba(" not in selected
    assert "stroke: #fff5c7;" in selected
    assert "stroke-opacity: 1;" in selected
    assert f"stroke-width: {width};" in selected
    assert "stroke-dasharray: 12 5;" in selected
    assert "stroke-linejoin: round;" in selected


def main() -> None:
    crosswalk = read("pages/crosswalkRegionEditor.css")
    check_selected(crosswalk, ".crosswalk-region-polygon",
                   ".crosswalk-region-polygon.is-selected", 6)
    assert "cursor: grab;" in declaration(crosswalk, ".crosswalk-region-vertex")
    editor = read("pages/CrosswalkRegionEditor.tsx")
    assert 'fill="none"' in editor
    assert "fillOpacity={0}" not in editor
    assert "onVertexDown(event, region.id, index)" in editor

    legacy = read("pages/zoneEditor.css")
    check_selected(legacy, ".zone-editor-polygon", ".zone-editor-selected", 7)

    assert "fill: none;" in declaration(read("pages/liveInference.css"), ".live-zone-polygon")
    assert "fill: none;" in declaration(read("styles/components.css"), ".zone")
    print("[PASS] Crosswalk and legacy polygons remain fully unfilled")
    print("[PASS] Selected outline lighter, fully opaque, thicker and dashed")
    print("[PASS] Existing vertices and live/simulation overlays preserved")


if __name__ == "__main__":
    main()
