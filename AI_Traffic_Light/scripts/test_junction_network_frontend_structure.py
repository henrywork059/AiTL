from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FRONTEND = PROJECT_ROOT / "apps" / "pc-studio" / "frontend" / "src"


def read(relative: str) -> str:
    return (FRONTEND / relative).read_text(encoding="utf-8")


def main() -> int:
    app = read("App.tsx")
    app_types = read("types/app.ts")
    navigation = read("constants/appNavigation.ts")
    functions = read("constants/functionRegistry.ts")
    page = read("pages/JunctionNetworkPage.tsx")
    api = read("lib/junctionNetworkApi.ts")
    types = read("types/junctionNetwork.ts")
    css = read("pages/junctionNetworkPage.css")

    assert 'import { JunctionNetworkPage } from "./pages/JunctionNetworkPage";' in app
    assert 'case "junction_network":' in app
    assert "<JunctionNetworkPage />" in app
    assert '| "junction_network"' in app_types
    assert "junction_network:" in navigation
    assert "PAGE_DETAILS.junction_network" in navigation

    for function_id in (
        "traffic.junction_network",
        "traffic.junction_camera_assignment",
        "traffic.junction_observability",
    ):
        assert f'id: "{function_id}"' in functions, f"function registry missing {function_id}"

    assert "useSerialPolling" in page
    assert "window.setInterval" not in page
    assert "fetchJunctionNetworkOverview" in page
    assert "saveJunctionNetwork" in page
    assert "resetJunctionNetwork" in page
    assert "source_ids" in page and "primary_source_id" in page
    assert "single selected AI source" in page
    assert "junction-map-canvas" in page
    assert "junction-link-layer" in page
    assert "junction-node" in page

    assert "/api/traffic/network/overview" in api
    assert "/api/traffic/network" in api
    assert 'method: "PUT"' in api
    assert 'method: "POST"' in api

    assert 'JunctionLoadLevel = "unavailable" | "clear" | "light" | "moderate" | "heavy"' in types
    assert "primary_source_id: string | null" in types
    assert "position: JunctionPosition" in types
    assert "simultaneous_multi_junction_inference: boolean" in types

    for marker in (
        ".junction-map-canvas",
        ".junction-link-layer",
        ".junction-node",
        ".junction-load-heavy",
        ".junction-warning-critical",
    ):
        assert marker in css, f"missing Junction Network style marker: {marker}"

    assert "width: 260px;" in css, "desktop junction cards must preserve enough width for live status content"
    assert "max-width: calc(100% - 24px);" in css, "junction cards must remain bounded by the map width"
    assert ".junction-node-meta span:last-child" in css
    assert "white-space: normal;" in css, "junction status content must be allowed to wrap instead of clipping"
    assert "overflow-wrap: anywhere;" in css, "long junction status labels must remain visible inside the card"
    assert "flex-wrap: wrap;" in css, "junction metadata/alerts must be able to wrap inside the card"

    print("[PASS] Junction Network is registered in navigation, App routing and function registry")
    print("[PASS] Junction Network uses serial polling and typed network APIs")
    print("[PASS] multi-camera assignment and single-selected-source boundary are visible in the page structure")
    print("[PASS] node/link/load/warning visualization styles are present")
    print("[PASS] junction cards keep title, phase, load and warning content visible without fixed-row clipping")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
