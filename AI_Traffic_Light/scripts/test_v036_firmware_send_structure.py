from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCES = (
    PROJECT_ROOT / "apps/device-camera/esp32-cam/src/main.cpp",
    PROJECT_ROOT / "apps/device-camera/esp32-cam/arduino/AiTL_ESP32_CAM_V036/AiTL_ESP32_CAM_V036.ino",
)
CONFIG = PROJECT_ROOT / "apps/device-camera/esp32-cam/include/aitl_config.h"


def main() -> int:
    for path in SOURCES:
        text = path.read_text(encoding="utf-8")
        assert "waitSocketWritableUntil" in text, f"missing bounded socket-writable wait: {path}"
        assert "select(fd + 1" in text, f"missing select() send readiness gate: {path}"
        assert "MSG_DONTWAIT" in text, f"missing non-blocking send flag: {path}"
        assert "errno == EAGAIN" in text, f"missing EAGAIN retry handling: {path}"
        assert "errno == EWOULDBLOCK" in text, f"missing EWOULDBLOCK retry handling: {path}"
        assert "::send(fd, data + sent, length - sent, 0)" not in text, f"blocking raw send reintroduced: {path}"

    config = CONFIG.read_text(encoding="utf-8")
    standalone = SOURCES[1].read_text(encoding="utf-8")
    assert "#define AITL_FRAME_SEND_DEADLINE_MS 120U" in config
    assert "#define AITL_FRAME_SEND_DEADLINE_MS 120U" in standalone

    print("[PASS] V036 firmware uses select() + MSG_DONTWAIT instead of blocking raw send")
    print("[PASS] PlatformIO and Arduino IDE firmware use the same 120 ms frame freshness deadline")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
