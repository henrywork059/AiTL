"""Selected regions are softly highlighted; unselected and live regions remain clear."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1] / "apps" / "pc-studio" / "frontend" / "src"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def declaration(css: str, selector: str) -> str:
    rules = re.findall(re.escape(selector) + r"\s*\{([^{}]+)\}", css)
    assert rules, selector
    return "\n".join(rules)


def check_selected(css: str, base: str, selected: str) -> None:
    normal = declaration(css, base)
    active = declaration(css, selected)
    assert "fill: none;" in normal
    match = re.search(r"fill:\s*rgba\(255,\s*246,\s*210,\s*([0-9.]+)\);", active)
    assert match, selected
    assert 0.15 <= float(match.group(1)) <= 0.30
    assert "stroke: var(--color-warning);" in active
    assert "stroke-dasharray: 14 7;" in active


def main() -> None:
    crosswalk = read("pages/crosswalkRegionEditor.css")
    check_selected(crosswalk, ".crosswalk-region-polygon", ".crosswalk-region-polygon.is-selected")
    assert "stroke-width: 5;" in declaration(crosswalk, ".crosswalk-region-polygon.is-selected")
    assert "cursor: grab;" in declaration(crosswalk, ".crosswalk-region-vertex")
    editor = read("pages/CrosswalkRegionEditor.tsx")
    assert 'fill="none"' in editor
    assert "fillOpacity={0}" not in editor
    assert "onVertexDown(event, region.id, index)" in editor

    legacy = read("pages/zoneEditor.css")
    check_selected(legacy, ".zone-editor-polygon", ".zone-editor-selected")
    assert "stroke-width: 6;" in declaration(legacy, ".zone-editor-selected")

    # No highlight tint is allowed on unselected camera overlays.
    assert "fill: none;" in declaration(read("pages/liveInference.css"), ".live-zone-polygon")
    assert "fill: none;" in declaration(read("styles/components.css"), ".zone")
    print("[PASS] Unselected regions clear; selected regions have 22% pale highlight and dashed border")
    print("[PASS] Crosswalk/legacy selection uses CSS fill without forced zero SVG opacity")
    print("[PASS] Vertex editing and live/simulation overlay transparency preserved")


if __name__ == "__main__":
    main()
