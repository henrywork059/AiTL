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
    node_card = read("components/junctions/JunctionNodeCard.tsx")
    view_helpers = read("lib/junctionNetworkView.ts")
    api = read("lib/junctionNetworkApi.ts")
    types = read("types/junctionNetwork.ts")
    css = read("pages/junctionNetworkPage.css")

    assert 'import { JunctionNetworkPage } from "./pages/JunctionNetworkPage";' in app
    assert 'case "junction_network":' in app
    assert "<JunctionNetworkPage" in app
    assert 'onSimulationChange={changeCameraSimulation}' in app
    assert 'cameraStatus?.simulation_enabled' in page
    assert 'Simulation · 1 shared camera' in page
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

    # V0313 keeps page state/mutations in the page but moves card presentation
    # and pure view helpers out of the already-large page module.
    assert 'import { JunctionNodeCard } from "../components/junctions/JunctionNodeCard";' in page
    assert "<JunctionNodeCard" in page
    assert "configById = useMemo" in page
    assert "cameraOwnerBySource = useMemo" in page
    assert "draft.intersections.find((item) => item.id === link.source_intersection_id)" not in page
    assert "function JunctionNodeCard" in node_card
    assert "junction-node-body" in node_card
    assert "JUNCTION_EDGES" in node_card and "junction-edge-tag" in node_card
    assert "JUNCTION_EDGE_LABELS" in node_card and "JUNCTION_EDGE_LABELS" in page
    assert "linkTargetEdge" in page and "Connect edges" in page
    assert "source_approach: `edge_" in page and "destination_approach: `edge_" in page
    assert "onSelectEdge(config.id, edge)" in node_card
    assert "selectedEdge={config.id === selectedId ? selectedEdge : null}" in page
    assert "crosswalk_edges" in types and "JunctionCrosswalkEdges" in types
    assert "fetchCrosswalks" in page and "crosswalkOwnerById" in page
    assert "Missing:" in page and "Refresh crossings" in page
    assert "junction-crosswalk-edge-choice" in css
    assert ".junction-edge-north" in css and ".junction-edge-east" in css
    assert ".junction-edge-south" in css and ".junction-edge-west" in css
    assert "JUNCTION_LOAD_LABELS" in node_card
    assert "fallbackJunctionNode" in view_helpers
    assert "cloneJunctionNetworkConfig" in view_helpers
    assert "nextJunctionNetworkId" in view_helpers

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

    # V0312/V0313 card content must remain visible rather than clipped by fixed
    # single-line metadata rows.
    assert "width: 260px;" in css
    assert "max-width: calc(100% - 24px);" in css
    assert ".junction-node-meta span:last-child" in css
    assert "white-space: normal;" in css
    assert "overflow-wrap: anywhere;" in css
    assert "flex-wrap: wrap;" in css
    assert "width: 220px;" in css

    print("[PASS] Junction Network is registered in navigation, App routing and function registry")
    print("[PASS] page behavior, node presentation and pure view helpers have separate owners")
    print("[PASS] Junction Network uses serial polling, typed APIs and memoized lookup maps")
    print("[PASS] multi-camera assignment and single-selected-source boundary remain visible")
    print("[PASS] node content remains responsive and non-clipping")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
