from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PLATFORMIO = PROJECT_ROOT / "apps/device-camera/esp32-cam/src/main.cpp"
V036_STANDALONE = PROJECT_ROOT / "apps/device-camera/esp32-cam/arduino/AiTL_ESP32_CAM_V036/AiTL_ESP32_CAM_V036.ino"
V037_STANDALONE = PROJECT_ROOT / "apps/device-camera/esp32-cam/arduino/AiTL_ESP32_CAM_V037/AiTL_ESP32_CAM_V037.ino"
CONFIG = PROJECT_ROOT / "apps/device-camera/esp32-cam/include/aitl_config.h"


def assert_vectored_transport(path: Path, text: str) -> None:
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
    assert "sendAllProgressBounded" not in text, f"old chunked helper still present: {path}"
    assert "AITL_STREAM_SEND_CHUNK_BYTES" not in text, f"artificial chunking reintroduced: {path}"
    assert "::send(fd, data + sent, length - sent, 0)" not in text, f"blocking raw send reintroduced: {path}"


def main() -> int:
    platformio = PLATFORMIO.read_text(encoding="utf-8")
    v036 = V036_STANDALONE.read_text(encoding="utf-8")
    v037 = V037_STANDALONE.read_text(encoding="utf-8")
    config = CONFIG.read_text(encoding="utf-8")

    assert_vectored_transport(PLATFORMIO, platformio)
    assert_vectored_transport(V037_STANDALONE, v037)

    for marker in (
        "#define AITL_STREAM_SELECT_SLICE_MS 20U",
        "#define AITL_WARMUP_SUCCESS_FRAMES 3U",
        "#define AITL_WARMUP_STALL_TIMEOUT_MS 1200U",
        "#define AITL_WARMUP_TOTAL_SEND_LIMIT_MS 2000U",
        "#define AITL_FRAME_STALL_TIMEOUT_MS 700U",
        "#define AITL_FRAME_TOTAL_SEND_LIMIT_MS 1500U",
    ):
        assert marker in config, f"current PlatformIO config missing R6 bound {marker}"
        assert marker in v037, f"V037 Arduino sketch missing R6 bound {marker}"

    # Keep archived V036 identifiable as the previous physical-test firmware.
    assert V036_STANDALONE.is_file()
    assert "r6-warmup-vectored-send" in v036
    assert "aitl-camera-v036" in v036

    assert "aitl-camera-v037" in platformio and "quality_preserving_transport" in platformio
    assert "aitl-camera-v037" in v037 and "quality_preserving_transport" in v037
    assert "adaptJpegPressure" not in platformio
    assert "adaptJpegPressure" not in v037

    print("[PASS] V037 R6 keeps the proven V036 non-blocking vectored TCP foundation")
    print("[PASS] V037 R6 extends send guardrails without reintroducing blocking writes")
    print("[PASS] archived V036 standalone sketch remains identifiable for comparison")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
