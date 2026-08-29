from pathlib import Path
import re

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PLATFORMIO = PROJECT_ROOT / "apps/device-camera/esp32-cam/src/main.cpp"
V036_STANDALONE = PROJECT_ROOT / "apps/device-camera/esp32-cam/arduino/AiTL_ESP32_CAM_V036/AiTL_ESP32_CAM_V036.ino"
V037_STANDALONE = PROJECT_ROOT / "apps/device-camera/esp32-cam/arduino/AiTL_ESP32_CAM_V037/AiTL_ESP32_CAM_V037.ino"
CONFIG = PROJECT_ROOT / "apps/device-camera/esp32-cam/include/aitl_config.h"


def compact_cpp(text: str) -> str:
    """Ignore formatting-only whitespace while preserving tokens/operators."""
    return re.sub(r"\s+", "", text)


def assert_vectored_transport(path: Path, text: str) -> None:
    compact = compact_cpp(text)

    assert "sendFrameVectoredProgressBounded" in text, f"missing vectored progress send helper: {path}"
    assert "sendmsg(fd,&message,MSG_DONTWAIT)" in compact, f"missing scatter/gather non-blocking send: {path}"
    assert "waitSocketWritableForProgress" in text, f"missing progress-bounded socket wait: {path}"
    assert "select(fd+1" in compact, f"missing select() backpressure wait: {path}"
    assert "errno==EAGAIN" in compact and "errno==EWOULDBLOCK" in compact, f"missing EAGAIN/EWOULDBLOCK handling: {path}"

    # Preserve the per-connection warm-up behavior semantically. Do not depend
    # on whether a later formatter writes spaces around the '<' operator.
    assert (
        "streamClientSuccessfulFrames<AITL_WARMUP_SUCCESS_FRAMES" in compact
    ), f"missing per-connection warmup gate: {path}"
    assert "streamClientSuccessfulFrames=0" in compact, f"new connections must restart warmup: {path}"

    assert "streamServer.accept()" in compact, f"firmware should use current accept() API: {path}"
    assert "streamServer.setNoDelay(true)" in compact, f"server no-delay policy missing: {path}"
    assert "lastSendAcceptedBytes" in text and "lastSendErrno" in text, f"send diagnostics missing: {path}"

    # The historical production path must not regress to the old blocking or
    # fixed-chunk implementation. V038 R4 may additionally contain a staged
    # diagnostic-only sender, but it must itself remain MSG_DONTWAIT-bounded.
    assert "sendAllProgressBounded" not in text, f"old chunked helper still present: {path}"
    assert "AITL_STREAM_SEND_CHUNK_BYTES" not in text, f"old artificial production chunking reintroduced: {path}"
    assert "::send(fd,data+sent,length-sent,0)" not in compact, f"blocking raw send reintroduced: {path}"

    if "v037-r7-diagnostic-isolation" in text:
        assert "DiagnosticStreamMode::Normal" in text, f"R7 normal diagnostic mode missing: {path}"
        assert "diagnosticStreamMode=DiagnosticStreamMode::Normal" in compact, f"R7 must default/restore to normal mode: {path}"
        assert "sendStagedFrame" in text, f"R7 staged diagnostic isolation helper missing: {path}"
        assert "MSG_DONTWAIT" in text, f"R7 diagnostic sender must remain non-blocking: {path}"
        assert (
            "elseif(fd>=0)payloadOk=sendFrameVectoredProgressBounded" in compact
        ), f"R7 normal camera path must still use the inherited vectored sender: {path}"


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

    print("[PASS] inherited V036/V037 non-blocking vectored TCP foundation is preserved independent of formatting")
    print("[PASS] per-connection warmup and R6 send guardrails remain active")
    print("[PASS] R7 diagnostic-only staged sending does not replace the normal vectored production path")
    print("[PASS] archived V036 standalone sketch remains identifiable for comparison")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
