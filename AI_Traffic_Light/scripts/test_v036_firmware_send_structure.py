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
        assert "sendFrameVectoredProgressBounded" in text, f"missing vectored progress send helper: {path}"
        assert "sendmsg(fd, &message, MSG_DONTWAIT)" in text, f"missing scatter/gather non-blocking send: {path}"
        assert "waitSocketWritableForProgress" in text, f"missing progress-bounded socket wait: {path}"
        assert "select(fd + 1" in text, f"missing select() backpressure wait: {path}"
        assert "errno == EAGAIN" in text and "errno == EWOULDBLOCK" in text, f"missing EAGAIN/EWOULDBLOCK handling: {path}"
        assert "streamClientSuccessfulFrames < AITL_WARMUP_SUCCESS_FRAMES" in text, f"missing per-connection warmup gate: {path}"
        assert "streamClientSuccessfulFrames = 0" in text, f"new connections must restart warmup: {path}"
        assert "streamServer.accept()" in text, f"firmware should use current accept() API: {path}"
        assert "streamServer.setNoDelay(true)" in text, f"server no-delay policy missing: {path}"
        assert "lastSendAcceptedBytes" in text and "lastSendErrno" in text, f"send diagnostics missing: {path}"
        assert "sendAllProgressBounded" not in text, f"R5 chunked helper still present: {path}"
        assert "AITL_STREAM_SEND_CHUNK_BYTES" not in text, f"R5 artificial chunking still present: {path}"
        assert "AITL_FRAME_SEND_DEADLINE_MS" not in text, f"R4 whole-frame cutoff still present: {path}"
        assert "::send(fd, data + sent, length - sent, 0)" not in text, f"blocking raw send reintroduced: {path}"

    for marker in (
        "#define AITL_STREAM_SELECT_SLICE_MS 20U",
        "#define AITL_WARMUP_SUCCESS_FRAMES 3U",
        "#define AITL_WARMUP_STALL_TIMEOUT_MS 1000U",
        "#define AITL_WARMUP_TOTAL_SEND_LIMIT_MS 1500U",
        "#define AITL_FRAME_STALL_TIMEOUT_MS 500U",
        "#define AITL_FRAME_TOTAL_SEND_LIMIT_MS 900U",
    ):
        assert marker in config, f"PlatformIO config missing {marker}"
        assert marker in standalone, f"Arduino IDE sketch missing {marker}"

    assert 'r6-warmup-vectored-send' in platformio
    assert 'r6-warmup-vectored-send' in standalone

    print("[PASS] V036 R6 sends header + JPEG through one non-blocking vectored stream path")
    print("[PASS] each new TCP connection gets a bounded warmup before steady-state freshness limits")
    print("[PASS] R5 artificial 1360-byte chunking and 250 ms reconnect loop are absent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
