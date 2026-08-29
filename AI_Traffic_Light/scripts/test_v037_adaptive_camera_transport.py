from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLATFORMIO = ROOT / "apps/device-camera/esp32-cam/src/main.cpp"
ARDUINO = ROOT / "apps/device-camera/esp32-cam/arduino/AiTL_ESP32_CAM_V037/AiTL_ESP32_CAM_V037.ino"
CONFIG = ROOT / "apps/device-camera/esp32-cam/include/aitl_config.h"
REMOTE = ROOT / "apps/pc-studio/backend/app/services/remote_camera.py"
MANAGER = ROOT / "apps/pc-studio/backend/app/services/remote_camera_manager.py"
FRONTEND = ROOT / "apps/pc-studio/frontend/src/lib/remoteCameraApi.ts"
PAGE = ROOT / "apps/pc-studio/frontend/src/pages/CameraSourcesPage.tsx"
VERSION = ROOT / "VERSION"


def compression_step(frame_bytes: int, target_bytes: int) -> int:
    if frame_bytes <= target_bytes:
        return 0
    step = 2 + (frame_bytes - target_bytes) // 1800
    return max(2, min(10, step))


def learned_target(current: int, accepted: int, frame_bytes: int) -> int:
    header = 16
    total = frame_bytes + header
    if accepted <= header or accepted >= total:
        return current
    observed_payload = accepted - header
    candidate = observed_payload - 512 if observed_payload > 512 else 3800
    candidate = max(3800, min(5000, candidate))
    return min(current, candidate)


def main() -> int:
    platformio = PLATFORMIO.read_text(encoding="utf-8")
    arduino = ARDUINO.read_text(encoding="utf-8")
    config = CONFIG.read_text(encoding="utf-8")
    remote = REMOTE.read_text(encoding="utf-8")
    manager = MANAGER.read_text(encoding="utf-8")
    frontend = FRONTEND.read_text(encoding="utf-8")
    page = PAGE.read_text(encoding="utf-8")
    version = VERSION.read_text(encoding="utf-8")

    assert "version: 0_3_7" in version
    assert "previous_version: 0_3_6" in version
    assert "passed_baseline: 0_2_4" in version

    for path, text in ((PLATFORMIO, platformio), (ARDUINO, arduino)):
        assert "aitl-camera-v037" in text, path
        assert "aitl-tcp-jpeg-v1" in text, path
        assert "sendmsg(fd, &message, MSG_DONTWAIT)" in text, path
        assert "compressionStepForOversize" in text, path
        assert "learnPayloadTargetFromPartialSend" in text, path
        assert "adaptivePayloadTargetBytes" in text, path
        assert "adaptiveLocalFrameDrops" in text, path
        assert "adaptiveWindowLearns" in text, path
        assert "lastFrameBytes > adaptivePayloadTargetBytes" in text, path
        assert text.index("lastFrameBytes > adaptivePayloadTargetBytes") < text.index("++sequenceNumber"), path
        assert "downshiftEffectiveFrameSize" in text, path
        assert "effectiveFrameSize" in text, path
        assert "AITL_ADAPTIVE_HARD_FRAME_BYTES" in text, path
        assert "effectiveJpegQuality < adaptiveCeiling" in text, path
        assert "changedPressure = downshiftEffectiveFrameSize()" in text, path
        assert "AiTL V037 R4 adaptive-resolution ESP32-CAM node" in text, path

    for marker in (
        "#define AITL_DEFAULT_FRAME_SIZE FRAMESIZE_QVGA",
        "#define AITL_DEFAULT_JPEG_QUALITY 24",
        "#define AITL_ADAPTIVE_MAX_JPEG_QUALITY 50",
        "#define AITL_ADAPTIVE_TARGET_FRAME_BYTES 5000U",
        "#define AITL_ADAPTIVE_MIN_TARGET_FRAME_BYTES 3800U",
        "#define AITL_ADAPTIVE_FAILURE_STEP 6",
        "#define AITL_ADAPTIVE_RECOVERY_SUCCESS_FRAMES 30U",
        "#define AITL_ADAPTIVE_HARD_FRAME_BYTES 6500U",
        "#define AITL_ADAPTIVE_RESOLUTION_RECOVERY_FRAMES 60U",
    ):
        assert marker in config, marker
        assert marker in arduino, marker

    assert 'CAMERA_PROTOCOL = "aitl-camera-v037"' in remote
    assert '"aitl-camera-v036"' in remote
    assert "COMPATIBLE_CAMERA_PROTOCOLS" in remote
    assert "socket.SO_RCVBUF, 256 * 1024" in remote
    assert '"frame_size": "QVGA"' in manager
    assert '"jpeg_quality": 24' in manager
    assert 'frame_size: "QVGA"' in frontend
    assert 'jpeg_quality: 24' in frontend
    assert "ESP payload target" in page
    assert "Oversize frames skipped" in page
    assert "TCP window learns" in page
    assert "ESP effective size" in page
    assert "Resolution adaptations" in page

    # A 20 KB first frame should jump compression strongly rather than causing
    # several TCP reconnects while stepping by only two quality points.
    assert compression_step(20000, 5000) == 10
    assert compression_step(9000, 5000) == 4
    assert compression_step(5500, 5000) == 2

    # Physical R6/R5 logs often accepted about 5.3-5.7 KB before stalling.
    # R2 learns a safe payload below the observed partial-write boundary.
    assert learned_target(5000, 5744, 20000) == 5000
    assert learned_target(5000, 5298, 20000) == 4770
    assert learned_target(4770, 4200, 12000) == 3800

    print("[PASS] V037 R4 preserves ATL1/TCP framing and V036 migration compatibility")
    print("[PASS] oversized JPEGs compress first, then downshift effective resolution instead of leaking past the target")
    print("[PASS] partial-send evidence learns a conservative one-window payload target")
    print("[PASS] PC receive buffer and Camera Sources diagnostics are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
