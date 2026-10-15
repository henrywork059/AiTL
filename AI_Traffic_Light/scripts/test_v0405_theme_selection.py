"""V0405 theme and selection indicator regression checks."""
from __future__ import annotations

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1] / "apps" / "pc-studio" / "frontend" / "src"


def read(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


def color(block: str, name: str) -> str:
    result = re.search(r"--" + re.escape(name) + r":\s*(#[0-9a-fA-F]{6});", block)
    assert result is not None, name
    return result.group(1).lower()


def contrast(first: str, second: str) -> float:
    def luminance(value: str) -> float:
        rgb = [int(value[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        rgb = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in rgb]
        return sum(x * weight for x, weight in zip(rgb, (0.2126, 0.7152, 0.0722)))
    low, high = sorted((luminance(first), luminance(second)))
    return (high + 0.05) / (low + 0.05)


def main() -> None:
    tokens = read("styles/tokens.css")
    light, dark = tokens.split("@media (prefers-color-scheme: dark)", 1)
    dark = dark.split("@media (prefers-contrast: more)", 1)[0]
    assert color(dark, "color-primary") == "#57ffed"
    assert color(light, "color-primary") == "#006f66"
    assert color(light, "color-crosswalk-guide") == "#006f66"
    for theme, fg, bg, minimum in (
        (light, "color-on-primary", "color-primary", 4.5),
        (light, "color-primary", "color-primary-surface", 4.5),
        (dark, "color-on-primary", "color-primary", 4.5),
        (dark, "color-primary", "color-dark-surface-1", 4.5),
    ):
        assert contrast(color(theme, fg), color(theme, bg)) >= minimum
    assert "--color-secondary: var(--color-primary);" in light
    assert "--color-secondary: var(--color-primary);" in dark

    shared = read("styles/components.css")
    assert ".nav-button.active::after" not in shared
    assert ".nav-section h2::after" in shared
    assert "background: var(--color-nav-selected);" in shared
    assert ".camera-status-entry.is-selected::before" in shared
    assert 'button[aria-pressed="true"]:not(.primary):not(.danger)' in shared
    assert '.experiment-toggle button[aria-pressed="true"]::before' in shared

    layout = read("layout/AppShell.tsx")
    assert 'aria-current={activePage === navPage.id ? "page" : undefined}' in layout

    pairs = (
        ("pages/trafficAnalytics.css", '.traffic-mode-tabs button[aria-pressed="true"]'),
        ("pages/simulationLab.css", ".experiment-tabs button.active::before"),
        ("pages/signalRules.css", ".signal-tab.active::before"),
        ("pages/crosswalksPage.css", ".crosswalk-list-item.active::after"),
        ("pages/datasetReview.css", ".capture-browser-item.active::after"),
        ("pages/liveInference.css", ".inline-toggle:has(input:checked)"),
        ("pages/junctionNetworkPage.css", '.junction-crosswalk-edge-choice[aria-pressed="true"]'),
    )
    for filename, marker in pairs:
        assert marker in read(filename), (filename, marker)

    assert 'aria-pressed={mode === "fixed"}' in read("pages/SimulationLabPage.tsx")
    assert 'aria-pressed={item.id === selectedId}' in read("pages/CrosswalksPage.tsx")
    assert 'aria-pressed={capture.capture_id === selectedCaptureId}' in read("pages/DatasetReviewPage.tsx")
    assert 'aria-selected={tab === id}' in read("pages/TrafficLogicPage.tsx")
    print("[PASS] mint dark/light theme and primary-text contrast")
    print("[PASS] selected navigation, tabs, lists, switches and camera controls")


if __name__ == "__main__":
    main()
