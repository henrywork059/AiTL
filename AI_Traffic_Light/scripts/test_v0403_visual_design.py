"""Shared V0403 visual-system regression: roles, contrast and page consistency."""
from __future__ import annotations

from pathlib import Path
import re
from tempfile import TemporaryDirectory

from check_structure import validate_frontend_style_system

ROOT = Path(__file__).resolve().parents[1] / "apps" / "pc-studio" / "frontend" / "src"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def color(css: str, key: str) -> str:
    match = re.search(r"--" + re.escape(key) + r":\s*(#[0-9a-fA-F]{6})\s*;", css)
    assert match, f"Missing color token {key}"
    return match.group(1)


def luminance(value: str) -> float:
    channels = [int(value[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in channels]
    return sum(v * weight for v, weight in zip(linear, (0.2126, 0.7152, 0.0722)))


def contrast(first: str, second: str) -> float:
    high, low = sorted((luminance(first), luminance(second)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def main() -> None:
    tokens = read("styles/tokens.css")
    light, dark = tokens.split("@media (prefers-color-scheme: dark)", 1)
    dark = dark.split("@media (prefers-contrast: more)", 1)[0]
    cases = [
        (light, "color-text-primary", "color-surface", 4.5),
        (light, "color-text-secondary", "color-surface", 4.5),
        (light, "color-text-muted", "color-surface", 4.5),
        (light, "color-on-primary", "color-primary", 4.5),
        (light, "color-control-stroke", "color-field", 3.0),
        (dark, "color-text-primary", "color-dark-surface-1", 4.5),
        (dark, "color-text-secondary", "color-dark-surface-1", 4.5),
        (dark, "color-text-muted", "color-dark-surface-1", 4.5),
        (dark, "color-on-primary", "color-primary", 4.5),
        (dark, "color-control-stroke", "color-dark-surface-1", 3.0),
    ]
    for section, foreground, background, minimum in cases:
        # Dark theme retains inherited color-field from its dark-surface role; check
        # the surface background instead for readable interactive boundaries.
        amount = contrast(color(section, foreground), color(section, background))
        assert amount >= minimum, f"Insufficient contrast {foreground}/{background}: {amount:.2f} < {minimum}"

    base = read("styles/base.css")
    components = read("styles/components.css")
    layout = read("styles/layout.css")
    assert "--control-height: 40px" in tokens
    assert "min-height: var(--control-height)" in base
    assert "border: var(--border-width) solid var(--color-control-stroke)" in base
    assert "outline: 3px solid var(--color-focus)" in base
    assert ".nav-button.active" in components and "inset 3px 0 0" in components
    assert "padding: var(--space-5)" in components and "var(--shadow-panel)" in components
    assert "grid-template-columns: var(--sidebar-width)" in layout
    assert "@media (max-width: 760px)" in layout

    for file in ("settingsPage.css", "datasetReview.css", "trafficAnalytics.css"):
        page = read("pages/" + file)
        assert not any(old in page for old in ("#0d1117", "#30363d", "#e6edf3", "#8b949e")), file
        assert "var(--color-" in page, file

    assert ".experiment-tabs button.active" in read("pages/simulationLab.css")
    simulation = read("pages/SimulationLabPage.tsx")
    assert 'event.key === "ArrowRight"' in simulation and 'event.key === "Home"' in simulation
    assert 'role="tab"' in simulation and 'aria-controls="experiment-tab-panel"' in simulation
    assert 'aria-pressed={mode === "flow"}' in read("pages/TrafficAnalyticsPage.tsx")
    assert 'aria-pressed={mode === "occupancy"}' in read("pages/TrafficAnalyticsPage.tsx")

    # Verify the structure gate accepts a new valid dark palette but rejects
    # malformed or disconnected base tokens.
    with TemporaryDirectory() as directory:
        project = Path(directory)
        shared = project / "apps" / "pc-studio" / "frontend" / "src"
        (shared / "styles").mkdir(parents=True)
        (shared / "styles.css").write_text(read("styles.css"), encoding="utf-8")
        token_file = shared / "styles" / "tokens.css"
        token_file.write_text(tokens, encoding="utf-8")
        errors: list[str] = []
        validate_frontend_style_system(project, errors)
        assert not errors, errors

        invalid = tokens.replace("--color-dark-surface-0: #0e1725;", "--color-dark-surface-0: invalid;")
        assert invalid != tokens
        token_file.write_text(invalid, encoding="utf-8")
        errors.clear()
        validate_frontend_style_system(project, errors)
        assert any("dark theme" in error for error in errors), errors

    print("[PASS] dark-palette structure guard accepts valid themes and rejects invalid base tokens")
    print(f"[PASS] {len(cases)} color contrast checks (WCAG 4.5:1 text, 3:1 boundaries)")
    print("[PASS] shared controls, navigation, panels, themed page chrome and tab selection")


if __name__ == "__main__":
    main()
