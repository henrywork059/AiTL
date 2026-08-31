from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PLATFORMIO = PROJECT_ROOT / "apps/device-camera/esp32-cam/platformio.ini"
WRAPPER = PROJECT_ROOT / "apps/device-camera/esp32-cam/src/main_v0310.cpp"
LEGACY = PROJECT_ROOT / "apps/device-camera/esp32-cam/src/main.cpp"
ARDUINO = (
    PROJECT_ROOT
    / "apps/device-camera/esp32-cam/arduino/AiTL_ESP32_CAM_V0310/AiTL_ESP32_CAM_V0310.ino"
)
ARDUINO_LEGACY = (
    PROJECT_ROOT
    / "apps/device-camera/esp32-cam/arduino/AiTL_ESP32_CAM_V037/AiTL_ESP32_CAM_V037.ino"
)
PC_RECEIVER = PROJECT_ROOT / "apps/pc-studio/backend/app/services/remote_camera.py"
R10_DIAG = (
    PROJECT_ROOT
    / "apps/device-camera/esp32-cam/arduino/AiTL_ESP32_CAM_ARCH_DIAG/AiTL_ESP32_CAM_ARCH_DIAG.ino"
)


def assert_tuned_wrapper(text: str) -> None:
    assert "kV0310SendChunkBytes = 11680U" in text
    assert "CAMERA_GRAB_LATEST" in text
    assert "kV0310FallbackGrabMode = CAMERA_GRAB_WHEN_EMPTY" in text
    assert "#define CAMERA_GRAB_WHEN_EMPTY aitlV0310GrabMode()" in text
    assert "#define sendmsg aitlV0310Sendmsg" in text
    assert "::send(fd, cursor, requested, flags)" in text
    assert "send_chunk=%u" in text


def main() -> int:
    for path in (PLATFORMIO, WRAPPER, LEGACY, ARDUINO, ARDUINO_LEGACY, PC_RECEIVER, R10_DIAG):
        assert path.exists(), path

    platformio = PLATFORMIO.read_text(encoding="utf-8")
    wrapper = WRAPPER.read_text(encoding="utf-8")
    legacy = LEGACY.read_text(encoding="utf-8")
    arduino = ARDUINO.read_text(encoding="utf-8")
    arduino_legacy = ARDUINO_LEGACY.read_text(encoding="utf-8")
    receiver = PC_RECEIVER.read_text(encoding="utf-8")
    r10_diag = R10_DIAG.read_text(encoding="utf-8")

    assert_tuned_wrapper(wrapper)
    assert_tuned_wrapper(arduino)

    # PlatformIO must compile only the V0310 wrapper. The wrapper textually
    # includes the mature implementation, so compiling main.cpp separately
    # would create duplicate setup/loop symbols.
    assert "build_src_filter" in platformio
    assert "+<main_v0310.cpp>" in platformio
    assert "+<main.cpp>" not in platformio
    assert '#include "main.cpp"' in wrapper

    # Arduino IDE users flash the V0310 sketch while it reuses the checked V037
    # implementation from the adjacent repository folder.
    assert "AiTL_ESP32_CAM_V0310" in str(ARDUINO)
    assert '#include "../AiTL_ESP32_CAM_V037/AiTL_ESP32_CAM_V037.ino"' in arduino

    # The actual wire/session contract is deliberately unchanged in V0310.
    for source in (legacy, arduino_legacy):
        assert '"aitl-camera-v037"' in source
        assert '"aitl-tcp-jpeg-v1"' in source
        assert "{'A', 'T', 'L', '1'}" in source
        assert "config.fb_count = 1" in source

    assert 'FRAME_MAGIC = b"ATL1"' in receiver
    assert 'FRAME_PROTOCOL = "aitl-tcp-jpeg-v1"' in receiver
    assert 'CAMERA_PROTOCOL = "aitl-camera-v037"' in receiver

    # V0310 must preserve PC-selected image quality/resolution rather than
    # silently forcing the diagnostic q18 result or reviving adaptive quality
    # degradation behind the saved profile.
    assert "jpegQuality = AITL_DEFAULT_JPEG_QUALITY" in legacy
    assert "settings.jpegQuality" in legacy
    assert "adaptive_quality_enabled\\\":false" in legacy
    assert "set_quality(sensor, settings.jpegQuality)" in legacy
    assert "set_framesize(sensor, settings.frameSize)" in legacy
    assert "JPEG_QUALITY 18" not in wrapper
    assert "JPEG_QUALITY 18" not in arduino

    # Keep the R10 diagnostic firmware available as an independent benchmark.
    assert "R10 camera tuning benchmark firmware" in r10_diag
    assert "AiTL_ESP32_CAM_ARCH_DIAG" in str(R10_DIAG)

    print("[PASS] V0310 keeps ATL1/PC session compatibility")
    print("[PASS] V0310 selects one-buffer CAMERA_GRAB_LATEST on PSRAM")
    print("[PASS] V0310 replaces real sendmsg with bounded plain send batches up to 11680 B")
    print("[PASS] saved resolution/JPEG quality remain PC-controlled")
    print("[PASS] PlatformIO and Arduino IDE production entrypoints are both present")
    print("[PASS] R10 diagnostic firmware remains separate for physical A/B verification")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
