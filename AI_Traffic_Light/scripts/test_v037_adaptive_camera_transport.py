from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLATFORMIO = ROOT / "apps/device-camera/esp32-cam/src/main.cpp"
ARDUINO = ROOT / "apps/device-camera/esp32-cam/arduino/AiTL_ESP32_CAM_V037/AiTL_ESP32_CAM_V037.ino"
CONFIG = ROOT / "apps/device-camera/esp32-cam/include/aitl_config.h"
REMOTE = ROOT / "apps/pc-studio/backend/app/services/remote_camera.py"
PAGE = ROOT / "apps/pc-studio/frontend/src/pages/CameraSourcesPage.tsx"
VERSION = ROOT / "VERSION"


def main() -> int:
    platformio = PLATFORMIO.read_text(encoding="utf-8")
    arduino = ARDUINO.read_text(encoding="utf-8")
    config = CONFIG.read_text(encoding="utf-8")
    remote = REMOTE.read_text(encoding="utf-8")
    page = PAGE.read_text(encoding="utf-8")
    version = VERSION.read_text(encoding="utf-8")

    assert "version: 0_3_7" in version
    assert "previous_version: 0_3_6" in version
    assert "passed_baseline: 0_2_4" in version

    for path, text in ((PLATFORMIO, platformio), (ARDUINO, arduino)):
        assert "aitl-camera-v037" in text, path
        assert "aitl-tcp-jpeg-v1" in text, path
        assert "v037-r6-quality-preserving-tcp" in text, path
        assert "sendmsg(fd, &message, MSG_DONTWAIT)" in text, path
        assert "sendFrameVectoredProgressBounded" in text, path
        assert "nextFrameDueUs = nowUs + periodUs" in text, path

        # R6 uses the physically validated one-buffer/WHEN_EMPTY camera path.
        assert "config.fb_count = 1" in text, path
        assert "config.grab_mode = CAMERA_GRAB_WHEN_EMPTY" in text, path
        assert "config.xclk_freq_hz = 20000000" in text, path
        assert "config.fb_count = 2" not in text, path
        assert "CAMERA_GRAB_LATEST" not in text, path

        # R2/R4's false single-lwIP-window assumption is intentionally gone.
        assert "compressionStepForOversize" not in text, path
        assert "learnPayloadTargetFromPartialSend" not in text, path
        assert "downshiftEffectiveFrameSize" not in text, path
        assert "AITL_ADAPTIVE_TARGET_FRAME_BYTES" not in text, path
        assert "AITL_ADAPTIVE_HARD_FRAME_BYTES" not in text, path
        assert "frameBytes > adaptivePayloadTargetBytes" not in text, path

        # Network failures must never rewrite image quality or resolution.
        assert "quality_preserving_transport" in text, path
        assert "adaptive_quality_enabled" in text, path
        assert 'adaptive_quality_enabled\\\":false' in text, path
        assert "quality/resolution preserved" in text, path
        assert "sensor->set_quality(sensor, settings.jpegQuality)" in text, path
        assert "sensor->set_framesize(sensor, settings.frameSize)" in text, path

        # BSSID/channel telemetry makes weak mesh/AP association visible.
        assert "WiFi.BSSIDstr()" in text, path
        assert "WiFi.channel()" in text, path
        assert "wifi_bssid" in text, path
        assert "wifi_channel" in text, path
        assert "wifi_disconnects" in text, path
        assert "wifi_reconnects" in text, path

    for marker in (
        "#define AITL_DEFAULT_FRAME_SIZE FRAMESIZE_QVGA",
        "#define AITL_DEFAULT_JPEG_QUALITY 24",
        "#define AITL_DEFAULT_STREAM_FPS 15U",
        "#define AITL_WARMUP_STALL_TIMEOUT_MS 1200U",
        "#define AITL_WARMUP_TOTAL_SEND_LIMIT_MS 2000U",
        "#define AITL_FRAME_STALL_TIMEOUT_MS 700U",
        "#define AITL_FRAME_TOTAL_SEND_LIMIT_MS 1500U",
    ):
        assert marker in config, marker
        assert marker in arduino, marker

    for removed in (
        "AITL_ADAPTIVE_MAX_JPEG_QUALITY",
        "AITL_ADAPTIVE_TARGET_FRAME_BYTES",
        "AITL_ADAPTIVE_MIN_TARGET_FRAME_BYTES",
        "AITL_ADAPTIVE_HARD_FRAME_BYTES",
        "AITL_ADAPTIVE_RESOLUTION_RECOVERY_FRAMES",
    ):
        assert removed not in config, removed
        assert removed not in arduino, removed

    assert 'CAMERA_PROTOCOL = "aitl-camera-v037"' in remote
    assert '"aitl-camera-v036"' in remote
    assert "COMPATIBLE_CAMERA_PROTOCOLS" in remote
    assert "socket.SO_RCVBUF, 256 * 1024" in remote
    assert "stream_reconnects" in remote
    assert "_recover_esp_session_if_needed" in remote

    assert "Image policy" in page
    assert "Wi-Fi BSSID" in page
    assert "ESP Wi-Fi recovery" in page
    assert "fixed saved quality / resolution" in page
    assert "fit one ESP lwIP send window" not in page
    assert "ESP payload target" not in page
    assert "TCP window learns" not in page

    print("[PASS] V037 R6 preserves ATL1/TCP framing and V036 migration compatibility")
    print("[PASS] R6 removes the false 3.8-5 KB single-window payload controller")
    print("[PASS] R6 preserves configured JPEG quality/resolution across TCP failures")
    print("[PASS] R6 uses one WHEN_EMPTY framebuffer and keeps 20 MHz XCLK")
    print("[PASS] R6 exposes RSSI/BSSID/channel and Wi-Fi recovery telemetry")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
