"""V0413 quiet sidebar navigation: neutral selection and subtle section dividers."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1] / "apps" / "pc-studio" / "frontend" / "src"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def literal_color(css: str, role: str) -> str:
    match = re.search(r"--" + re.escape(role) + r":\s*(#[0-9a-fA-F]{6});", css)
    assert match, role
    return match.group(1).lower()


def contrast(fg: str, bg: str) -> float:
    def luminance(value: str) -> float:
        rgb = [int(value[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        linear = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in rgb]
        return sum(v * w for v, w in zip(linear, (0.2126, 0.7152, 0.0722)))
    high, low = sorted((luminance(fg), luminance(bg)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def main() -> None:
    tokens = read("styles/tokens.css")
    light, dark = tokens.split("@media (prefers-color-scheme: dark)", 1)
    dark = dark.split("@media (prefers-contrast: more)", 1)[0]
    for section, expected, backgrounds in (
        (light, {"color-nav-selected": "#c9d4e2", "color-nav-hover": "#e3eaf2"}, 
         (("color-text-primary", "color-nav-selected"), 
          ("color-nav-heading-text", "color-shell"))),
        (dark, {"color-nav-selected": "#5a5c70", "color-nav-hover": "#505266",
                "color-nav-heading-text": "#bec2d1"}, 
         (("color-text-primary", "color-nav-selected"),
          ("color-nav-heading-text", "color-shell"))),
    ):
        for name, value in expected.items():
            assert literal_color(section, name) == value, (name, value)
        for fg, bg in backgrounds:
            assert contrast(literal_color(section, fg), literal_color(section, bg)) >= 4.5

    css = read("styles/components.css")
    layout = read("styles/layout.css")
    app = read("layout/AppShell.tsx")
    assert ".nav-section h2::after" in css
    assert "background: var(--color-nav-divider);" in css
    heading = css.split(".nav-section h2 {", 1)[1].split("}", 1)[0]
    assert "color: var(--color-nav-heading-text);" in heading
    assert "border-left:" not in heading and "background:" not in heading
    active = css.split(".nav-button.active,", 1)[1].split("}", 1)[0]
    assert "background: var(--color-nav-selected);" in active
    assert "color: var(--color-text-primary);" in active
    assert "box-shadow:" not in active
    assert "color-primary" not in active
    assert ".nav-button.active:hover:not(:disabled)" in css
    assert ".nav-button.active::after" not in css
    assert "background: var(--color-nav-hover);" in css
    assert "border-radius: var(--radius-sm);" in css
    assert "background: var(--color-brand-surface);" in layout
    assert ".nav-button:focus-visible" in css and "var(--color-focus)" in css
    assert 'aria-current={activePage === navPage.id ? "page" : undefined}' in app
    # Keep mint selection feedback in controls where it conveys a real action/state.
    assert ".camera-status-entry.is-selected::before" in css
    assert 'button[aria-pressed="true"]:not(.primary):not(.danger)' in css
    print("[PASS] Quiet slate sidebar roles with readable light/dark text contrast")
    print("[PASS] Muted section dividers and selected navigation without mint strips or dots")
    print("[PASS] Existing brand panel, keyboard focus and non-navigation indicators preserved")


if __name__ == "__main__":
    main()
