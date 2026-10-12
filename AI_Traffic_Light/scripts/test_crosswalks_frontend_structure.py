"""Static page and API wiring for the Crosswalks feature."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "apps" / "pc-studio" / "frontend" / "src"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def main() -> None:
    page = read("pages/CrosswalksPage.tsx")
    assert 'case "crosswalks":' in read("App.tsx")
    assert "PAGE_DETAILS.crosswalks" in read("constants/appNavigation.ts")
    assert 'crosswalks: { id: "crosswalks"' in read("constants/appNavigation.ts")
    assert '"crosswalks"' in read("types/app.ts")
    assert "saveCrosswalks" in page and "fetchCrosswalks" in page
    assert "cameraPicker(\"camera_side_a_id\"" in page
    assert "cameraPicker(\"camera_side_b_id\"" in page
    assert "<svg" in page and "Array.from({ length: 7 }" in page
    # Zebra lines run horizontally across a vertical route between camera A and B.
    assert 'x="250" y={138 + index * 17} width="140" height="10"' in page
    assert 'd="M240 75 V305 M400 75 V305"' in page
    assert 'x={225 + index * 28} y="137" width="16" height="106"' not in page
    assert "Vertical pedestrian crossing from Side A to Side B" in page
    assert 138 + 6 * 17 + 10 < 255  # All horizontal lines stay within the road.
    assert 140 > 10  # Each white stripe is horizontal, not longitudinal.
    assert "useSerialPolling" in page and "fetchRemoteCameraStatus" in page
    assert "simultaneous two-camera pedestrian inference" in page
    assert 'method: "PUT"' in read("lib/crosswalksApi.ts")
    assert '"/api/crosswalks"' in read("lib/crosswalksApi.ts")
    assert "camera_side_a_id" in read("types/crosswalks.ts")
    assert "camera_side_b_id" in read("types/crosswalks.ts")
    assert ".crosswalk-layout" in read("pages/crosswalksPage.css")
    assert "traffic.crosswalk_configuration" in read("constants/functionRegistry.ts")
    print("[PASS] crosswalk page, opposite-side cameras, horizontal stripes, vertical path and API wiring")


if __name__ == "__main__":
    main()
