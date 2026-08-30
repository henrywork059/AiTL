from __future__ import annotations

import http.client
import math
import socket
import statistics
import struct
import time
from typing import Any, Callable
from urllib.parse import urlencode

ATL1_HEADER = struct.Struct("!4sIII")
ATL1_MAGIC = b"ATL1"
CONTROL_PORT = 80
ATL1_PORT = 81


def _number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _integer(value: Any, default: int = 0) -> int:
    return int(_number(value, default))


def _http_json(host: str, path: str, method: str = "GET", query: dict[str, Any] | None = None) -> dict[str, Any]:
    target = path + (("?" + urlencode({k: str(v) for k, v in query.items()})) if query else "")
    connection = http.client.HTTPConnection(host, CONTROL_PORT, timeout=8.0)
    try:
        connection.request(
            method,
            target,
            body=b"" if method != "GET" else None,
            headers={"Connection": "close", "Accept": "application/json", "User-Agent": "AiTL-R8-Alternative-Followup"},
        )
        response = connection.getresponse()
        payload = response.read(256 * 1024)
        if response.status < 200 or response.status >= 300:
            raise RuntimeError(f"HTTP {response.status}: {payload[:200]!r}")
        import json

        parsed = json.loads(payload.decode("utf-8"))
        if not isinstance(parsed, dict):
            raise RuntimeError("ESP JSON response was not an object")
        return parsed
    finally:
        connection.close()


def _read_exact(sock: socket.socket, size: int, *, chunk_bytes: int | None = None, delay_ms: int = 0) -> bytes:
    output = bytearray(size)
    view = memoryview(output)
    offset = 0
    while offset < size:
        wanted = size - offset if not chunk_bytes else min(chunk_bytes, size - offset)
        count = sock.recv_into(view[offset : offset + wanted])
        if count == 0:
            raise EOFError(f"socket closed at {offset}/{size} bytes")
        offset += count
        if delay_ms > 0 and offset < size:
            time.sleep(delay_ms / 1000.0)
    return bytes(output)


def _result(
    *,
    key: str,
    name: str,
    transport: str,
    requested: int,
    frames: int,
    elapsed_s: float,
    bytes_received: int,
    detail: str,
    telemetry: dict[str, Any],
    production_candidate: bool = False,
) -> dict[str, Any]:
    measured_fps = frames / max(0.001, elapsed_s)
    return {
        "key": key,
        "name": name,
        "transport": transport,
        "status": "PASS" if frames == requested else "FAIL",
        "requested_frames": requested,
        "frames": frames,
        "bytes_received": bytes_received,
        "elapsed_ms": round(elapsed_s * 1000.0, 1),
        "measured_fps": round(measured_fps, 2),
        "completion_ratio": round(frames / requested, 3) if requested else 0.0,
        "status_poll_successes": 0,
        "status_poll_failures": 0,
        "packet_loss": None,
        "detail": detail,
        "telemetry": telemetry,
        "production_candidate": production_candidate,
    }


def _configure(host: str, *, mode: str, fps: int, payload_bytes: int, chunk_bytes: int = 1460) -> None:
    try:
        _http_json(host, "/stop", "POST")
    except Exception:
        pass
    _http_json(
        host,
        "/mode",
        "POST",
        {
            "mode": mode,
            "fps": fps,
            "stall_ms": 5000,
            "total_ms": 7000,
            "payload_bytes": payload_bytes,
            "chunk_bytes": chunk_bytes,
        },
    )
    _http_json(host, "/start", "POST")


def _run_atl1(
    host: str,
    *,
    key: str,
    name: str,
    mode: str,
    fps: int,
    frames: int,
    payload_bytes: int,
    requested_rcvbuf: int = 256 * 1024,
    read_chunk_bytes: int | None = None,
    read_delay_ms: int = 0,
    production_candidate: bool = False,
) -> dict[str, Any]:
    sock: socket.socket | None = None
    arrivals: list[float] = []
    total_bytes = 0
    records: list[dict[str, Any]] = []
    error: str | None = None
    actual_rcvbuf: int | None = None
    started = time.perf_counter()
    try:
        _configure(host, mode=mode, fps=fps, payload_bytes=payload_bytes)
        sock = socket.create_connection((host, ATL1_PORT), timeout=3.0)
        sock.settimeout(8.0)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, requested_rcvbuf)
            actual_rcvbuf = int(sock.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF))
        except OSError:
            actual_rcvbuf = None

        for index in range(1, frames + 1):
            frame_started = time.perf_counter()
            header = _read_exact(sock, ATL1_HEADER.size)
            magic, length, sequence, source_uptime_ms = ATL1_HEADER.unpack(header)
            if magic != ATL1_MAGIC:
                raise ValueError(f"bad ATL1 magic {magic!r}")
            if length <= 0 or length > 8 * 1024 * 1024:
                raise ValueError(f"invalid ATL1 payload length {length}")
            payload = _read_exact(sock, length, chunk_bytes=read_chunk_bytes, delay_ms=read_delay_ms)
            if len(payload) < 4 or not payload.startswith(b"\xff\xd8") or not payload.endswith(b"\xff\xd9"):
                raise ValueError("payload did not contain complete JPEG markers")
            now = time.perf_counter()
            arrivals.append(now)
            total_bytes += len(header) + len(payload)
            records.append(
                {
                    "index": index,
                    "sequence": sequence,
                    "payload_bytes": length,
                    "source_uptime_ms": source_uptime_ms,
                    "receive_elapsed_ms": round((now - frame_started) * 1000.0, 1),
                }
            )
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
    finally:
        elapsed = max(0.001, time.perf_counter() - started)
        if sock is not None:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            sock.close()
        try:
            _http_json(host, "/stop", "POST")
        except Exception:
            pass
        try:
            status = _http_json(host, "/status")
        except Exception as exc:
            status = {"status_error": f"{type(exc).__name__}: {exc}"}

    got = len(arrivals)
    measured_fps = 0.0
    if got >= 2:
        measured_fps = (got - 1) / max(0.001, arrivals[-1] - arrivals[0])
    elif got:
        measured_fps = got / elapsed
    detail = f"{got}/{frames} complete frames; requested/actual PC SO_RCVBUF={requested_rcvbuf}/{actual_rcvbuf or 'unknown'}"
    if read_delay_ms:
        detail += f"; receiver delay={read_delay_ms} ms per {read_chunk_bytes or 0} B read"
    if error:
        detail += f"; {error}"
    if status:
        detail += f"; ESP last_send={status.get('last_send_ms')} ms; accepted={status.get('last_accepted_bytes')}"

    result = _result(
        key=key,
        name=name,
        transport="ATL1/TCP follow-up",
        requested=frames,
        frames=got,
        elapsed_s=elapsed,
        bytes_received=total_bytes,
        detail=detail,
        telemetry={
            **status,
            "requested_rcvbuf": requested_rcvbuf,
            "actual_rcvbuf": actual_rcvbuf,
            "read_chunk_bytes": read_chunk_bytes,
            "read_delay_ms": read_delay_ms,
            "frame_records": records,
            "receiver_error": error,
        },
        production_candidate=production_candidate,
    )
    result["measured_fps"] = round(measured_fps, 2)
    return result


def _base_results(raw: dict[str, Any]) -> dict[str, dict[str, Any]]:
    values = raw.get("results") if isinstance(raw.get("results"), list) else []
    return {str(item.get("key")): item for item in values if isinstance(item, dict) and item.get("key")}


def extract_reference_size(raw: dict[str, Any]) -> int:
    by = _base_results(raw)
    candidates: list[int] = []
    for key in ("dram_copy_send", "direct_send", "dram_copy_send_10", "dram_copy_send_15", "staged_send"):
        item = by.get(key)
        if not item:
            continue
        telemetry = item.get("telemetry") if isinstance(item.get("telemetry"), dict) else {}
        sizes = telemetry.get("frame_size_bytes") if isinstance(telemetry.get("frame_size_bytes"), list) else []
        candidates.extend(_integer(value) for value in sizes if 512 <= _integer(value) <= 65536)
        if not sizes and _integer(item.get("frames")) > 0:
            approx = round((_integer(item.get("bytes_received")) / max(1, _integer(item.get("frames")))) - ATL1_HEADER.size)
            if 512 <= approx <= 65536:
                candidates.append(approx)
    if candidates:
        return int(statistics.median(candidates))
    fallback = _integer(raw.get("reference_frame_bytes"), 6000)
    return max(512, min(65536, fallback))


def _fps(item: dict[str, Any] | None) -> float:
    return _number((item or {}).get("measured_fps"))


def analyze_alternatives(raw: dict[str, Any], rows: list[dict[str, Any]], reference_bytes: int) -> dict[str, Any]:
    base = _base_results(raw)
    extra = {str(item.get("key")): item for item in rows if item.get("key")}
    real = base.get("dram_copy_send") or base.get("direct_send") or {}
    real_fps = _fps(real)
    same = extra.get(f"alt_synthetic_{reference_bytes}") or {}
    synthetic_fps = _fps(same)

    size_rows = [item for item in rows if str(item.get("key", "")).startswith("alt_synthetic_")]
    size_rows.sort(key=lambda item: _integer((item.get("telemetry") or {}).get("payload_bytes")))
    size_curve = [
        {
            "payload_bytes": _integer((item.get("telemetry") or {}).get("payload_bytes")),
            "fps": _fps(item),
            "status": item.get("status"),
        }
        for item in size_rows
    ]

    rcv_rows = [item for item in rows if str(item.get("key", "")).startswith("alt_rcvbuf_")]
    rcv_fps = [_fps(item) for item in rcv_rows if _fps(item) > 0]
    rcv_spread = ((max(rcv_fps) - min(rcv_fps)) / max(0.01, min(rcv_fps))) if len(rcv_fps) >= 2 else 0.0
    rcv_sensitive = rcv_spread >= 0.25

    fast = extra.get("alt_fast_drain") or {}
    slow = extra.get("alt_slow_drain") or {}
    fast_fps = _fps(fast)
    slow_fps = _fps(slow)
    drain_sensitive = fast_fps > 0 and slow_fps > 0 and slow_fps < fast_fps * 0.75

    mjpeg = base.get("mjpeg_10") or base.get("mjpeg") or {}
    mjpeg_fps = _fps(mjpeg)
    raw_api_difference = abs(mjpeg_fps - real_fps) / max(0.01, real_fps) if real_fps and mjpeg_fps else None

    staged = [(key, item) for key, item in base.items() if key.startswith("staged_") and _fps(item) > 0]
    best_staged = max(staged, key=lambda pair: _fps(pair[1])) if staged else None

    findings: list[str] = []
    if real_fps > 0 and synthetic_fps > 0:
        ratio = synthetic_fps / real_fps
        if ratio >= 1.5:
            classification = "real_camera_payload_path_specific"
            findings.append(
                f"Exact-size synthetic DRAM reaches {synthetic_fps:.2f} FPS versus {real_fps:.2f} FPS for real JPEG data; payload size alone does not explain the ceiling."
            )
        elif 0.75 <= ratio <= 1.35:
            classification = "payload_size_or_common_tcp_path"
            findings.append(
                f"Exact-size synthetic and real JPEG throughput are similar ({synthetic_fps:.2f} vs {real_fps:.2f} FPS); payload size/common TCP handling is the leading limiter."
            )
        else:
            classification = "mixed_payload_and_transport_effect"
            findings.append(
                f"Exact-size synthetic/real throughput ratio is {ratio:.2f}; neither size-only nor camera-only behavior fully explains the result."
            )
    else:
        classification = "insufficient_exact_size_evidence"
        findings.append("The exact-size synthetic A/B did not produce enough complete frames for a decisive comparison.")

    if rcv_sensitive:
        findings.append(f"PC receive-buffer size changes FPS materially ({rcv_spread * 100:.0f}% spread), so receiver buffering contributes to backpressure.")
    elif rcv_fps:
        findings.append(f"PC receive-buffer sweep changes FPS by only {rcv_spread * 100:.0f}%; PC SO_RCVBUF is unlikely to be the primary limiter.")

    if drain_sensitive:
        findings.append(f"Artificially slowing the PC drain reduces throughput from {fast_fps:.2f} to {slow_fps:.2f} FPS, confirming backpressure sensitivity.")
    elif fast_fps and slow_fps:
        findings.append(f"Artificial PC drain delay changes throughput from {fast_fps:.2f} to {slow_fps:.2f} FPS without a large collapse.")

    if raw_api_difference is not None:
        if raw_api_difference < 0.30:
            findings.append("MJPEG/WiFiClient.write() and raw ATL1 send() have similar real-camera throughput, so changing only the Arduino send API is unlikely to remove the ceiling.")
        else:
            findings.append("MJPEG/WiFiClient.write() and raw ATL1 send() differ materially; the sender API/framing implementation remains worth comparing.")

    if best_staged:
        findings.append(f"Best existing staged-chunk result is {best_staged[0]} at {_fps(best_staged[1]):.2f} FPS; chunk batching can be compared against whole-frame DRAM copy.")

    if classification == "payload_size_or_common_tcp_path":
        next_action = "Test ESP-side blocking send/WiFiClient.write/Nagle behavior in a dedicated diagnostic firmware, then compare a different 2.4 GHz AP and a known-good 5 V supply."
    elif classification == "real_camera_payload_path_specific":
        next_action = "Instrument DRAM-copy allocation/copy/cache/framebuffer-release timing and compare real JPEG bytes with exact-size synthetic bytes through the same sender."
    else:
        next_action = "Repeat the exact-size A/B on a second AP/power source before changing the production protocol."

    return {
        "revision": "R8-alternatives",
        "classification": classification,
        "confidence": "high" if same.get("status") == "PASS" and len(rcv_fps) >= 3 else "medium",
        "reference_real_jpeg_bytes": reference_bytes,
        "real_candidate_fps": round(real_fps, 2),
        "same_size_synthetic_fps": round(synthetic_fps, 2),
        "size_curve": size_curve,
        "receiver_buffer_spread_ratio": round(rcv_spread, 3),
        "receiver_buffer_sensitive": rcv_sensitive,
        "drain_sensitive": drain_sensitive,
        "mjpeg_wificlient_fps": round(mjpeg_fps, 2),
        "findings": findings,
        "next_action": next_action,
        "methods_assessed": [
            {"method": "ATL1 + whole-frame DRAM + plain send()", "status": "benchmarked", "role": "current preferred reliable path"},
            {"method": "Arduino WiFiClient.write()", "status": "benchmarked indirectly", "role": "used by current HTTP /capture and MJPEG firmware paths"},
            {"method": "staged DRAM chunking", "status": "benchmarked", "role": "lower-memory ATL1 alternative"},
            {"method": "UDP JPEG", "status": "benchmarked", "role": "TCP-bypass control; currently lossy"},
            {"method": "WebSocket", "status": "assessed only", "role": "still TCP/lwIP; unlikely to bypass lower-layer backpressure"},
            {"method": "RTSP/RTP", "status": "assessed only", "role": "larger stack change; UDP loss result weakens the case"},
            {"method": "raw lwIP tcp_write/tcp_output", "status": "future firmware A/B", "role": "lower-level option if socket APIs remain limiting"},
            {"method": "ESP-NOW", "status": "not suitable for this PC JPEG path", "role": "different peer model and packet constraints"},
        ],
    }


def run_alternative_followup(
    host: str,
    raw: dict[str, Any],
    *,
    progress: Callable[[str, str], None] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    reference_bytes = extract_reference_size(raw)
    settings = raw.get("settings") if isinstance(raw.get("settings"), dict) else {}
    fps = max(1, min(15, _integer(settings.get("fps"), 3)))
    frames = 4
    rows: list[dict[str, Any]] = []

    sizes = sorted({5000, 10000, 15000, reference_bytes, 20000, 25000})
    for payload_bytes in sizes:
        label = f"Synthetic DRAM plain send() @ {payload_bytes} B"
        if progress:
            progress("EXACT-SIZE SYNTHETIC PAYLOAD SWEEP", label)
        item = _run_atl1(
            host,
            key=f"alt_synthetic_{payload_bytes}",
            name=label,
            mode="synthetic_send",
            fps=fps,
            frames=frames,
            payload_bytes=payload_bytes,
            requested_rcvbuf=256 * 1024,
            production_candidate=False,
        )
        item["telemetry"]["payload_bytes"] = payload_bytes
        rows.append(item)

    for requested in (16 * 1024, 64 * 1024, 256 * 1024, 1024 * 1024):
        label = f"Real DRAM-copy send() with PC RCVBUF {requested // 1024} KiB"
        if progress:
            progress("PC RECEIVER BUFFER SWEEP", label)
        rows.append(
            _run_atl1(
                host,
                key=f"alt_rcvbuf_{requested}",
                name=label,
                mode="dram_copy_send",
                fps=fps,
                frames=frames,
                payload_bytes=reference_bytes,
                requested_rcvbuf=requested,
                production_candidate=False,
            )
        )

    if progress:
        progress("PC RECEIVER DRAIN A/B", "Fast-drain real DRAM-copy baseline")
    rows.append(
        _run_atl1(
            host,
            key="alt_fast_drain",
            name="Real DRAM-copy send() / fast PC drain",
            mode="dram_copy_send",
            fps=fps,
            frames=frames,
            payload_bytes=reference_bytes,
            requested_rcvbuf=256 * 1024,
            production_candidate=False,
        )
    )
    if progress:
        progress("PC RECEIVER DRAIN A/B", "Artificially throttled PC receiver")
    rows.append(
        _run_atl1(
            host,
            key="alt_slow_drain",
            name="Real DRAM-copy send() / throttled PC drain",
            mode="dram_copy_send",
            fps=fps,
            frames=frames,
            payload_bytes=reference_bytes,
            requested_rcvbuf=256 * 1024,
            read_chunk_bytes=1024,
            read_delay_ms=10,
            production_candidate=False,
        )
    )

    try:
        _http_json(host, "/stop", "POST")
        _http_json(host, "/mode", "POST", {"mode": "direct_sendmsg", "fps": fps, "stall_ms": 1200, "total_ms": 2000})
    except Exception:
        pass

    return rows, analyze_alternatives(raw, rows, reference_bytes)


__all__ = ["analyze_alternatives", "extract_reference_size", "run_alternative_followup"]
