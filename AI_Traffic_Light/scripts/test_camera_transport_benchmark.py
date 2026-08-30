from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, field
import http.client
import json
import math
import socket
import statistics
import struct
import threading
import time
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlencode

ATL1_HEADER = struct.Struct('!4sIII')
ATL1_MAGIC = b'ATL1'
UDP_HEADER = struct.Struct('!4sIHHIIH')
UDP_MAGIC = b'ATU1'
CONTROL_PORT = 80
ATL1_PORT = 81
MJPEG_PORT = 84
CONTROL_TIMEOUT = 8.0
STREAM_TIMEOUT = 8.0


@dataclass
class TestResult:
    key: str
    name: str
    transport: str
    status: str
    requested_frames: int = 0
    frames: int = 0
    bytes_received: int = 0
    elapsed_ms: float | None = None
    measured_fps: float | None = None
    completion_ratio: float = 0.0
    status_poll_successes: int = 0
    status_poll_failures: int = 0
    packet_loss: int | None = None
    detail: str = ''
    telemetry: dict[str, Any] = field(default_factory=dict)
    production_candidate: bool = True


def _http(host: str, path: str, method: str = 'GET', query: dict[str, Any] | None = None,
          *, expect_json: bool = False, timeout: float = CONTROL_TIMEOUT) -> tuple[int, bytes, dict[str, str]]:
    target = path + (('?' + urlencode({k: str(v) for k, v in query.items()})) if query else '')
    connection = http.client.HTTPConnection(host, CONTROL_PORT, timeout=timeout)
    try:
        connection.request(method, target, body=b'' if method != 'GET' else None,
                           headers={'Connection': 'close', 'User-Agent': 'AiTL-R4-Transport-Benchmark'})
        response = connection.getresponse()
        payload = response.read(512 * 1024)
        headers = {k.lower(): v for k, v in response.getheaders()}
        if response.status < 200 or response.status >= 300:
            raise RuntimeError(f'HTTP {response.status}: {payload[:300]!r}')
        if expect_json:
            json.loads(payload.decode('utf-8'))
        return response.status, payload, headers
    finally:
        connection.close()


def http_json(host: str, path: str, method: str = 'GET', query: dict[str, Any] | None = None) -> dict[str, Any]:
    _, payload, _ = _http(host, path, method, query, expect_json=True)
    parsed = json.loads(payload.decode('utf-8'))
    if not isinstance(parsed, dict):
        raise RuntimeError('JSON response was not an object')
    return parsed


def jpeg_ok(payload: bytes) -> bool:
    return len(payload) >= 4 and payload.startswith(b'\xff\xd8') and payload.endswith(b'\xff\xd9')


def read_exact(sock: socket.socket, size: int) -> bytes:
    data = bytearray(size)
    view = memoryview(data)
    offset = 0
    while offset < size:
        count = sock.recv_into(view[offset:])
        if count == 0:
            raise EOFError(f'socket closed at {offset}/{size} bytes')
        offset += count
    return bytes(data)


def start_status_poller(host: str, stop: threading.Event, interval: float = 0.25) -> tuple[threading.Thread, dict[str, Any]]:
    state: dict[str, Any] = {'successes': 0, 'failures': 0, 'latencies_ms': [], 'errors': []}

    def worker() -> None:
        while not stop.wait(interval):
            started = time.perf_counter()
            try:
                http_json(host, '/status')
                state['successes'] += 1
                state['latencies_ms'].append((time.perf_counter() - started) * 1000.0)
            except Exception as exc:  # diagnostic collector
                state['failures'] += 1
                if len(state['errors']) < 8:
                    state['errors'].append(f'{type(exc).__name__}: {exc}')

    thread = threading.Thread(target=worker, name='aitl-r4-status-poller', daemon=True)
    thread.start()
    return thread, state


def finish_status_poller(stop: threading.Event, thread: threading.Thread, state: dict[str, Any]) -> dict[str, Any]:
    stop.set()
    thread.join(timeout=2.0)
    latencies = state.get('latencies_ms') or []
    return {
        'successes': int(state.get('successes', 0)),
        'failures': int(state.get('failures', 0)),
        'avg_ms': round(statistics.mean(latencies), 1) if latencies else None,
        'max_ms': round(max(latencies), 1) if latencies else None,
        'errors': list(state.get('errors') or []),
    }


def make_result(*, key: str, name: str, transport: str, requested: int, frames: int,
                elapsed_s: float, bytes_received: int = 0, detail: str = '', telemetry: dict[str, Any] | None = None,
                status_poll: dict[str, Any] | None = None, packet_loss: int | None = None,
                production_candidate: bool = True, forced_status: str | None = None) -> TestResult:
    completion = (frames / requested) if requested > 0 else 0.0
    fps = frames / max(0.001, elapsed_s)
    status = forced_status or ('PASS' if frames == requested else 'FAIL')
    return TestResult(
        key=key,
        name=name,
        transport=transport,
        status=status,
        requested_frames=requested,
        frames=frames,
        bytes_received=bytes_received,
        elapsed_ms=round(elapsed_s * 1000.0, 1),
        measured_fps=round(fps, 2),
        completion_ratio=round(completion, 3),
        status_poll_successes=int((status_poll or {}).get('successes', 0)),
        status_poll_failures=int((status_poll or {}).get('failures', 0)),
        packet_loss=packet_loss,
        detail=detail,
        telemetry=telemetry or {},
        production_candidate=production_candidate,
    )


def test_single_capture(host: str) -> tuple[TestResult, int]:
    started = time.perf_counter()
    try:
        status, payload, _ = _http(host, '/capture')
        elapsed = max(0.001, time.perf_counter() - started)
        ok = status == 200 and jpeg_ok(payload)
        return make_result(
            key='capture_single', name='HTTP single /capture', transport='HTTP snapshot', requested=1,
            frames=1 if ok else 0, elapsed_s=elapsed, bytes_received=len(payload),
            detail=f'HTTP {status}; {len(payload)} B; JPEG markers {"valid" if jpeg_ok(payload) else "invalid"}',
            forced_status='PASS' if ok else 'FAIL'
        ), len(payload)
    except Exception as exc:
        elapsed = max(0.001, time.perf_counter() - started)
        return make_result(key='capture_single', name='HTTP single /capture', transport='HTTP snapshot', requested=1,
                           frames=0, elapsed_s=elapsed, detail=f'{type(exc).__name__}: {exc}', forced_status='FAIL'), 0


def test_snapshot_polling(host: str, frames: int, fps: int) -> TestResult:
    started = time.perf_counter()
    deadline_period = 1.0 / max(1, fps)
    good = 0
    total_bytes = 0
    errors: list[str] = []
    latencies: list[float] = []
    for _ in range(frames):
        frame_started = time.perf_counter()
        try:
            status, payload, _ = _http(host, '/capture')
            latency = time.perf_counter() - frame_started
            latencies.append(latency * 1000.0)
            if status == 200 and jpeg_ok(payload):
                good += 1
                total_bytes += len(payload)
            else:
                errors.append(f'HTTP {status} or invalid JPEG')
        except Exception as exc:
            errors.append(f'{type(exc).__name__}: {exc}')
        spent = time.perf_counter() - frame_started
        if spent < deadline_period:
            time.sleep(deadline_period - spent)
    elapsed = max(0.001, time.perf_counter() - started)
    detail = f'{good}/{frames} complete snapshots; avg request {statistics.mean(latencies):.1f} ms' if latencies else f'{good}/{frames}; no successful requests'
    if errors:
        detail += f'; errors={errors[:3]}'
    return make_result(key='snapshot_polling', name=f'HTTP snapshot polling @ {fps} FPS', transport='HTTP snapshot',
                       requested=frames, frames=good, elapsed_s=elapsed, bytes_received=total_bytes, detail=detail)


def configure_atl1(host: str, mode: str, fps: int, stall_ms: int, total_ms: int,
                   payload_bytes: int, chunk_bytes: int) -> None:
    try:
        http_json(host, '/stop', 'POST')
    except Exception:
        pass
    http_json(host, '/mode', 'POST', {
        'mode': mode, 'fps': fps, 'stall_ms': stall_ms, 'total_ms': total_ms,
        'payload_bytes': payload_bytes, 'chunk_bytes': chunk_bytes,
    })
    http_json(host, '/start', 'POST')


def test_atl1(host: str, *, key: str, label: str, mode: str, fps: int, frames: int,
              stall_ms: int, total_ms: int, payload_bytes: int, chunk_bytes: int,
              poll_status: bool = False, production_candidate: bool = True) -> TestResult:
    sock: socket.socket | None = None
    arrivals: list[float] = []
    total_bytes = 0
    error: str | None = None
    started = time.perf_counter()
    poll_stop = threading.Event()
    poll_thread: threading.Thread | None = None
    poll_state: dict[str, Any] | None = None
    try:
        configure_atl1(host, mode, fps, stall_ms, total_ms, payload_bytes, chunk_bytes)
        sock = socket.create_connection((host, ATL1_PORT), timeout=3.0)
        sock.settimeout(STREAM_TIMEOUT)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 256 * 1024)
        except OSError:
            pass
        if poll_status:
            poll_thread, poll_state = start_status_poller(host, poll_stop)
        for _ in range(frames):
            header = read_exact(sock, ATL1_HEADER.size)
            magic, length, _seq, _uptime = ATL1_HEADER.unpack(header)
            if magic != ATL1_MAGIC:
                raise ValueError(f'bad ATL1 magic {magic!r}')
            if length <= 0 or length > 8 * 1024 * 1024:
                raise ValueError(f'invalid ATL1 payload length {length}')
            payload = read_exact(sock, length)
            if not jpeg_ok(payload):
                raise ValueError('payload did not contain complete JPEG markers')
            total_bytes += len(header) + len(payload)
            arrivals.append(time.perf_counter())
    except Exception as exc:
        error = f'{type(exc).__name__}: {exc}'
    finally:
        elapsed = max(0.001, time.perf_counter() - started)
        poll = finish_status_poller(poll_stop, poll_thread, poll_state) if poll_thread is not None and poll_state is not None else {}
        if sock is not None:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            sock.close()
        try:
            http_json(host, '/stop', 'POST')
        except Exception:
            pass
        try:
            telemetry = http_json(host, '/status')
        except Exception as exc:
            telemetry = {'status_error': f'{type(exc).__name__}: {exc}'}
    got = len(arrivals)
    detail = f'{got}/{frames} complete frames'
    if error:
        detail += f'; {error}'
    if telemetry:
        detail += (f"; ESP send={telemetry.get('last_send_ms')} ms, accepted={telemetry.get('last_accepted_bytes')}, "
                   f"errno={telemetry.get('last_errno')}, internal_free={telemetry.get('internal_free')}")
    if poll_status:
        detail += f"; /status {poll.get('successes', 0)} ok/{poll.get('failures', 0)} fail"
    result = make_result(key=key, name=label, transport='ATL1/TCP', requested=frames, frames=got,
                         elapsed_s=elapsed, bytes_received=total_bytes, detail=detail, telemetry=telemetry,
                         status_poll=poll, production_candidate=production_candidate)
    if got >= 2:
        result.measured_fps = round((got - 1) / max(0.001, arrivals[-1] - arrivals[0]), 2)
    return result


def configure_mjpeg(host: str, frames: int, fps: int) -> None:
    http_json(host, '/mjpeg/config', 'POST', {'frames': frames, 'fps': fps})


def parse_mjpeg_stream(sock: socket.socket, requested_frames: int) -> tuple[list[bytes], int]:
    buffer = bytearray()
    frames: list[bytes] = []
    total_read = 0
    while len(frames) < requested_frames:
        chunk = sock.recv(65536)
        if not chunk:
            break
        total_read += len(chunk)
        buffer.extend(chunk)
        while True:
            header_end = buffer.find(b'\r\n\r\n')
            if header_end < 0:
                break
            header_blob = bytes(buffer[:header_end])
            if b'Content-Type: image/jpeg' not in header_blob:
                # Initial HTTP header; discard and continue.
                del buffer[:header_end + 4]
                continue
            length = None
            for line in header_blob.decode('latin1', errors='replace').split('\r\n'):
                if line.lower().startswith('content-length:'):
                    try:
                        length = int(line.split(':', 1)[1].strip())
                    except ValueError:
                        length = None
            if length is None:
                raise ValueError('MJPEG part missing Content-Length')
            needed = header_end + 4 + length + 2
            if len(buffer) < needed:
                break
            payload = bytes(buffer[header_end + 4:header_end + 4 + length])
            frames.append(payload)
            del buffer[:needed]
            if len(frames) >= requested_frames:
                break
    return frames, total_read


def test_mjpeg(host: str, frames: int, fps: int, poll_status: bool = True) -> TestResult:
    sock: socket.socket | None = None
    started = time.perf_counter()
    poll_stop = threading.Event()
    poll_thread: threading.Thread | None = None
    poll_state: dict[str, Any] | None = None
    error: str | None = None
    parsed: list[bytes] = []
    total_read = 0
    try:
        configure_mjpeg(host, frames, fps)
        sock = socket.create_connection((host, MJPEG_PORT), timeout=3.0)
        sock.settimeout(max(STREAM_TIMEOUT, frames / max(1, fps) + 5.0))
        request = f'GET /stream HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n\r\n'.encode()
        sock.sendall(request)
        if poll_status:
            poll_thread, poll_state = start_status_poller(host, poll_stop)
        parsed, total_read = parse_mjpeg_stream(sock, frames)
    except Exception as exc:
        error = f'{type(exc).__name__}: {exc}'
    finally:
        elapsed = max(0.001, time.perf_counter() - started)
        poll = finish_status_poller(poll_stop, poll_thread, poll_state) if poll_thread is not None and poll_state is not None else {}
        if sock is not None:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            sock.close()
        try:
            telemetry = http_json(host, '/status')
        except Exception as exc:
            telemetry = {'status_error': f'{type(exc).__name__}: {exc}'}
    good = sum(1 for frame in parsed if jpeg_ok(frame))
    detail = f'{good}/{frames} complete JPEG parts'
    if error:
        detail += f'; {error}'
    if poll_status:
        detail += f"; /status {poll.get('successes', 0)} ok/{poll.get('failures', 0)} fail"
    return make_result(key='mjpeg', name=f'Dedicated-port MJPEG @ {fps} FPS', transport='HTTP MJPEG',
                       requested=frames, frames=good, elapsed_s=elapsed, bytes_received=total_read,
                       detail=detail, telemetry=telemetry, status_poll=poll)


def local_ip_for(host: str) -> str:
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect((host, 9))
        return str(probe.getsockname()[0])
    finally:
        probe.close()


def test_udp(host: str, frames: int, fps: int, chunk_bytes: int = 1200) -> TestResult:
    recv = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    recv.bind(('0.0.0.0', 0))
    recv.settimeout(0.25)
    local_port = int(recv.getsockname()[1])
    local_ip = local_ip_for(host)
    started = time.perf_counter()
    reassembly: dict[int, dict[str, Any]] = {}
    complete: dict[int, bytes] = {}
    packets = 0
    malformed = 0
    error: str | None = None
    poll_stop = threading.Event()
    poll_thread: threading.Thread | None = None
    poll_state: dict[str, Any] | None = None
    poll: dict[str, Any] = {}
    try:
        http_json(host, '/udp/config', 'POST', {
            'remote_ip': local_ip,
            'remote_port': local_port,
            'frames': frames,
            'fps': fps,
            'chunk_bytes': chunk_bytes,
        })
        http_json(host, '/udp/start', 'POST')
        poll_thread, poll_state = start_status_poller(host, poll_stop)
        deadline = time.monotonic() + max(6.0, frames / max(1, fps) + 4.0)
        while time.monotonic() < deadline and len(complete) < frames:
            try:
                packet, _addr = recv.recvfrom(2048)
            except socket.timeout:
                continue
            packets += 1
            if len(packet) < UDP_HEADER.size:
                malformed += 1
                continue
            magic, seq, chunk_index, chunk_count, frame_length, offset, payload_length = UDP_HEADER.unpack(packet[:UDP_HEADER.size])
            payload = packet[UDP_HEADER.size:]
            if magic != UDP_MAGIC or payload_length != len(payload) or chunk_count == 0 or chunk_index >= chunk_count:
                malformed += 1
                continue
            item = reassembly.setdefault(seq, {'frame_length': frame_length, 'chunk_count': chunk_count, 'chunks': {}})
            item['chunks'][chunk_index] = (offset, payload)
            if len(item['chunks']) == chunk_count:
                frame = bytearray(frame_length)
                valid = True
                for _idx, (chunk_offset, chunk_payload) in item['chunks'].items():
                    end = chunk_offset + len(chunk_payload)
                    if end > frame_length:
                        valid = False
                        break
                    frame[chunk_offset:end] = chunk_payload
                if valid and jpeg_ok(bytes(frame)):
                    complete[seq] = bytes(frame)
                del reassembly[seq]
        try:
            http_json(host, '/udp/stop', 'POST')
        except Exception:
            pass
    except Exception as exc:
        error = f'{type(exc).__name__}: {exc}'
    finally:
        elapsed = max(0.001, time.perf_counter() - started)
        if poll_thread is not None and poll_state is not None:
            poll = finish_status_poller(poll_stop, poll_thread, poll_state)
        recv.close()
        try:
            telemetry = http_json(host, '/status')
        except Exception as exc:
            telemetry = {'status_error': f'{type(exc).__name__}: {exc}'}
    good = len(complete)
    expected_packets = int(telemetry.get('udp_packets_sent') or 0)
    packet_loss = max(0, expected_packets - packets) if expected_packets else None
    detail = f'{good}/{frames} complete frames; packets received={packets}'
    if packet_loss is not None:
        detail += f'; estimated packet loss={packet_loss}'
    if malformed:
        detail += f'; malformed={malformed}'
    if error:
        detail += f'; {error}'
    detail += f"; /status {poll.get('successes', 0)} ok/{poll.get('failures', 0)} fail"
    return make_result(key='udp', name=f'UDP freshness-first JPEG @ {fps} FPS', transport='UDP JPEG', requested=frames,
                       frames=good, elapsed_s=elapsed, bytes_received=sum(len(x) for x in complete.values()),
                       detail=detail, telemetry=telemetry, status_poll=poll, packet_loss=packet_loss)


def score_candidate(result: TestResult, target_fps: int) -> float:
    if not result.production_candidate:
        return -1.0
    completion = min(1.0, max(0.0, result.completion_ratio))
    fps_ratio = min(1.0, max(0.0, (result.measured_fps or 0.0) / max(1, target_fps)))
    control_penalty = min(20.0, result.status_poll_failures * 5.0)
    loss_penalty = min(20.0, float(result.packet_loss or 0) * 2.0)
    # Reliability dominates. Speed only decides among paths that actually complete frames.
    score = 70.0 * completion + 25.0 * fps_ratio + 5.0 - control_penalty - loss_penalty
    if result.status != 'PASS':
        score -= 15.0
    return round(max(0.0, min(100.0, score)), 1)


def diagnose(results: dict[str, TestResult], target_fps: int) -> dict[str, Any]:
    passed = lambda k: k in results and results[k].status == 'PASS'
    if not passed('capture_single'):
        code = 'camera_or_power_failure'
        cause = 'Camera capture itself is failing before transport comparison.'
    elif not passed('snapshot_polling'):
        code = 'repeated_capture_or_http_failure'
        cause = 'A single JPEG works but repeated independent captures are unstable; camera/power/control-path pressure is implicated.'
    elif not passed('direct_sendmsg_1200') and passed('direct_sendmsg_5000'):
        code = 'timeout_too_aggressive'
        cause = 'The current-like 1.2 s limit fails but the same direct sendmsg path completes with a relaxed timeout.'
    elif not passed('direct_sendmsg_5000') and passed('direct_send'):
        code = 'sendmsg_specific_failure'
        cause = 'Direct PSRAM data succeeds with plain send() but fails with sendmsg(); vectored sendmsg is the leading fault.'
    elif not passed('direct_send') and (passed('staged_send') or passed('dram_copy_send')):
        code = 'direct_psram_socket_source_failure'
        cause = 'Direct PSRAM-to-socket sending fails while the same camera data succeeds after internal-DRAM staging/copy.'
    elif not passed('direct_sendmsg_5000') and passed('mjpeg'):
        code = 'custom_tcp_sender_failure'
        cause = 'Persistent MJPEG succeeds while the custom ATL1 direct path fails; the raw sender implementation is the leading bottleneck.'
    elif not passed('mjpeg') and passed('snapshot_polling') and passed('udp'):
        code = 'persistent_tcp_backpressure'
        cause = 'Independent snapshots and UDP succeed while persistent TCP/MJPEG does not; sustained TCP/backpressure or receiver draining is implicated.'
    elif not passed('mjpeg') and not passed('staged_send') and not passed('dram_copy_send') and passed('udp'):
        code = 'tcp_lwip_path_failure'
        cause = 'UDP succeeds while multiple TCP variants fail; focus on TCP/lwIP/socket/backpressure rather than camera capture.'
    elif not passed('udp') and not passed('mjpeg') and not passed('dram_copy_send'):
        code = 'wifi_power_or_general_resource_failure'
        cause = 'Multiple independent transports fail; Wi-Fi RF quality, router behavior, power integrity, or ESP resource pressure is more likely than one framing method.'
    elif passed('direct_sendmsg_5000') and not passed('direct_sendmsg_1200'):
        code = 'latency_margin_problem'
        cause = 'Transport works only with a large timeout; this is functional but too slow for a healthy 5–15 FPS production path.'
    else:
        code = 'mixed_or_healthy'
        cause = 'No single failure signature dominates this run; use the ranking and environment comparison.'

    scored: list[dict[str, Any]] = []
    candidate_keys = ['dram_copy_send', 'staged_send', 'direct_send', 'mjpeg', 'snapshot_polling', 'udp', 'direct_sendmsg_5000']
    for key in candidate_keys:
        result = results.get(key)
        if result is None:
            continue
        scored.append({'key': key, 'name': result.name, 'score': score_candidate(result, target_fps), 'status': result.status})
    scored.sort(key=lambda item: (item['score'], item['status'] == 'PASS'), reverse=True)
    recommended = scored[0] if scored else None

    # Preserve the existing ATL1 architecture when it is genuinely stable; otherwise favor the simplest stable fallback.
    if passed('dram_copy_send'):
        recommendation = 'Use whole-frame internal-DRAM copy + plain send() for ATL1 first; it preserves the current PC protocol and releases the camera framebuffer before network transmission.'
        recommended_key = 'dram_copy_send'
    elif passed('staged_send'):
        recommendation = 'Use 1460-byte internal-DRAM staging + plain send() for ATL1; it preserves the protocol with lower RAM demand.'
        recommended_key = 'staged_send'
    elif passed('direct_send'):
        recommendation = 'Replace sendmsg() with ordinary send() while keeping ATL1; direct PSRAM access itself appears usable.'
        recommended_key = 'direct_send'
    elif passed('mjpeg'):
        recommendation = 'Use dedicated-port persistent MJPEG as the production fallback; it is stable in this benchmark and simpler than custom transport.'
        recommended_key = 'mjpeg'
    elif passed('snapshot_polling'):
        recommendation = 'Use independent HTTP /capture polling as the safe fallback while investigating persistent-stream pressure.'
        recommended_key = 'snapshot_polling'
    elif passed('udp'):
        recommendation = 'UDP is the only stable live candidate in this run; investigate TCP/lwIP/backpressure before considering UDP as production transport.'
        recommended_key = 'udp'
    else:
        recommendation = 'Do not switch protocol yet. Fix Wi-Fi/power/resource instability first because no transport is healthy.'
        recommended_key = None

    return {
        'diagnosis_code': code,
        'likely_bottleneck': cause,
        'recommended_key': recommended_key,
        'recommendation': recommendation,
        'ranking': scored,
        'assessed_not_benchmarked': [
            {
                'method': 'WebSocket binary JPEG',
                'reason': 'It still rides TCP/lwIP and adds handshake/framing code, so it cannot bypass the suspected lower-layer TCP stall. Add only if raw TCP is healthy and message framing itself remains suspect.'
            },
            {
                'method': 'RTSP/RTP or H.264',
                'reason': 'This changes the streaming stack/codec substantially and is not a fair isolation test for the current OV2640 JPEG path; it is higher complexity than required for AiTL.'
            },
            {
                'method': 'Separate camera ESP and signal-control ESP',
                'reason': 'This is an architecture/resource-isolation option rather than a same-device transport benchmark. It remains a strong fallback if camera streaming and LED/control duties contend on one node.'
            },
        ],
        'next_environment_checks': [
            'Repeat this exact benchmark close to the access point.',
            'Repeat on a different 2.4 GHz AP or phone hotspot and compare JSON reports.',
            'Repeat with a known-good 5 V supply and short wiring if multiple transports fail.',
            'After restoring production V037 firmware, run the built-in V038 Camera Diagnostics managed-worker phase. If raw transport passes here but PC Studio fails there, the bottleneck is PC-side integration/backpressure.'
        ],
    }


def run_load_ladder(host: str, base_results: dict[str, TestResult], payload_bytes: int, frames: int, frame_size: str,
                    jpeg_quality: int) -> list[TestResult]:
    _ = (frame_size, jpeg_quality)
    ladder: list[TestResult] = []
    for fps in (10, 15):
        if base_results.get('dram_copy_send') and base_results['dram_copy_send'].status == 'PASS':
            ladder.append(test_atl1(host, key=f'dram_copy_send_{fps}', label=f'ATL1 DRAM-copy send() @ {fps} FPS',
                                    mode='dram_copy_send', fps=fps, frames=frames, stall_ms=2000, total_ms=3000,
                                    payload_bytes=payload_bytes, chunk_bytes=1460, poll_status=False))
        if base_results.get('staged_send') and base_results['staged_send'].status == 'PASS':
            ladder.append(test_atl1(host, key=f'staged_send_{fps}', label=f'ATL1 staged send() @ {fps} FPS',
                                    mode='staged_send', fps=fps, frames=frames, stall_ms=2000, total_ms=3000,
                                    payload_bytes=payload_bytes, chunk_bytes=1460, poll_status=False))
        if base_results.get('mjpeg') and base_results['mjpeg'].status == 'PASS':
            ladder.append(test_mjpeg(host, frames, fps, poll_status=False))
            ladder[-1].key = f'mjpeg_{fps}'
            ladder[-1].name = f'Dedicated-port MJPEG @ {fps} FPS'
        if base_results.get('udp') and base_results['udp'].status == 'PASS':
            ladder.append(test_udp(host, frames, fps))
            ladder[-1].key = f'udp_{fps}'
            ladder[-1].name = f'UDP freshness-first JPEG @ {fps} FPS'
    return ladder


def print_table(results: list[TestResult], target_fps: int) -> None:
    print('\nAiTL 0_3_8 R4 camera transport benchmark\n')
    print(f"{'Test':42} {'Result':6} {'Frames':>8} {'FPS':>7} {'Score':>6}  Detail")
    print('-' * 145)
    for item in results:
        fps = '-' if item.measured_fps is None else f'{item.measured_fps:.2f}'
        score = '-' if not item.production_candidate else f'{score_candidate(item, target_fps):.1f}'
        frame_text = f'{item.frames}/{item.requested_frames}' if item.requested_frames else str(item.frames)
        print(f'{item.name[:42]:42} {item.status:6} {frame_text:>8} {fps:>7} {score:>6}  {item.detail}')


def main() -> int:
    parser = argparse.ArgumentParser(description='AiTL 0_3_8 R4 comprehensive ESP32-CAM transport benchmark')
    parser.add_argument('--host', required=True, help='ESP32-CAM private-LAN IPv4 address')
    parser.add_argument('--frames', type=int, default=8, help='Frames per primary streaming phase')
    parser.add_argument('--fps', type=int, default=5, help='Primary comparison FPS')
    parser.add_argument('--frame-size', default='QVGA', choices=['QQVGA', 'HQVGA', 'QVGA', 'CIF', 'VGA'])
    parser.add_argument('--jpeg-quality', type=int, default=24)
    parser.add_argument('--output', type=Path, default=Path('camera_transport_benchmark.json'))
    parser.add_argument('--environment-label', default='default-network', help='Label for AP/power/environment comparison')
    parser.add_argument('--chunk-sweep', action='store_true', help='Run staged-send chunk sweep 256/512/1024/1460/2920')
    parser.add_argument('--no-load-ladder', action='store_true', help='Skip 10/15 FPS follow-up on passing live candidates')
    args = parser.parse_args()

    if args.frames < 2 or args.frames > 50:
        raise SystemExit('--frames must be 2..50')
    if args.fps < 1 or args.fps > 15:
        raise SystemExit('--fps must be 1..15')
    if args.jpeg_quality < 4 or args.jpeg_quality > 63:
        raise SystemExit('--jpeg-quality must be 4..63')

    host = args.host.strip()
    initial = http_json(host, '/status')
    if not str(initial.get('firmware', '')).startswith('aitl-0_3_8-r4-transport-benchmark'):
        raise SystemExit('The ESP is not running the AiTL 0_3_8 R4 transport benchmark firmware.')
    http_json(host, '/config', 'POST', {'frame_size': args.frame_size, 'jpeg_quality': args.jpeg_quality})

    ordered: list[TestResult] = []
    single, captured_bytes = test_single_capture(host)
    ordered.append(single)
    ordered.append(test_snapshot_polling(host, args.frames, args.fps))
    payload_bytes = captured_bytes if 128 <= captured_bytes <= 32768 else 6000

    ordered.append(test_mjpeg(host, args.frames, args.fps, poll_status=True))
    ordered.append(test_atl1(host, key='direct_sendmsg_1200', label='ATL1 direct PSRAM sendmsg() @ 1.2 s', mode='direct_sendmsg',
                             fps=1, frames=max(2, min(args.frames, 4)), stall_ms=1200, total_ms=2000,
                             payload_bytes=payload_bytes, chunk_bytes=1460, poll_status=False))
    ordered.append(test_atl1(host, key='direct_sendmsg_5000', label='ATL1 direct PSRAM sendmsg() @ 5 s', mode='direct_sendmsg',
                             fps=args.fps, frames=args.frames, stall_ms=5000, total_ms=7000,
                             payload_bytes=payload_bytes, chunk_bytes=1460, poll_status=True))
    ordered.append(test_atl1(host, key='direct_send', label='ATL1 direct PSRAM plain send()', mode='direct_send',
                             fps=args.fps, frames=args.frames, stall_ms=5000, total_ms=7000,
                             payload_bytes=payload_bytes, chunk_bytes=1460, poll_status=True))
    ordered.append(test_atl1(host, key='staged_send', label='ATL1 1460-B DRAM staging + send()', mode='staged_send',
                             fps=args.fps, frames=args.frames, stall_ms=5000, total_ms=7000,
                             payload_bytes=payload_bytes, chunk_bytes=1460, poll_status=True))
    ordered.append(test_atl1(host, key='dram_copy_sendmsg', label='ATL1 full JPEG DRAM copy + sendmsg()', mode='dram_copy_sendmsg',
                             fps=args.fps, frames=args.frames, stall_ms=5000, total_ms=7000,
                             payload_bytes=payload_bytes, chunk_bytes=1460, poll_status=False))
    ordered.append(test_atl1(host, key='dram_copy_send', label='ATL1 full JPEG DRAM copy + send()', mode='dram_copy_send',
                             fps=args.fps, frames=args.frames, stall_ms=5000, total_ms=7000,
                             payload_bytes=payload_bytes, chunk_bytes=1460, poll_status=True))
    ordered.append(test_atl1(host, key='synthetic_sendmsg', label='Synthetic same-size DRAM + sendmsg()', mode='synthetic_sendmsg',
                             fps=args.fps, frames=args.frames, stall_ms=5000, total_ms=7000,
                             payload_bytes=payload_bytes, chunk_bytes=1460, poll_status=False, production_candidate=False))
    ordered.append(test_atl1(host, key='synthetic_send', label='Synthetic same-size DRAM + send()', mode='synthetic_send',
                             fps=args.fps, frames=args.frames, stall_ms=5000, total_ms=7000,
                             payload_bytes=payload_bytes, chunk_bytes=1460, poll_status=False, production_candidate=False))
    ordered.append(test_udp(host, args.frames, args.fps))
    ordered.extend([
        TestResult(key='websocket_assessment', name='WebSocket binary JPEG', transport='WebSocket/TCP', status='SKIP',
                   detail='Assessment only: still rides TCP/lwIP and adds handshake/framing, so it cannot bypass a lower-layer TCP stall.', production_candidate=False),
        TestResult(key='rtsp_assessment', name='RTSP/RTP or H.264', transport='RTSP/RTP', status='SKIP',
                   detail='Assessment only: changes stack/codec substantially; higher complexity than needed for current JPEG bottleneck isolation.', production_candidate=False),
        TestResult(key='split_esp_assessment', name='Separate camera ESP + signal ESP', transport='Architecture', status='SKIP',
                   detail='Architecture option, not a same-device transport benchmark; useful if camera/network and LED/control duties contend.', production_candidate=False),
    ])

    if args.chunk_sweep:
        for chunk in (256, 512, 1024, 1460, 2920):
            ordered.append(test_atl1(host, key=f'staged_{chunk}', label=f'Staged DRAM chunk {chunk} B', mode='staged_send',
                                     fps=args.fps, frames=max(3, min(args.frames, 6)), stall_ms=5000, total_ms=7000,
                                     payload_bytes=payload_bytes, chunk_bytes=chunk, poll_status=False))

    primary = {item.key: item for item in ordered}
    diagnosis = diagnose(primary, args.fps)
    ladder: list[TestResult] = []
    if not args.no_load_ladder:
        ladder = run_load_ladder(host, primary, payload_bytes, max(4, min(args.frames, 8)), args.frame_size, args.jpeg_quality)
        ordered.extend(ladder)

    final_status = http_json(host, '/status')
    report = {
        'schema_version': 2,
        'firmware': initial.get('firmware'),
        'host': host,
        'environment_label': args.environment_label,
        'generated_at_ms': int(time.time() * 1000),
        'settings': {'frame_size': args.frame_size, 'jpeg_quality': args.jpeg_quality, 'fps': args.fps, 'frames': args.frames},
        'reference_frame_bytes': captured_bytes,
        'initial_device': initial,
        'final_device': final_status,
        'diagnosis': diagnosis,
        'results': [asdict(item) for item in ordered],
        'interpretation_notes': {
            'raw_receiver': 'ATL1 tests use a minimal Python socket receiver with no image decode/UI/inference. A pass here but failure in V038 managed-worker diagnostics isolates PC Studio integration/backpressure.',
            'websocket': 'Assessed but intentionally not benchmarked: WebSocket still uses TCP/lwIP and therefore cannot bypass a lower-level TCP stall.',
            'rtsp': 'Assessed but intentionally not benchmarked: it changes the transport stack substantially and is not required unless simpler stable transports are insufficient.',
        },
    }
    args.output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print_table(ordered, args.fps)
    print(f"\nDiagnosis: {diagnosis['diagnosis_code']}\n{diagnosis['likely_bottleneck']}")
    print(f"\nRecommended path: {diagnosis['recommended_key']}\n{diagnosis['recommendation']}")
    print(f'\nSaved report: {args.output.resolve()}')
    return 0 if single.status == 'PASS' else 2


if __name__ == '__main__':
    raise SystemExit(main())
