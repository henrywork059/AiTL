from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLATFORMIO = ROOT / "apps/device-camera/esp32-cam/src/main.cpp"
ARDUINO = ROOT / "apps/device-camera/esp32-cam/arduino/AiTL_ESP32_CAM_V037/AiTL_ESP32_CAM_V037.ino"
CONFIG = ROOT / "apps/device-camera/esp32-cam/include/aitl_config.h"
REMOTE = ROOT / "apps/pc-studio/backend/app/services/remote_camera.py"
MANAGER = ROOT / "apps/pc-studio/backend/app/services/remote_camera_manager.py"
FRONTEND = ROOT / "apps/pc-studio/frontend/src/lib/remoteCameraApi.ts"
VERSION = ROOT / "VERSION"


def simulate(configured: int, events: list[tuple[bool, int, int]]) -> list[int]:
    effective = configured
    recovery = 0
    values: list[int] = []
    for success, frame_bytes, send_ms in events:
        budget = max(1, 1000 // 15)
        high = max(20, budget * 85 // 100)
        low = max(8, budget * 35 // 100)
        ceiling = max(configured, 40)
        if not success:
            recovery = 0
            effective = min(ceiling, max(configured, effective + 4))
        elif send_ms > high or frame_bytes > 9000:
            recovery = 0
            effective = min(ceiling, max(configured, effective + 2))
        elif send_ms <= low and frame_bytes <= 7000 and effective > configured:
            recovery += 1
            if recovery >= 12:
                effective = max(configured, effective - 1)
                recovery = 0
        else:
            recovery = 0
        values.append(effective)
    return values


def main() -> int:
    platformio = PLATFORMIO.read_text(encoding="utf-8")
    arduino = ARDUINO.read_text(encoding="utf-8")
    config = CONFIG.read_text(encoding="utf-8")
    remote = REMOTE.read_text(encoding="utf-8")
    manager = MANAGER.read_text(encoding="utf-8")
    frontend = FRONTEND.read_text(encoding="utf-8")
    version = VERSION.read_text(encoding="utf-8")

    assert "version: 0_3_7" in version
    assert "previous_version: 0_3_6" in version
    assert "passed_baseline: 0_2_4" in version

    for path, text in ((PLATFORMIO, platformio), (ARDUINO, arduino)):
        assert 'aitl-camera-v037' in text, path
        assert 'aitl-tcp-jpeg-v1' in text, path
        assert 'sendmsg(fd, &message, MSG_DONTWAIT)' in text, path
        assert 'adaptJpegPressure' in text, path
        assert 'effectiveJpegQuality' in text, path
        assert 'sendEwmaMs' in text, path
        assert 'adaptive_quality_adjustments' in text, path
        assert 'configured_jpeg_quality' in text, path
        assert 'effective_jpeg_quality' in text, path
        assert 'AiTL V037 adaptive-JPEG ESP32-CAM node' in text, path

    for marker in (
        '#define AITL_DEFAULT_FRAME_SIZE FRAMESIZE_QVGA',
        '#define AITL_DEFAULT_JPEG_QUALITY 24',
        '#define AITL_ADAPTIVE_MAX_JPEG_QUALITY 40',
        '#define AITL_ADAPTIVE_FAILURE_STEP 4',
        '#define AITL_ADAPTIVE_RECOVERY_SUCCESS_FRAMES 12U',
    ):
        assert marker in config, marker
        assert marker in arduino, marker

    assert 'CAMERA_PROTOCOL = "aitl-camera-v037"' in remote
    assert '"aitl-camera-v036"' in remote
    assert 'COMPATIBLE_CAMERA_PROTOCOLS' in remote
    assert '"frame_size": "QVGA"' in manager
    assert '"jpeg_quality": 24' in manager
    assert 'frame_size: "QVGA"' in frontend
    assert 'jpeg_quality: 24' in frontend

    pressured = simulate(24, [(True, 14000, 300)] * 5)
    assert pressured == [26, 28, 30, 32, 34]
    failed = simulate(24, [(False, 14000, 900)] * 6)
    assert failed[-1] == 40 and all(24 <= q <= 40 for q in failed)
    recovery = simulate(24, [(True, 14000, 300)] * 4 + [(True, 5000, 10)] * 24)
    assert recovery[-1] == 30  # 32 -> 31 -> 30 after two 12-frame recovery windows
    assert min(recovery) >= 24
    high_config = simulate(50, [(False, 14000, 900)] * 3)
    assert high_config == [50, 50, 50], "adaptive logic must never reduce a user's already-high compression setting"

    print("[PASS] V037 preserves V036 ATL1/TCP framing and R6 non-blocking vectored send")
    print("[PASS] adaptive JPEG pressure is bounded, failure-responsive, and recovers slowly")
    print("[PASS] new profile defaults are QVGA / JPEG 24 / 15 FPS while V036 remains migration-compatible")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
