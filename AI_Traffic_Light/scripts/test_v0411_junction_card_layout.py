"""Junction card: full title bar, centered content, four-sided controls and fluid text."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1] / "apps" / "pc-studio" / "frontend" / "src"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def block(css: str, selector: str) -> str:
    found = re.search(re.escape(selector) + r"\s*\{([^}]+)\}", css)
    assert found, selector
    return found.group(1)


def main() -> None:
    card = read("components/junctions/JunctionNodeCard.tsx")
    css = read("pages/junctionNetworkPage.css")

    title = card.index('className="junction-drag-handle"')
    heading = card.index('className="junction-node-heading"')
    id_field = card.index('className="junction-node-id"')
    layout = card.index('className="junction-node-edge-layout"')
    body = card.index('className="junction-node-body"')
    edges = card.index("JUNCTION_EDGES.map((edge) =>")
    assert title < heading < id_field < layout < body < edges
    assert "{config.label}" in card[heading:layout]
    assert "{config.id}" in card[heading:layout]
    assert "{active &&" in card[heading:layout]
    assert "onPointerDown={(event) => onBeginDrag(config.id, event)}" in card
    assert "onSelectEdge(config.id, edge)" in card
    assert "aria-pressed={selected && selectedEdge === edge}" in card

    node_style = block(css, ".junction-node")
    assert "container-type: inline-size;" in node_style
    assert "width: clamp(268px, 27vw, 336px);" in node_style
    assert "max-width: calc(100% - 24px);" in node_style
    assert "padding: 28px 32px;" not in node_style
    assert "overflow: hidden;" not in node_style

    drag = block(css, ".junction-drag-handle")
    assert "min-height: 48px;" in drag
    assert "border-bottom:" in drag
    assert "background: var(--color-surface-raised);" in drag

    grid = block(css, ".junction-node-edge-layout")
    assert "grid-template-columns: 34px minmax(0, 1fr) 34px;" in grid
    assert "grid-template-rows: 34px auto 34px;" in grid
    for side, col, row in (("north", 2, 1), ("east", 3, 2),
                           ("south", 2, 3), ("west", 1, 2)):
        position = block(css, ".junction-edge-" + side)
        assert f"grid-column: {col};" in position, side
        assert f"grid-row: {row};" in position, side
        assert not any(t in position for t in ("top:", "bottom:", "left:", "right:"))

    info = block(css, ".junction-node-body")
    assert "grid-column: 2;" in info and "grid-row: 2;" in info
    assert "justify-items: center;" in info and "text-align: center;" in info
    assert "font-size: clamp(" in info and "cqi" in info
    assert "height:" not in info and "overflow: hidden;" not in info
    assert "white-space: normal;" in block(css, ".junction-node-id")
    assert "white-space: normal;" in block(css, ".junction-load")
    assert "flex-wrap: wrap;" in block(css, ".junction-node-loads")
    assert "justify-content: center;" in block(css, ".junction-node-meta")
    assert "justify-content: center;" in block(css, ".junction-node-alerts")

    edge_style = block(css, ".junction-edge-tag")
    assert "position: absolute;" not in edge_style
    assert "min-height: 30px;" in edge_style
    print("[PASS] full-width draggable title bar contains complete junction label and ID")
    print("[PASS] center information grows vertically, wraps and scales with card width")
    print("[PASS] edge labels 1-4 occupy distinct sides of the content grid")


if __name__ == "__main__":
    main()
