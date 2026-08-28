from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PLATFORMIO = PROJECT_ROOT / "apps/device-camera/esp32-cam/src/main.cpp"
STANDALONE = PROJECT_ROOT / "apps/device-camera/esp32-cam/arduino/AiTL_ESP32_CAM_V036/AiTL_ESP32_CAM_V036.ino"
CONFIG = PROJECT_ROOT / "apps/device-camera/esp32-cam/include/aitl_config.h"


def main() -> int:
    platformio = PLATFORMIO.read_text(encoding="utf-8")
    standalone = STANDALONE.read_text(encoding="utf-8")
    config = CONFIG.read_text(encoding="utf-8")

    for path, text in ((PLATFORMIO, platformio), (STANDALONE, standalone)):
        assert "waitSocketWritableForProgress" in text, f"missing progress-bounded socket wait: {path}"
        assert "sendAllProgressBounded" in text, f"missing progress-bounded send helper: {path}"
        assert "select(fd + 1" in text, f"missing select() backpressure wait: {path}"
        assert "MSG_DONTWAIT" in text, f"missing non-blocking send flag: {path}"
        assert "errno == EAGAIN" in text, f"missing EAGAIN handling: {path}"
        assert "errno == EWOULDBLOCK" in text, f"missing EWOULDBLOCK handling: {path}"
        assert "AITL_STREAM_SEND_CHUNK_BYTES" in text, f"missing bounded send chunk: {path}"
        assert "lastProgressMs = millis()" in text, f"successful writes must reset progress timer: {path}"
        assert "sendAllWithDeadline" not in text, f"R4 whole-frame deadline helper still present: {path}"
        assert "AITL_FRAME_SEND_DEADLINE_MS" not in text, f"R4 whole-frame cutoff still present: {path}"
        assert "::send(fd, data + sent, length - sent, 0)" not in text, f"blocking raw send reintroduced: {path}"

    for marker in (
        "#define AITL_STREAM_SELECT_SLICE_MS 20U",
        "#define AITL_FRAME_STALL_TIMEOUT_MS 250U",
        "#define AITL_FRAME_TOTAL_SEND_LIMIT_MS 500U",
        "#define AITL_STREAM_SEND_CHUNK_BYTES 1360U",
    ):
        assert marker in config, f"PlatformIO config missing {marker}"
        assert marker in standalone, f"Arduino IDE sketch missing {marker}"

    assert 'r5-progress-bounded-send' in platformio
    assert 'r5-progress-bounded-send' in standalone

    print("[PASS] V036 firmware uses non-blocking chunked sends with ACK/backpressure progress waits")
    print("[PASS] PlatformIO and Arduino IDE firmware use matching 250 ms stall / 500 ms hard limits")
    print("[PASS] R4 120 ms whole-frame cutoff and blocking raw send are absent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
