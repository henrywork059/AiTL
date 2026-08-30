from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import http.client
import json
import socket
import statistics
import struct
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

ATL1_HEADER = struct.Struct("!4sIII")
ATL1_MAGIC = b"ATL1"
CONTROL_TIMEOUT = 8.0
STREAM_TIMEOUT = 8.0


@dataclass
class TestResult:
    name: str
    status: str
    frames: int = 0
    bytes_received: int = 0
    elapsed_ms: float | None = None
    measured_fps: float | None = None
    detail: str = ""
    telemetry: dict[str, Any] | None = None


def http_json(host: str, path: str, method: str = "GET", query: dict[str, Any] | None = None) -> dict[str, Any]:
    target = path + (("?" + urlencode({k: str(v) for k, v in query.items()})) if query else "")
    connection = http.client.HTTPConnection(host, 80, timeout=CONTROL_TIMEOUT)
    try:
        connection.request(method, target, body=b"" if method != "GET" else None, headers={"Connection": "close"})
        response = connection.getresponse()
        payload = response.read(128 * 1024)
        if response.status < 200 or response.status >= 300:
            raise RuntimeError(f"HTTP {response.status}: {payload[:300]!r}")
        parsed = json.loads(payload.decode("utf-8"))
        if not isinstance(parsed, dict):
            raise RuntimeError("JSON response was not an object")
        return parsed
    finally:
        connection.close()


def read_exact(sock: socket.socket, size: int) -> bytes:
    data = bytearray(size)
    view = memoryview(data)
    offset = 0
    while offset < size:
        count = sock.recv_into(view[offset:])
        if count == 0:
            raise EOFError(f"socket closed at {offset}/{size} bytes")
        offset += count
    return bytes(data)


def jpeg_ok(payload: bytes) -> bool:
    return len(payload) >= 4 and payload.startswith(b"\xff\xd8") and payload.endswith(b"\xff\xd9")


def test_capture(host: str) -> tuple[TestResult, int]:
    started = time.perf_counter()
    connection = http.client.HTTPConnection(host, 80, timeout=CONTROL_TIMEOUT)
    try:
        connection.request("GET", "/capture", headers={"Connection": "close"})
        response = connection.getresponse()
        payload = response.read()
        elapsed = (time.perf_counter() - started) * 1000.0
        ok = response.status == 200 and jpeg_ok(payload)
        return TestResult(
            name="HTTP /capture",
            status="PASS" if ok else "FAIL",
            frames=1 if ok else 0,
            bytes_received=len(payload),
            elapsed_ms=round(elapsed, 1),
            detail=f"HTTP {response.status}; JPEG markers {'valid' if jpeg_ok(payload) else 'invalid'}",
        ), len(payload)
    except Exception as exc:
        return TestResult(name="HTTP /capture", status="FAIL", detail=f"{type(exc).__name__}: {exc}"), 0
    finally:
        connection.close()


def parse_mjpeg(body: bytes, boundary: bytes = b"aitlframe") -> list[bytes]:
    marker = b"--" + boundary
    frames: list[bytes] = []
    for part in body.split(marker):
        if b"Content-Type: image/jpeg" not in part:
            continue
        header_end = part.find(b"\r\n\r\n")
        if header_end < 0:
            continue
        header = part[:header_end].decode("latin1", errors="replace")
        content_length = None
        for line in header.split("\r\n"):
            if line.lower().startswith("content-length:"):
                try:
                    content_length = int(line.split(":", 1)[1].strip())
                except ValueError:
                    content_length = None
        payload = part[header_end + 4:]
        if content_length is not None:
            payload = payload[:content_length]
        else:
            payload = payload.rstrip(b"\r\n")
        if payload:
            frames.append(payload)
    return frames


def test_mjpeg(host: str, frames: int, fps: int) -> TestResult:
    started = time.perf_counter()
    connection = http.client.HTTPConnection(host, 80, timeout=max(CONTROL_TIMEOUT, frames / max(1, fps) + 5))
    try:
        connection.request("GET", f"/mjpeg?frames={frames}&fps={fps}", headers={"Connection": "close"})
        response = connection.getresponse()
        body = response.read()
        elapsed_s = max(0.001, time.perf_counter() - started)
        parsed = parse_mjpeg(body)
        good = sum(1 for frame in parsed if jpeg_ok(frame))
        ok = response.status == 200 and good == frames
        return TestResult(
            name=f"HTTP MJPEG {fps} FPS",
            status="PASS" if ok else "FAIL",
            frames=good,
            bytes_received=sum(len(frame) for frame in parsed),
            elapsed_ms=round(elapsed_s * 1000.0, 1),
            measured_fps=round(good / elapsed_s, 2),
            detail=f"HTTP {response.status}; {good}/{frames} complete JPEG parts",
        )
    except Exception as exc:
        return TestResult(name=f"HTTP MJPEG {fps} FPS", status="FAIL", detail=f"{type(exc).__name__}: {exc}")
    finally:
        connection.close()


def configure_mode(host: str, mode: str, fps: int, stall_ms: int, total_ms: int,
                   payload_bytes: int, chunk_bytes: int) -> None:
    http_json(host, "/stop", "POST")
    http_json(host, "/mode", "POST", {
        "mode": mode,
        "fps": fps,
        "stall_ms": stall_ms,
        "total_ms": total_ms,
        "payload_bytes": payload_bytes,
        "chunk_bytes": chunk_bytes,
    })
    http_json(host, "/start", "POST")


def test_atl1(host: str, *, label: str, mode: str, fps: int, frames: int,
              stall_ms: int, total_ms: int, payload_bytes: int, chunk_bytes: int) -> TestResult:
    sock: socket.socket | None = None
    arrivals: list[float] = []
    total = 0
    error: str | None = None
    try:
        configure_mode(host, mode, fps, stall_ms, total_ms, payload_bytes, chunk_bytes)
        started = time.perf_counter()
        sock = socket.create_connection((host, 81), timeout=3.0)
        sock.settimeout(STREAM_TIMEOUT)
        for _ in range(frames):
            header = read_exact(sock, ATL1_HEADER.size)
            magic, length, _sequence, _uptime = ATL1_HEADER.unpack(header)
            if magic != ATL1_MAGIC:
                raise ValueError(f"bad ATL1 magic {magic!r}")
            if length <= 0 or length > 8 * 1024 * 1024:
                raise ValueError(f"invalid ATL1 payload length {length}")
            payload = read_exact(sock, length)
            if not jpeg_ok(payload):
                raise ValueError("payload did not contain complete JPEG markers")
            total += len(header) + len(payload)
            arrivals.append(time.perf_counter())
        elapsed_s = max(0.001, time.perf_counter() - started)
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        elapsed_s = max(0.001, (time.perf_counter() - started) if 'started' in locals() else 0.001)
    finally:
        if sock is not None:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            sock.close()
        try:
            http_json(host, "/stop", "POST")
        except Exception:
            pass
        try:
            telemetry = http_json(host, "/status")
        except Exception as exc:
            telemetry = {"status_error": f"{type(exc).__name__}: {exc}"}

    got = len(arrivals)
    measured = 0.0
    if len(arrivals) >= 2:
        measured = (len(arrivals) - 1) / max(0.001, arrivals[-1] - arrivals[0])
    elif got:
        measured = got / elapsed_s
    passed = got == frames and error is None
    detail = f"{got}/{frames} frames"
    if error:
        detail += f"; {error}"
    if isinstance(telemetry, dict):
        detail += (
            f"; ESP send={telemetry.get('last_send_ms')} ms"
            f", accepted={telemetry.get('last_accepted_bytes')}/{(int(telemetry.get('last_frame_bytes') or 0) + ATL1_HEADER.size)} total"
            f", errno={telemetry.get('last_errno')}"
        )
    return TestResult(
        name=label,
        status="PASS" if passed else "FAIL",
        frames=got,
        bytes_received=total,
        elapsed_ms=round(elapsed_s * 1000.0, 1),
        measured_fps=round(measured, 2),
        detail=detail,
        telemetry=telemetry,
    )


def diagnose(results: dict[str, TestResult]) -> dict[str, Any]:
    passed = lambda key: results.get(key) is not None and results[key].status == "PASS"
    direct_short = passed("direct_1200")
    direct_long = passed("direct_5000")
    if not passed("capture"):
        code = "camera_capture_path_failure"
        summary = "Single HTTP JPEG capture failed; investigate camera initialization, power, sensor, or framebuffer first."
    elif not passed("mjpeg"):
        code = "persistent_camera_stream_failure"
        summary = "Single capture passed but finite MJPEG failed; persistent streaming/Wi-Fi/backpressure is implicated before ATL1 framing."
    elif not direct_short and direct_long:
        code = "production_timeout_too_aggressive"
        summary = "Direct ATL1 fails at the 1.2 s diagnostic limit but completes with 5 s; the current timeout is a material cause, though send latency is still abnormal."
    elif not direct_long and passed("staged") and passed("dram_copy") and passed("synthetic"):
        code = "direct_psram_send_unstable"
        summary = "MJPEG and internal-DRAM ATL1 paths pass while direct camera-framebuffer ATL1 fails; direct PSRAM→sendmsg is the leading cause."
    elif not direct_long and not passed("staged") and passed("synthetic"):
        code = "real_camera_persistent_transport_stall"
        summary = "Synthetic ATL1 works but both direct and staged real-camera streaming fail; investigate camera/Wi-Fi interaction or sustained receiver backpressure."
    elif not direct_long and not passed("synthetic"):
        code = "general_tcp_or_wifi_stall"
        summary = "Even same-size synthetic internal-DRAM ATL1 fails; focus on Wi-Fi/lwIP/socket/receiver behavior rather than PSRAM."
    elif all(item.status == "PASS" for item in results.values()):
        code = "healthy_under_isolation_test"
        summary = "All isolation paths passed in this run. Compare ESP send latency with the prior failure and repeat to catch intermittency."
    else:
        code = "mixed_transport_failure"
        summary = "The result pattern is mixed; use the per-test progress trace and repeat at 1 FPS before changing production code."
    return {"code": code, "summary": summary}


def print_table(results: list[TestResult]) -> None:
    print("\nAiTL camera transport isolation\n")
    print(f"{'Test':34} {'Result':6} {'Frames':>7} {'FPS':>7}  Detail")
    print("-" * 110)
    for item in results:
        fps = "-" if item.measured_fps is None else f"{item.measured_fps:.2f}"
        print(f"{item.name[:34]:34} {item.status:6} {item.frames:7d} {fps:>7}  {item.detail}")


def main() -> int:
    parser = argparse.ArgumentParser(description="AiTL 0_3_8 R3 camera transport isolation test")
    parser.add_argument("--host", required=True, help="ESP32-CAM private-LAN IPv4 address")
    parser.add_argument("--frames", type=int, default=6, help="Frames per streaming phase")
    parser.add_argument("--fps", type=int, default=5, help="Streaming target for 5 FPS phases")
    parser.add_argument("--frame-size", default="QVGA", choices=["QQVGA", "HQVGA", "QVGA", "CIF", "VGA"])
    parser.add_argument("--jpeg-quality", type=int, default=24)
    parser.add_argument("--output", type=Path, default=Path("camera_transport_isolation.json"))
    parser.add_argument("--chunk-sweep", action="store_true", help="Also run staged chunks 256/512/1024/1460/2920")
    args = parser.parse_args()

    host = args.host.strip()
    initial = http_json(host, "/status")
    if not str(initial.get("firmware", "")).startswith("aitl-0_3_8-r3-transport-diag"):
        raise SystemExit("The ESP is not running the AiTL 0_3_8 R3 transport diagnostic firmware.")
    http_json(host, "/config", "POST", {"frame_size": args.frame_size, "jpeg_quality": args.jpeg_quality})

    ordered: list[TestResult] = []
    capture, captured_bytes = test_capture(host)
    ordered.append(capture)
    ordered.append(test_mjpeg(host, args.frames, args.fps))
    payload_bytes = captured_bytes if 128 <= captured_bytes <= 32768 else 6000

    ordered.append(test_atl1(host, label="ATL1 direct @ 1.2 s", mode="direct", fps=1, frames=max(2, min(args.frames, 4)), stall_ms=1200, total_ms=2000, payload_bytes=payload_bytes, chunk_bytes=1460))
    ordered.append(test_atl1(host, label="ATL1 direct @ 5 s", mode="direct", fps=args.fps, frames=args.frames, stall_ms=5000, total_ms=7000, payload_bytes=payload_bytes, chunk_bytes=1460))
    ordered.append(test_atl1(host, label="ATL1 staged DRAM", mode="staged", fps=args.fps, frames=args.frames, stall_ms=5000, total_ms=7000, payload_bytes=payload_bytes, chunk_bytes=1460))
    ordered.append(test_atl1(host, label="ATL1 full JPEG DRAM copy", mode="dram_copy", fps=args.fps, frames=args.frames, stall_ms=5000, total_ms=7000, payload_bytes=payload_bytes, chunk_bytes=1460))
    ordered.append(test_atl1(host, label="ATL1 same-size synthetic DRAM", mode="synthetic", fps=args.fps, frames=args.frames, stall_ms=5000, total_ms=7000, payload_bytes=payload_bytes, chunk_bytes=1460))

    if args.chunk_sweep:
        for chunk in (256, 512, 1024, 1460, 2920):
            ordered.append(test_atl1(host, label=f"Staged chunk {chunk} B", mode="staged", fps=args.fps, frames=max(3, min(args.frames, 5)), stall_ms=5000, total_ms=7000, payload_bytes=payload_bytes, chunk_bytes=chunk))

    keys = ["capture", "mjpeg", "direct_1200", "direct_5000", "staged", "dram_copy", "synthetic"]
    primary = dict(zip(keys, ordered[:7]))
    diagnosis = diagnose(primary)
    report = {
        "schema_version": 1,
        "host": host,
        "generated_at_ms": int(time.time() * 1000),
        "settings": {"frame_size": args.frame_size, "jpeg_quality": args.jpeg_quality, "fps": args.fps},
        "captured_reference_bytes": captured_bytes,
        "diagnosis": diagnosis,
        "results": [asdict(item) for item in ordered],
    }
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print_table(ordered)
    print(f"\nDiagnosis: {diagnosis['code']}\n{diagnosis['summary']}")
    print(f"\nSaved report: {args.output.resolve()}")
    return 0 if not any(item.status == "FAIL" for item in ordered[:2]) else 2


if __name__ == "__main__":
    raise SystemExit(main())
