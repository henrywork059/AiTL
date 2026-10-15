"""The selected-region contract: soft translucent fills and emphasized borders."""
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
    def alpha(rule: str) -> float:
        match = re.search(r"fill:\s*rgba\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*,\s*(0?\.\d+|1(?:\.0)?)\s*\)", rule)
        assert match, "Expected explicit RGBA polygon fill"
        return float(match.group(1))

    assert 0 < alpha(normal) < alpha(selected) < 0.3
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
    assert 'fill="none"' not in editor
    assert "fillOpacity={0}" not in editor
    assert "onVertexDown(event, region.id, index)" in editor

    legacy = read("pages/zoneEditor.css")
    check_selected(legacy, ".zone-editor-polygon", ".zone-editor-selected", 7)

    assert "fill: none;" in declaration(read("pages/liveInference.css"), ".live-zone-polygon")
    assert "fill: none;" in declaration(read("styles/components.css"), ".zone")
    print("[PASS] Crosswalk and legacy polygon fills are translucent, selected tint stronger")
    print("[PASS] Selected outline lighter, fully opaque, thicker and dashed")
    print("[PASS] Existing vertices and live/simulation overlays preserved")


if __name__ == "__main__":
    main()
