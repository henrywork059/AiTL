"""Hallmark shell regression: explicit simulation toggle with preserved navigation."""
from pathlib import Path
import re

SRC = Path(__file__).resolve().parents[1] / "apps" / "pc-studio" / "frontend" / "src"


def read(path: str) -> str:
    return (SRC / path).read_text(encoding="utf-8")


def main() -> None:
    shell = read("layout/AppShell.tsx")
    layout = read("styles/layout.css")
    base = read("styles/base.css")
    components = read("styles/components.css")
    app = read("App.tsx")
    status = read("components/AppStatusBar.tsx")

    brand = shell.split('<div className="brand-block">', 1)[1].split("</div>", 1)[0]
    assert "<h1>AI Traffic Light</h1>" in brand
    assert brand.count("<button") == 1
    assert 'type="button"' in brand
    assert 'className="simulation-tools-toggle"' in brand
    assert 'aria-pressed={showSimulationTools}' in brand
    assert 'onClick={onSimulationToolsToggle}' in brand
    assert "onKeyDown=" not in brand and 'role="button"' not in brand
    assert "APP_VERSION_LABEL" not in shell
    assert "APP_VERSION_LABEL" in status
    assert '<div className="eyebrow">Legacy</div>' not in shell
    assert "<p>{page.description}</p>" in shell
    assert 'aria-current={activePage === navPage.id ? "page" : undefined}' in shell

    assert "onSimulationToolsToggle={toggleSimulationTools}" in app
    assert 'if (activePage === "simulation_lab") setActivePage("dashboard");' in app
    assert "setShowSimulationTools((current) => !current);" in app
    button = re.search(r"\.simulation-tools-toggle\s*\{([^{}]+)\}", layout)
    assert button and "width: 100%;" in button.group(1)
    assert "margin-top: var(--space-3);" in button.group(1)
    brand_style = re.search(r"\.brand-block\s*\{([^{}]+)\}", layout)
    assert brand_style and "cursor: pointer;" not in brand_style.group(1)
    assert ".brand-block:hover" not in layout
    assert "button:focus-visible" in base
    assert 'button[aria-pressed="true"]:not(.primary):not(.danger)' in components
    assert "@media (max-width: 760px)" in layout

    print("[PASS] Simulation tools has a native labeled control with existing state and keyboard support")
    print("[PASS] Branding is informational; navigation, status and compact layout remain wired")


if __name__ == "__main__":
    main()
