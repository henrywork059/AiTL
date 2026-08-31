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

    print("[PASS] Junction Network is registered in navigation, App routing and function registry")
    print("[PASS] Junction Network uses serial polling and typed network APIs")
    print("[PASS] multi-camera assignment and single-selected-source boundary are visible in the page structure")
    print("[PASS] node/link/load/warning visualization styles are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
