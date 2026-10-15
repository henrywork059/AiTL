"""Focused V0401 navigation and legacy preservation checks."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "apps" / "pc-studio" / "frontend" / "src"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def main() -> None:
    nav = read("constants/appNavigation.ts")
    app = read("App.tsx")
    shell = read("layout/AppShell.tsx")
    types = read("types/app.ts")
    sections = nav.split("export const APP_SECTIONS:", 1)[1]
    for item in ("dashboard", "camera_settings", "crosswalks"):
        line = next(line for line in nav.splitlines() if line.strip().startswith(item + ":"))
        assert 'status: "stable"' in line
    for item in ("camera_sources", "zone_editor"):
        assert f'{item}: {{ id: "{item}"' in nav
        assert f'PAGE_DETAILS.{item}' not in sections
        assert f'case "{item}":' in app
    assert 'status: "legacy"' in nav and 'status: "stable"' in nav
    assert 'PAGE_DETAILS.zones' not in sections
    assert 'case "zones":' not in app and '<ZonesPage />' not in app
    assert '"zones"' not in types
    assert 'pages/ZonesPage' not in app
    assert 'PAGE_DETAILS.crosswalks' in sections
    assert 'Region Editor (Legacy)' in nav
    assert 'Legacy Zones' not in nav
    assert '<small>{navPage.status}</small>' not in shell
    assert '<div className="eyebrow">{page.status}</div>' not in shell
    assert 'test-ready</span>' not in read("pages/DashboardPage.tsx")
    print("[PASS] stable labels, hidden legacy region editor and removed empty Zones page")


if __name__ == "__main__":
    main()
