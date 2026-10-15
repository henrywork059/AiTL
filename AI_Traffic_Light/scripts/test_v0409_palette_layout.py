"""V0409 palette, sidebar hierarchy, and inside-card edge-label regression."""
from __future__ import annotations

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1] / "apps" / "pc-studio" / "frontend" / "src"


def source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def role(css: str, name: str) -> str:
    match = re.search(r"--" + re.escape(name) + r":\s*(#[0-9a-fA-F]{6});", css)
    assert match, f"Missing literal role: {name}"
    return match.group(1).lower()


def luminance(color: str) -> float:
    values = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in values]
    return sum(x * weight for x, weight in zip(linear, (0.2126, 0.7152, 0.0722)))


def contrast(foreground: str, background: str) -> float:
    low, high = sorted((luminance(foreground), luminance(background)))
    return (high + 0.05) / (low + 0.05)


def main() -> None:
    tokens = source("styles/tokens.css")
    light, dark = tokens.split("@media (prefers-color-scheme: dark)", 1)
    dark = dark.split("@media (prefers-contrast: more)", 1)[0]
    colors = {
        "color-dark-surface-0": "#4d4e61",
        "color-shell": "#414354",
        "color-brand-surface": "#333648",
        "color-nav-heading-surface": "#333648",
        "color-dark-surface-1": "#55576a",
        "color-dark-surface-2": "#5a5c70",
        "color-field": "#47495b",
        "color-primary-surface": "#2f585a",
        "color-primary": "#57ffed",
        "color-on-primary": "#08312c",
    }
    for name, expected in colors.items():
        assert role(dark, name) == expected, (name, expected)
    assert role(light, "color-primary") == "#006f66"
    assert "--color-canvas: var(--color-dark-surface-0);" in dark
    assert "--color-surface: var(--color-dark-surface-1);" in dark
    assert "--color-surface-raised: var(--color-dark-surface-2);" in dark
    assert "--color-selection: rgba(87, 255, 237, 0.28);" in dark

    checks = (
        ("color-text-primary", "color-dark-surface-1", 4.5),
        ("color-text-secondary", "color-dark-surface-1", 4.5),
        ("color-text-muted", "color-dark-surface-2", 4.5),
        ("color-primary", "color-dark-surface-2", 4.5),
        ("color-primary", "color-primary-surface", 4.5),
        ("color-on-primary", "color-primary", 4.5),
        ("color-control-stroke", "color-dark-surface-2", 3.0),
        ("color-success", "color-success-surface", 4.5),
        ("color-warning", "color-warning-surface", 4.5),
        ("color-danger", "color-danger-surface", 4.5),
        ("color-info", "color-info-surface", 4.5),
        ("color-chart-vehicle", "color-dark-surface-1", 4.5),
        ("color-chart-pedestrian", "color-dark-surface-1", 4.5),
    )
    for fg, bg, minimum in checks:
        ratio = contrast(role(dark, fg), role(dark, bg))
        assert ratio >= minimum, (fg, bg, ratio)

    layout = source("styles/layout.css")
    components = source("styles/components.css")
    assert "background: var(--color-brand-surface);" in layout
    assert "border-radius: var(--radius-lg);" in layout
    assert ".brand-block h1" in components
    assert ".nav-section h2" in components
    assert "background: var(--color-nav-heading-surface);" in components
    assert "border-left: 2px solid var(--color-primary);" in components
    assert ".nav-button.active::after" in components

    junction = source("pages/junctionNetworkPage.css")
    assert "width: clamp(268px, 27vw, 336px);" in junction
    assert "grid-template-columns: 34px minmax(0, 1fr) 34px;" in junction
    for key, position in (
        ("north", "grid-column: 2; grid-row: 1;"),
        ("south", "grid-column: 2; grid-row: 3;"),
        ("east", "grid-column: 3; grid-row: 2;"),
        ("west", "grid-column: 1; grid-row: 2;"),
    ):
        marker = re.search(r"\.junction-edge-" + key + r"\s*\{([^}]+)\}", junction)
        assert marker and position in marker.group(1), (key, position)
    assert "top: -31px;" not in junction
    assert "bottom: -31px;" not in junction
    assert "left: -38px;" not in junction
    assert "right: -38px;" not in junction
    assert 'className="junction-node-edge-layout"' in source("components/junctions/JunctionNodeCard.tsx")
    assert 'JUNCTION_EDGES.map((edge) =>' in source("components/junctions/JunctionNodeCard.tsx")
    print(f"[PASS] Slate/mint palette with {len(checks)} contrast checks and preserved light mode")
    print("[PASS] Boxed sidebar header, distinct navigation sections and selected state")
    print("[PASS] Edge labels 1-4 use the four sides of a central content grid")


if __name__ == "__main__":
    main()
