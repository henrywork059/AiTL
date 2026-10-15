"""AI group and direct crossing edge drag regression for PC Studio V058."""
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "apps/pc-studio/frontend/src"

def read(name: str) -> str:
    return (SRC / name).read_text(encoding="utf-8")

def main() -> None:
    nav = read("constants/appNavigation.ts")
    app = read("App.tsx")
    preview = read("pages/LiveAiPage.tsx")
    models = read("pages/ModelRegistryPage.tsx")
    panel = read("components/CrosswalkNetworkPanel.tsx")
    css = read("components/crosswalkNetworkPanel.css")
    nav_sections = nav.split("export const APP_SECTIONS:", 1)[1]

    assert 'id: "operate", label: "Operate"' in nav_sections
    assert 'id: "ai", label: "AI"' in nav_sections
    assert nav_sections.index('id: "operate"') < nav_sections.index('id: "ai"')
    assert "PAGE_DETAILS.camera_settings" in nav_sections.split('id: "ai"', 1)[0]
    assert 'pages: [PAGE_DETAILS.model_registry, PAGE_DETAILS.live_ai]' in nav_sections
    assert nav_sections.index('id: "traffic"') < nav_sections.index('id: "ai"')
    assert "PAGE_DETAILS.settings" not in nav_sections
    assert nav_sections.count("PAGE_DETAILS.live_ai") == 1
    assert nav_sections.count("PAGE_DETAILS.model_registry") == 1
    assert 'label: "Camera AI Preview"' in nav and 'label: "AI Models"' in nav
    assert 'case "live_ai":' in app and 'case "model_registry":' in app

    assert "<CameraDetectionView" in preview and "fetchCameraInference(" in preview
    assert "fetchCrosswalks(" in preview and "regionClassCounts(" in preview
    assert "<LiveView" not in preview and "<InferencePanel" not in preview
    assert "loadInferenceModel" not in preview and "autoLoadAttempted" not in preview
    assert "No current camera feed" in preview
    assert "frame?.source_id === sourceId && hasFeed" in preview
    assert "onDetectionCountChange(detections.length)" in preview
    assert "await saveRuntimeSettings({" in models and "inference_interval_ms: inferenceInterval" in models
    assert "uploadInferenceModel(" in models and "type=\"range\"" in models
    assert "loadInferenceModel" in models and "setDefaultModel" in models
    assert "unloadInferenceModel" in models and "deleteModel" in models
    assert "onSettingsChange(saved)" in models

    for marker in (
        'onPointerDown={(event) => beginConnection(crosswalk.id, edge, event)}',
        "document.elementFromPoint(clientX, clientY)",
        "finishConnection(event)",
        "cancelConnection(event)",
        'className="crossing-network-preview"',
        "edgeCenters[link.source_crosswalk_id + ",
        "connectWithKeyboard(crosswalk.id, edge)",
        "Save network",
        "These two numbered edges are already connected.",
    ):
        assert marker in panel, marker
    assert 'data-crosswalk-id={crosswalk.id}' in panel
    assert 'data-crosswalk-edge={edge}' in panel
    assert "<h4>Connect crossings</h4>" not in panel
    assert "cursor: crosshair" in css and ".crossing-network-edge.is-drop-target" in css
    print("[PASS] Traffic-first navigation, camera AI preview regions, global model settings and APIs")
    print("[PASS] Pointer/keyboard edge connections, preview, cancellation, duplicate handling and persistence")

if __name__ == "__main__":
    main()
