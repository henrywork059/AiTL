"""V0416: remove empty Zones navigation and standardize UI wording to Regions."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "apps" / "pc-studio" / "frontend" / "src"


def source(path: str) -> str:
    return (FRONTEND / path).read_text(encoding="utf-8")


def main() -> None:
    nav = source("constants/appNavigation.ts")
    app = source("App.tsx")
    page_ids = source("types/app.ts")
    assert 'PAGE_DETAILS.zones' not in nav
    assert '  zones: { id: "zones"' not in nav
    assert 'case "zones":' not in app
    assert 'ZonesPage' not in app
    assert '"zones"' not in page_ids
    assert not (FRONTEND / "pages" / "ZonesPage.tsx").exists()
    assert 'PAGE_DETAILS.crosswalks' in nav
    assert 'PAGE_DETAILS.junction_network' in nav

    # Preserve hidden editor/route and serialized zone API identifiers.
    assert 'zone_editor: { id: "zone_editor", label: "Region Editor (Legacy)"' in nav
    assert 'case "zone_editor":' in app
    assert 'ZoneEditorPage' in app
    api = source("api.ts")
    assert '/api/zones/active' in api
    assert "saveActiveZones" in api

    assert '> Regions</label>' in source("pages/LiveAiPage.tsx")
    assert "<h2>Regions</h2>" in source("components/ZonePanel.tsx")
    assert 'configured region overlay' in source("components/CameraDetectionView.tsx")

    logic = source("pages/TrafficLogicPage.tsx")
    for label in ("Live region / class observation", "Region / class count",
                  "<label>Region<select", "region/class scenario conditions"):
        assert label in logic, label
    assert "Live zone / class observation" not in logic
    assert ">Zone / class count</option>" not in logic

    analytics = source("pages/TrafficAnalyticsPage.tsx")
    assert ">Region Editor</span>" in analytics
    assert "pedestrian waiting regions" in analytics
    assert "labels, zones" not in analytics

    registry = source("constants/functionRegistry.ts")
    assert 'area: "Regions"' in registry
    assert 'area: "Zones"' not in registry
    assert '"Edit camera-aligned traffic regions"' in registry
    assert '"Overlay regions on Live AI"' in registry
    assert '"Count live detections in regions"' in registry

    editor = source("pages/ZoneEditorPage.tsx")
    for label in ("Regions & counting geometry", "Region ID", "Save regions",
                  " regions to ", '<FunctionChecklist area="Regions" />'):
        assert label in editor, label
    assert "Zone ID must use" not in editor
    assert "Save zones" not in editor

    mock = source("mockData.ts")
    assert "Pedestrian Waiting Region" in mock
    assert "Crossing Region" in mock
    print("[PASS] Empty Traffic Zones page and route removed; Crosswalks preserved")
    print("[PASS] Region wording across Live AI, Signal Control, Analytics and legacy editor")
    print("[PASS] Existing zone API/schema and legacy editor compatibility preserved")


if __name__ == "__main__":
    main()
