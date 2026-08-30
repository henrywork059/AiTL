from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, field
import http.client
import json
import math
import os
import platform
import socket
import sys
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

BENCHMARK_REVISION = "R5"
REPORT_SCHEMA_VERSION = 3

_PROGRESS = None


class ConsoleProgress:
    def __init__(self, *, host: str, environment: str, quiet: bool = False) -> None:
        self.host = host
        self.environment = environment
        self.quiet = quiet
        self.run_started = time.perf_counter()
        self.test_index = 0
        self.current_label = ""

    def _emit(self, text: str) -> None:
        if not self.quiet:
            print(text, flush=True)

    def banner(self, *, local_ip: str, settings: dict[str, Any]) -> None:
        self._emit("")
        self._emit("=" * 92)
        self._emit(f"AiTL 0_3_8 {BENCHMARK_REVISION} CAMERA TRANSPORT BENCHMARK")
        self._emit(f"ESP host        : {self.host}")
        self._emit(f"PC local IP     : {local_ip}")
        self._emit(f"Environment     : {self.environment}")
        self._emit(
            "Camera settings : "
            f"{settings.get('frame_size')} / JPEG q={settings.get('jpeg_quality')} / "
            f"primary {settings.get('fps')} FPS / {settings.get('frames')} frames"
        )
        self._emit("=" * 92)

    def section(self, title: str) -> None:
        self._emit("")
        self._emit(f"--- {title} ---")

    def start(self, label: str, context: str = "") -> None:
        self.test_index += 1
        self.current_label = label
        suffix = f" | {context}" if context else ""
        elapsed = time.perf_counter() - self.run_started
        self._emit(f"[{self.test_index:02d}] START  +{elapsed:6.1f}s | {label}{suffix}")

    def frame(self, completed: int, total: int, detail: str = "") -> None:
        suffix = f" | {detail}" if detail else ""
        self._emit(f"     RUN    {completed:>2}/{total:<2} | {self.current_label}{suffix}")

    def finish(self, result: "TestResult") -> None:
        fps = "-" if result.measured_fps is None else f"{result.measured_fps:.2f}"
        self._emit(
            f"     {result.status:<6} {result.frames}/{result.requested_frames} frames | "
            f"{fps} FPS | {result.elapsed_ms or 0:.0f} ms | {result.key}"
        )


def _progress_frame(completed: int, total: int, detail: str = "") -> None:
    if _PROGRESS is not None:
        _PROGRESS.frame(completed, total, detail)


def safe_device_status(host: str) -> dict[str, Any]:
    try:
        return http_json(host, "/status")
    except Exception as exc:
        return {"status_error": f"{type(exc).__name__}: {exc}"}


_COUNTER_FIELDS = (
    "frame_count", "send_failures", "deadline_drops",
    "mjpeg_frames_sent", "mjpeg_failures",
    "udp_frames_sent", "udp_packets_sent", "udp_send_failures",
)


def device_deltas(before: dict[str, Any], after: dict[str, Any]) -> dict[str, int]:
    output: dict[str, int] = {}
    for key in _COUNTER_FIELDS:
        try:
            output[key] = int(after.get(key, 0) or 0) - int(before.get(key, 0) or 0)
        except (TypeError, ValueError):
            continue
    return output


def resource_snapshot(status: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "uptime_ms", "rssi", "bssid", "channel", "free_heap", "internal_free",
        "internal_largest", "internal_min_free", "psram_free", "psram_total",
        "internal_total", "last_frame_bytes", "last_capture_ms", "last_send_ms",
        "last_accepted_bytes", "last_errno", "mode", "stall_timeout_ms",
        "total_send_limit_ms", "chunk_bytes",
    )
    return {key: status.get(key) for key in keys if key in status}


def enrich_result(host: str, value: Any, before: dict[str, Any], started_epoch_ms: int,
                  started_perf: float) -> Any:
    result = value[0] if isinstance(value, tuple) and value and isinstance(value[0], TestResult) else value
    if not isinstance(result, TestResult):
        return value
    after = safe_device_status(host)
    result.telemetry = dict(result.telemetry or {})
    result.telemetry["benchmark_timing"] = {
        "started_at_ms": started_epoch_ms,
        "ended_at_ms": int(time.time() * 1000),
        "wall_elapsed_ms": round((time.perf_counter() - started_perf) * 1000.0, 1),
    }
    result.telemetry["device_before"] = before
    result.telemetry["device_after"] = after
    result.telemetry["counter_deltas"] = device_deltas(before, after)
    result.telemetry["resource_before"] = resource_snapshot(before)
    result.telemetry["resource_after"] = resource_snapshot(after)
    if _PROGRESS is not None:
        _PROGRESS.finish(result)
    return value


def execute_test(host: str, label: str, fn: Callable[[], Any], *, context: str = "") -> Any:
    if _PROGRESS is not None:
        _PROGRESS.start(label, context)
    before = safe_device_status(host)
    started_epoch_ms = int(time.time() * 1000)
    started_perf = time.perf_counter()
    value = fn()
    return enrich_result(host, value, before, started_epoch_ms, started_perf)


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
                           headers={'Connection': 'close', 'User-Agent': 'AiTL-R5-Transport-Benchmark'})
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
    state: dict[str, Any] = {'successes': 0, 'failures': 0, 'latencies_ms': [], 'errors': [], 'samples': []}
    poll_started = time.perf_counter()

    def worker() -> None:
        while not stop.wait(interval):
            started = time.perf_counter()
            try:
                sample = http_json(host, '/status')
                latency_ms = (time.perf_counter() - started) * 1000.0
                state['successes'] += 1
                state['latencies_ms'].append(latency_ms)
                if len(state['samples']) < 160:
                    state['samples'].append({
                        'elapsed_ms': round((time.perf_counter() - poll_started) * 1000.0, 1),
                        'latency_ms': round(latency_ms, 1),
                        **resource_snapshot(sample),
                        'frame_count': sample.get('frame_count'),
                        'send_failures': sample.get('send_failures'),
                        'deadline_drops': sample.get('deadline_drops'),
                        'mjpeg_frames_sent': sample.get('mjpeg_frames_sent'),
                        'mjpeg_failures': sample.get('mjpeg_failures'),
                        'udp_frames_sent': sample.get('udp_frames_sent'),
                        'udp_packets_sent': sample.get('udp_packets_sent'),
                        'udp_send_failures': sample.get('udp_send_failures'),
                    })
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
    samples = list(state.get('samples') or [])
    def vals(key: str) -> list[float]:
        out: list[float] = []
        for sample in samples:
            value = sample.get(key)
            if isinstance(value, (int, float)):
                out.append(float(value))
        return out
    return {
        'successes': int(state.get('successes', 0)),
        'failures': int(state.get('failures', 0)),
        'avg_ms': round(statistics.mean(latencies), 1) if latencies else None,
        'p95_ms': round(sorted(latencies)[max(0, math.ceil(len(latencies) * .95) - 1)], 1) if latencies else None,
        'max_ms': round(max(latencies), 1) if latencies else None,
        'errors': list(state.get('errors') or []),
        'samples': samples,
        'sample_summary': {
            'rssi_min': min(vals('rssi')) if vals('rssi') else None,
            'rssi_max': max(vals('rssi')) if vals('rssi') else None,
            'internal_free_min': min(vals('internal_free')) if vals('internal_free') else None,
            'internal_largest_min': min(vals('internal_largest')) if vals('internal_largest') else None,
            'free_heap_min': min(vals('free_heap')) if vals('free_heap') else None,
            'psram_free_min': min(vals('psram_free')) if vals('psram_free') else None,
        },
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
    frame_records: list[dict[str, Any]] = []
    for index in range(1, frames + 1):
        frame_started = time.perf_counter()
        record: dict[str, Any] = {'index': index}
        try:
            status, payload, _ = _http(host, '/capture')
            latency = time.perf_counter() - frame_started
            latency_ms = latency * 1000.0
            latencies.append(latency_ms)
            valid = status == 200 and jpeg_ok(payload)
            record.update({'ok': valid, 'http_status': status, 'bytes': len(payload), 'latency_ms': round(latency_ms, 1)})
            if valid:
                good += 1
                total_bytes += len(payload)
            else:
                errors.append(f'HTTP {status} or invalid JPEG')
        except Exception as exc:
            message = f'{type(exc).__name__}: {exc}'
            errors.append(message)
            record.update({'ok': False, 'error': message, 'latency_ms': round((time.perf_counter() - frame_started) * 1000.0, 1)})
        frame_records.append(record)
        _progress_frame(index, frames, f"{'OK' if record.get('ok') else 'FAIL'}; {record.get('bytes', 0)} B; {record.get('latency_ms')} ms")
        spent = time.perf_counter() - frame_started
        if spent < deadline_period:
            time.sleep(deadline_period - spent)
    elapsed = max(0.001, time.perf_counter() - started)
    detail = f'{good}/{frames} complete snapshots; avg request {statistics.mean(latencies):.1f} ms' if latencies else f'{good}/{frames}; no successful requests'
    if errors:
        detail += f'; errors={errors[:3]}'
    telemetry = {
        'frame_records': frame_records,
        'latency_ms': {
            'avg': round(statistics.mean(latencies), 1) if latencies else None,
            'min': round(min(latencies), 1) if latencies else None,
            'max': round(max(latencies), 1) if latencies else None,
            'p95': round(sorted(latencies)[max(0, math.ceil(len(latencies) * .95) - 1)], 1) if latencies else None,
        },
        'errors': errors[:20],
    }
    return make_result(key='snapshot_polling', name=f'HTTP snapshot polling @ {fps} FPS', transport='HTTP snapshot',
                       requested=frames, frames=good, elapsed_s=elapsed, bytes_received=total_bytes, detail=detail,
                       telemetry=telemetry)

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
    frame_records: list[dict[str, Any]] = []
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
        for index in range(1, frames + 1):
            frame_started = time.perf_counter()
            header = read_exact(sock, ATL1_HEADER.size)
            magic, length, seq, source_uptime = ATL1_HEADER.unpack(header)
            if magic != ATL1_MAGIC:
                raise ValueError(f'bad ATL1 magic {magic!r}')
            if length <= 0 or length > 8 * 1024 * 1024:
                raise ValueError(f'invalid ATL1 payload length {length}')
            payload = read_exact(sock, length)
            if not jpeg_ok(payload):
                raise ValueError('payload did not contain complete JPEG markers')
            now = time.perf_counter()
            total_bytes += len(header) + len(payload)
            arrivals.append(now)
            interval_ms = (arrivals[-1] - arrivals[-2]) * 1000.0 if len(arrivals) >= 2 else None
            record = {
                'index': index,
                'sequence': seq,
                'source_uptime_ms': source_uptime,
                'payload_bytes': length,
                'receive_elapsed_ms': round((now - frame_started) * 1000.0, 1),
                'arrival_from_phase_start_ms': round((now - started) * 1000.0, 1),
                'interval_ms': round(interval_ms, 1) if interval_ms is not None else None,
                'jpeg_valid': True,
            }
            frame_records.append(record)
            _progress_frame(index, frames, f"seq={seq}; {length} B; recv={record['receive_elapsed_ms']} ms")
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
    intervals = [(b - a) * 1000.0 for a, b in zip(arrivals, arrivals[1:])]
    detail = f'{got}/{frames} complete frames'
    if error:
        detail += f'; {error}'
    if telemetry:
        detail += (f"; ESP send={telemetry.get('last_send_ms')} ms, accepted={telemetry.get('last_accepted_bytes')}, "
                   f"errno={telemetry.get('last_errno')}, internal_free={telemetry.get('internal_free')}")
    if poll_status:
        detail += f"; /status {poll.get('successes', 0)} ok/{poll.get('failures', 0)} fail"
    telemetry = {
        **telemetry,
        'mode_requested': mode,
        'test_parameters': {
            'fps': fps, 'frames': frames, 'stall_ms': stall_ms, 'total_ms': total_ms,
            'payload_bytes_control': payload_bytes, 'chunk_bytes': chunk_bytes,
            'pc_socket_rcvbuf_requested': 256 * 1024,
        },
        'frame_records': frame_records,
        'frame_size_bytes': [item['payload_bytes'] for item in frame_records],
        'sequence_numbers': [item['sequence'] for item in frame_records],
        'interval_ms': {
            'values': [round(x, 1) for x in intervals],
            'avg': round(statistics.mean(intervals), 1) if intervals else None,
            'p95': round(sorted(intervals)[max(0, math.ceil(len(intervals) * .95) - 1)], 1) if intervals else None,
            'max': round(max(intervals), 1) if intervals else None,
            'jitter_stddev': round(statistics.pstdev(intervals), 1) if len(intervals) >= 2 else 0.0,
        },
        'receiver_error': error,
        'status_poll': poll,
        'socket_role': 'minimal raw Python receiver; no decode/UI/inference',
    }
    result = make_result(key=key, name=label, transport='ATL1/TCP', requested=frames, frames=got,
                         elapsed_s=elapsed, bytes_received=total_bytes, detail=detail, telemetry=telemetry,
                         status_poll=poll, production_candidate=production_candidate)
    if got >= 2:
        result.measured_fps = round((got - 1) / max(0.001, arrivals[-1] - arrivals[0]), 2)
    return result

def configure_mjpeg(host: str, frames: int, fps: int) -> None:
    http_json(host, '/mjpeg/config', 'POST', {'frames': frames, 'fps': fps})


def parse_mjpeg_stream(sock: socket.socket, requested_frames: int) -> tuple[list[bytes], int, list[dict[str, Any]]]:
    buffer = bytearray()
    frames: list[bytes] = []
    records: list[dict[str, Any]] = []
    total_read = 0
    started = time.perf_counter()
    previous_arrival: float | None = None
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
            arrival = time.perf_counter()
            interval_ms = (arrival - previous_arrival) * 1000.0 if previous_arrival is not None else None
            previous_arrival = arrival
            records.append({
                'index': len(frames),
                'payload_bytes': len(payload),
                'jpeg_valid': jpeg_ok(payload),
                'arrival_from_phase_start_ms': round((arrival - started) * 1000.0, 1),
                'interval_ms': round(interval_ms, 1) if interval_ms is not None else None,
            })
            _progress_frame(len(frames), requested_frames, f"{len(payload)} B; JPEG={'OK' if jpeg_ok(payload) else 'BAD'}")
            del buffer[:needed]
            if len(frames) >= requested_frames:
                break
    return frames, total_read, records

def test_mjpeg(host: str, frames: int, fps: int, poll_status: bool = True) -> TestResult:
    sock: socket.socket | None = None
    started = time.perf_counter()
    poll_stop = threading.Event()
    poll_thread: threading.Thread | None = None
    poll_state: dict[str, Any] | None = None
    error: str | None = None
    parsed: list[bytes] = []
    records: list[dict[str, Any]] = []
    total_read = 0
    try:
        configure_mjpeg(host, frames, fps)
        sock = socket.create_connection((host, MJPEG_PORT), timeout=3.0)
        sock.settimeout(max(STREAM_TIMEOUT, frames / max(1, fps) + 5.0))
        request = f'GET /stream HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n\r\n'.encode()
        sock.sendall(request)
        if poll_status:
            poll_thread, poll_state = start_status_poller(host, poll_stop)
        parsed, total_read, records = parse_mjpeg_stream(sock, frames)
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
    intervals = [float(item['interval_ms']) for item in records if item.get('interval_ms') is not None]
    detail = f'{good}/{frames} complete JPEG parts'
    if error:
        detail += f'; {error}'
    if poll_status:
        detail += f"; /status {poll.get('successes', 0)} ok/{poll.get('failures', 0)} fail"
    telemetry = {
        **telemetry,
        'test_parameters': {'fps': fps, 'frames': frames, 'port': MJPEG_PORT},
        'frame_records': records,
        'frame_size_bytes': [len(frame) for frame in parsed],
        'interval_ms': {
            'values': intervals,
            'avg': round(statistics.mean(intervals), 1) if intervals else None,
            'p95': round(sorted(intervals)[max(0, math.ceil(len(intervals) * .95) - 1)], 1) if intervals else None,
            'max': round(max(intervals), 1) if intervals else None,
        },
        'receiver_error': error,
        'status_poll': poll,
    }
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
    completion_records: list[dict[str, Any]] = []
    packets = 0
    malformed = 0
    duplicate_chunks = 0
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
                packet, addr = recv.recvfrom(2048)
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
            item = reassembly.setdefault(seq, {'frame_length': frame_length, 'chunk_count': chunk_count, 'chunks': {}, 'first_packet_ms': round((time.perf_counter() - started) * 1000.0, 1)})
            if chunk_index in item['chunks']:
                duplicate_chunks += 1
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
                frame_bytes = bytes(frame)
                if valid and jpeg_ok(frame_bytes):
                    complete[seq] = frame_bytes
                    completion_records.append({
                        'sequence': seq,
                        'frame_bytes': frame_length,
                        'chunks': chunk_count,
                        'first_packet_ms': item.get('first_packet_ms'),
                        'completed_ms': round((time.perf_counter() - started) * 1000.0, 1),
                        'source_ip': addr[0],
                    })
                    _progress_frame(len(complete), frames, f"seq={seq}; {frame_length} B; chunks={chunk_count}")
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
    telemetry = {
        **telemetry,
        'test_parameters': {'fps': fps, 'frames': frames, 'chunk_bytes': chunk_bytes, 'pc_port': local_port, 'pc_ip': local_ip},
        'completion_records': completion_records,
        'packets_received': packets,
        'packets_sent_reported': expected_packets,
        'estimated_packet_loss': packet_loss,
        'malformed_packets': malformed,
        'duplicate_chunks': duplicate_chunks,
        'incomplete_frames_at_deadline': [
            {'sequence': seq, 'received_chunks': len(item['chunks']), 'expected_chunks': item['chunk_count'], 'frame_length': item['frame_length']}
            for seq, item in sorted(reassembly.items())[:20]
        ],
        'receiver_error': error,
        'status_poll': poll,
    }
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



def build_analysis_evidence(results: dict[str, TestResult], diagnosis: dict[str, Any]) -> dict[str, Any]:
    def view(key: str) -> dict[str, Any]:
        item = results.get(key)
        if item is None:
            return {'present': False}
        telemetry = item.telemetry or {}
        after = telemetry.get('device_after') if isinstance(telemetry.get('device_after'), dict) else telemetry
        before = telemetry.get('device_before') if isinstance(telemetry.get('device_before'), dict) else {}
        frame_bytes = after.get('last_frame_bytes') or telemetry.get('last_frame_bytes')
        accepted = after.get('last_accepted_bytes') or telemetry.get('last_accepted_bytes')
        try:
            accepted_ratio = round(float(accepted) / max(1.0, float(frame_bytes)), 4) if accepted is not None and frame_bytes else None
        except (TypeError, ValueError):
            accepted_ratio = None
        poll = telemetry.get('status_poll') if isinstance(telemetry.get('status_poll'), dict) else {}
        return {
            'present': True,
            'status': item.status,
            'frames': item.frames,
            'requested_frames': item.requested_frames,
            'completion_ratio': item.completion_ratio,
            'measured_fps': item.measured_fps,
            'elapsed_ms': item.elapsed_ms,
            'bytes_received': item.bytes_received,
            'packet_loss': item.packet_loss,
            'last_errno': after.get('last_errno'),
            'last_send_ms': after.get('last_send_ms'),
            'last_frame_bytes': frame_bytes,
            'last_accepted_bytes': accepted,
            'accepted_ratio': accepted_ratio,
            'rssi_before': before.get('rssi'),
            'rssi_after': after.get('rssi'),
            'internal_free_before': before.get('internal_free'),
            'internal_free_after': after.get('internal_free'),
            'internal_largest_before': before.get('internal_largest'),
            'internal_largest_after': after.get('internal_largest'),
            'poll_successes': poll.get('successes'),
            'poll_failures': poll.get('failures'),
            'poll_summary': poll.get('sample_summary'),
            'counter_deltas': telemetry.get('counter_deltas'),
            'receiver_error': telemetry.get('receiver_error'),
            'detail': item.detail,
        }

    pairs = {
        'timeout_1200_vs_5000': {'left': view('direct_sendmsg_1200'), 'right': view('direct_sendmsg_5000')},
        'direct_sendmsg_vs_plain_send': {'left': view('direct_sendmsg_5000'), 'right': view('direct_send')},
        'direct_psram_vs_staged_dram': {'left': view('direct_send'), 'right': view('staged_send')},
        'direct_psram_vs_full_dram_copy': {'left': view('direct_send'), 'right': view('dram_copy_send')},
        'dram_copy_sendmsg_vs_send': {'left': view('dram_copy_sendmsg'), 'right': view('dram_copy_send')},
        'real_camera_vs_synthetic_sendmsg': {'left': view('direct_sendmsg_5000'), 'right': view('synthetic_sendmsg')},
        'real_camera_vs_synthetic_send': {'left': view('direct_send'), 'right': view('synthetic_send')},
        'persistent_tcp_vs_mjpeg': {'left': view('dram_copy_send'), 'right': view('mjpeg')},
        'persistent_tcp_vs_udp': {'left': view('dram_copy_send'), 'right': view('udp')},
        'snapshot_vs_mjpeg': {'left': view('snapshot_polling'), 'right': view('mjpeg')},
    }

    hypotheses: list[dict[str, Any]] = []
    def add(name: str, confidence: str, evidence: list[str]) -> None:
        hypotheses.append({'hypothesis': name, 'confidence': confidence, 'evidence': evidence})

    p = lambda key: results.get(key) is not None and results[key].status == 'PASS'
    f = lambda key: results.get(key) is not None and results[key].status == 'FAIL'
    if f('direct_sendmsg_1200') and p('direct_sendmsg_5000'):
        add('configured timeout is materially contributing', 'high', ['1.2 s sendmsg fails while 5 s sendmsg passes'])
    if f('direct_sendmsg_5000') and p('direct_send'):
        add('sendmsg/vectored-write implementation is implicated', 'high', ['same direct PSRAM source fails with sendmsg and passes with plain send'])
    if f('direct_send') and (p('staged_send') or p('dram_copy_send')):
        add('direct PSRAM-to-socket access is implicated', 'high', ['camera data passes only after internal-DRAM staging/copy'])
    if f('direct_sendmsg_5000') and p('synthetic_sendmsg'):
        add('payload memory/camera interaction is more likely than generic sendmsg/lwIP', 'medium-high', ['synthetic internal-DRAM sendmsg passes while real-camera direct sendmsg fails'])
    if f('mjpeg') and f('dram_copy_send') and p('udp'):
        add('persistent TCP/backpressure/lwIP path is implicated', 'high', ['UDP passes while persistent TCP variants fail'])
    if f('mjpeg') and f('dram_copy_send') and f('udp'):
        add('Wi-Fi/power/general ESP resource pressure is implicated', 'high', ['independent persistent TCP, MJPEG and UDP transports fail'])
    if not hypotheses:
        add('no single dominant transport fault isolated', 'medium', [str(diagnosis.get('likely_bottleneck') or 'mixed evidence')])

    memory_rows = []
    for key, item in results.items():
        if not isinstance(item, TestResult) or item.status == 'SKIP':
            continue
        v = view(key)
        memory_rows.append({
            'key': key,
            'internal_free_before': v.get('internal_free_before'),
            'internal_free_after': v.get('internal_free_after'),
            'internal_largest_before': v.get('internal_largest_before'),
            'internal_largest_after': v.get('internal_largest_after'),
            'rssi_before': v.get('rssi_before'),
            'rssi_after': v.get('rssi_after'),
            'poll_summary': v.get('poll_summary'),
        })

    return {
        'primary_diagnosis_code': diagnosis.get('diagnosis_code'),
        'comparative_pairs': pairs,
        'hypothesis_ranking': hypotheses,
        'resource_and_rf_by_test': memory_rows,
        'analysis_hints': [
            'A failure at nearly 100% accepted bytes still counts as a failed JPEG frame; inspect accepted_ratio and progress_trace.',
            'If raw Python ATL1 passes but normal V038 PC Studio managed streaming later fails, focus on PC-side worker/backpressure rather than ESP transport.',
            'Compare resource minima during status polling, not only before/after values, because transient internal-RAM pressure can recover after a phase.',
            'Repeat the same benchmark on another AP/hotspot and power source if multiple unrelated transports fail.',
        ],
    }


def run_load_ladder(host: str, base_results: dict[str, TestResult], payload_bytes: int, frames: int, frame_size: str,
                    jpeg_quality: int) -> list[TestResult]:
    _ = (frame_size, jpeg_quality)
    ladder: list[TestResult] = []
    if _PROGRESS is not None:
        _PROGRESS.section('LOAD / HEADROOM FOLLOW-UP')
    for fps in (10, 15):
        if base_results.get('dram_copy_send') and base_results['dram_copy_send'].status == 'PASS':
            label = f'ATL1 DRAM-copy send() @ {fps} FPS'
            ladder.append(execute_test(host, label, lambda fps=fps, label=label: test_atl1(
                host, key=f'dram_copy_send_{fps}', label=label, mode='dram_copy_send', fps=fps, frames=frames,
                stall_ms=2000, total_ms=3000, payload_bytes=payload_bytes, chunk_bytes=1460, poll_status=False),
                context='load ladder'))
        if base_results.get('staged_send') and base_results['staged_send'].status == 'PASS':
            label = f'ATL1 staged send() @ {fps} FPS'
            ladder.append(execute_test(host, label, lambda fps=fps, label=label: test_atl1(
                host, key=f'staged_send_{fps}', label=label, mode='staged_send', fps=fps, frames=frames,
                stall_ms=2000, total_ms=3000, payload_bytes=payload_bytes, chunk_bytes=1460, poll_status=False),
                context='load ladder'))
        if base_results.get('mjpeg') and base_results['mjpeg'].status == 'PASS':
            label = f'Dedicated-port MJPEG @ {fps} FPS'
            item = execute_test(host, label, lambda fps=fps: test_mjpeg(host, frames, fps, poll_status=False), context='load ladder')
            item.key = f'mjpeg_{fps}'
            item.name = label
            ladder.append(item)
        if base_results.get('udp') and base_results['udp'].status == 'PASS':
            label = f'UDP freshness-first JPEG @ {fps} FPS'
            item = execute_test(host, label, lambda fps=fps: test_udp(host, frames, fps), context='load ladder')
            item.key = f'udp_{fps}'
            item.name = label
            ladder.append(item)
    return ladder

def print_table(results: list[TestResult], target_fps: int) -> None:
    print('\nAiTL 0_3_8 R5 camera transport benchmark\n')
    print(f"{'Test':42} {'Result':6} {'Frames':>8} {'FPS':>7} {'Score':>6}  Detail")
    print('-' * 145)
    for item in results:
        fps = '-' if item.measured_fps is None else f'{item.measured_fps:.2f}'
        score = '-' if not item.production_candidate else f'{score_candidate(item, target_fps):.1f}'
        frame_text = f'{item.frames}/{item.requested_frames}' if item.requested_frames else str(item.frames)
        print(f'{item.name[:42]:42} {item.status:6} {frame_text:>8} {fps:>7} {score:>6}  {item.detail}')


def main() -> int:
    global _PROGRESS
    parser = argparse.ArgumentParser(description='AiTL 0_3_8 R5 comprehensive ESP32-CAM transport benchmark')
    parser.add_argument('--host', required=True, help='ESP32-CAM private-LAN IPv4 address')
    parser.add_argument('--frames', type=int, default=8, help='Frames per primary streaming phase')
    parser.add_argument('--fps', type=int, default=5, help='Primary comparison FPS')
    parser.add_argument('--frame-size', default='QVGA', choices=['QQVGA', 'HQVGA', 'QVGA', 'CIF', 'VGA'])
    parser.add_argument('--jpeg-quality', type=int, default=24)
    parser.add_argument('--output', type=Path, default=Path('camera_transport_benchmark.json'))
    parser.add_argument('--environment-label', default='default-network', help='Label for AP/power/environment comparison')
    parser.add_argument('--chunk-sweep', action='store_true', help='Run staged-send chunk sweep 256/512/1024/1460/2920')
    parser.add_argument('--no-load-ladder', action='store_true', help='Skip 10/15 FPS follow-up on passing live candidates')
    parser.add_argument('--quiet', action='store_true', help='Suppress live per-test/per-frame progress; final table still prints')
    args = parser.parse_args()

    if args.frames < 2 or args.frames > 50:
        raise SystemExit('--frames must be 2..50')
    if args.fps < 1 or args.fps > 15:
        raise SystemExit('--fps must be 1..15')
    if args.jpeg_quality < 4 or args.jpeg_quality > 63:
        raise SystemExit('--jpeg-quality must be 4..63')

    run_started_epoch_ms = int(time.time() * 1000)
    run_started_perf = time.perf_counter()
    host = args.host.strip()
    local_ip = local_ip_for(host)
    _PROGRESS = ConsoleProgress(host=host, environment=args.environment_label, quiet=args.quiet)
    settings = {'frame_size': args.frame_size, 'jpeg_quality': args.jpeg_quality, 'fps': args.fps, 'frames': args.frames}
    _PROGRESS.banner(local_ip=local_ip, settings=settings)

    _PROGRESS.section('PREFLIGHT')
    _PROGRESS.start('ESP firmware / readiness probe', f'http://{host}:{CONTROL_PORT}/status')
    initial = http_json(host, '/status')
    expected_prefix = 'aitl-0_3_8-r5-transport-benchmark'
    if not str(initial.get('firmware', '')).startswith(expected_prefix):
        raise SystemExit(f'The ESP is not running the AiTL 0_3_8 R5 transport benchmark firmware (expected {expected_prefix}).')
    _PROGRESS._emit(
        f"     PASS   camera_ready={initial.get('camera_ready')} | RSSI={initial.get('rssi')} dBm | "
        f"internal_free={initial.get('internal_free')} | largest={initial.get('internal_largest')} | "
        f"PSRAM_free={initial.get('psram_free')}"
    )
    _PROGRESS.start('Apply benchmark image settings', f"{args.frame_size}, JPEG q={args.jpeg_quality}")
    configured = http_json(host, '/config', 'POST', {'frame_size': args.frame_size, 'jpeg_quality': args.jpeg_quality})
    _PROGRESS._emit(f"     PASS   frame_size={configured.get('frame_size', args.frame_size)} | jpeg_quality={configured.get('jpeg_quality', args.jpeg_quality)}")

    ordered: list[TestResult] = []

    _PROGRESS.section('BASE CAMERA / HTTP CONTROL')
    single, captured_bytes = execute_test(host, 'HTTP single /capture', lambda: test_single_capture(host), context='camera + one HTTP JPEG')
    ordered.append(single)
    ordered.append(execute_test(host, f'HTTP snapshot polling @ {args.fps} FPS',
                                lambda: test_snapshot_polling(host, args.frames, args.fps),
                                context='independent-frame fallback'))
    payload_bytes = captured_bytes if 128 <= captured_bytes <= 32768 else 6000

    _PROGRESS.section('PERSISTENT MJPEG / CURRENT ATL1 ISOLATION')
    ordered.append(execute_test(host, f'Dedicated-port MJPEG @ {args.fps} FPS',
                                lambda: test_mjpeg(host, args.frames, args.fps, poll_status=True),
                                context=f'port {MJPEG_PORT}; /status polling active'))
    ordered.append(execute_test(host, 'ATL1 direct PSRAM sendmsg() @ 1.2 s',
                                lambda: test_atl1(host, key='direct_sendmsg_1200', label='ATL1 direct PSRAM sendmsg() @ 1.2 s', mode='direct_sendmsg',
                                                  fps=1, frames=max(2, min(args.frames, 4)), stall_ms=1200, total_ms=2000,
                                                  payload_bytes=payload_bytes, chunk_bytes=1460, poll_status=False),
                                context='current-like timeout control; 1 FPS'))
    ordered.append(execute_test(host, 'ATL1 direct PSRAM sendmsg() @ 5 s',
                                lambda: test_atl1(host, key='direct_sendmsg_5000', label='ATL1 direct PSRAM sendmsg() @ 5 s', mode='direct_sendmsg',
                                                  fps=args.fps, frames=args.frames, stall_ms=5000, total_ms=7000,
                                                  payload_bytes=payload_bytes, chunk_bytes=1460, poll_status=True),
                                context='relaxed-timeout A/B; /status polling active'))
    ordered.append(execute_test(host, 'ATL1 direct PSRAM plain send()',
                                lambda: test_atl1(host, key='direct_send', label='ATL1 direct PSRAM plain send()', mode='direct_send',
                                                  fps=args.fps, frames=args.frames, stall_ms=5000, total_ms=7000,
                                                  payload_bytes=payload_bytes, chunk_bytes=1460, poll_status=True),
                                context='sendmsg vs send A/B'))

    _PROGRESS.section('MEMORY-SOURCE ISOLATION')
    ordered.append(execute_test(host, 'ATL1 1460-B DRAM staging + send()',
                                lambda: test_atl1(host, key='staged_send', label='ATL1 1460-B DRAM staging + send()', mode='staged_send',
                                                  fps=args.fps, frames=args.frames, stall_ms=5000, total_ms=7000,
                                                  payload_bytes=payload_bytes, chunk_bytes=1460, poll_status=True),
                                context='PSRAM copied in small DRAM chunks'))
    ordered.append(execute_test(host, 'ATL1 full JPEG DRAM copy + sendmsg()',
                                lambda: test_atl1(host, key='dram_copy_sendmsg', label='ATL1 full JPEG DRAM copy + sendmsg()', mode='dram_copy_sendmsg',
                                                  fps=args.fps, frames=args.frames, stall_ms=5000, total_ms=7000,
                                                  payload_bytes=payload_bytes, chunk_bytes=1460, poll_status=False),
                                context='same real JPEG, internal DRAM source'))
    ordered.append(execute_test(host, 'ATL1 full JPEG DRAM copy + send()',
                                lambda: test_atl1(host, key='dram_copy_send', label='ATL1 full JPEG DRAM copy + send()', mode='dram_copy_send',
                                                  fps=args.fps, frames=args.frames, stall_ms=5000, total_ms=7000,
                                                  payload_bytes=payload_bytes, chunk_bytes=1460, poll_status=True),
                                context='strongest ATL1 production candidate'))

    _PROGRESS.section('CAMERA-INDEPENDENT TCP CONTROLS')
    ordered.append(execute_test(host, 'Synthetic same-size DRAM + sendmsg()',
                                lambda: test_atl1(host, key='synthetic_sendmsg', label='Synthetic same-size DRAM + sendmsg()', mode='synthetic_sendmsg',
                                                  fps=args.fps, frames=args.frames, stall_ms=5000, total_ms=7000,
                                                  payload_bytes=payload_bytes, chunk_bytes=1460, poll_status=False, production_candidate=False),
                                context=f'synthetic payload ~= captured JPEG ({payload_bytes} B)'))
    ordered.append(execute_test(host, 'Synthetic same-size DRAM + send()',
                                lambda: test_atl1(host, key='synthetic_send', label='Synthetic same-size DRAM + send()', mode='synthetic_send',
                                                  fps=args.fps, frames=args.frames, stall_ms=5000, total_ms=7000,
                                                  payload_bytes=payload_bytes, chunk_bytes=1460, poll_status=False, production_candidate=False),
                                context=f'synthetic payload ~= captured JPEG ({payload_bytes} B)'))

    _PROGRESS.section('TCP-BYPASS CONTROL')
    ordered.append(execute_test(host, f'UDP freshness-first JPEG @ {args.fps} FPS',
                                lambda: test_udp(host, args.frames, args.fps),
                                context='removes TCP retransmission/backpressure'))

    ordered.extend([
        TestResult(key='websocket_assessment', name='WebSocket binary JPEG', transport='WebSocket/TCP', status='SKIP',
                   detail='Assessment only: still rides TCP/lwIP and adds handshake/framing, so it cannot bypass a lower-layer TCP stall.', production_candidate=False),
        TestResult(key='rtsp_assessment', name='RTSP/RTP or H.264', transport='RTSP/RTP', status='SKIP',
                   detail='Assessment only: changes stack/codec substantially; higher complexity than needed for current JPEG bottleneck isolation.', production_candidate=False),
        TestResult(key='split_esp_assessment', name='Separate camera ESP + signal ESP', transport='Architecture', status='SKIP',
                   detail='Architecture option, not a same-device transport benchmark; useful if camera/network and LED/control duties contend.', production_candidate=False),
    ])

    if args.chunk_sweep:
        _PROGRESS.section('DRAM STAGING CHUNK-SIZE SWEEP')
        for chunk in (256, 512, 1024, 1460, 2920):
            label = f'Staged DRAM chunk {chunk} B'
            ordered.append(execute_test(host, label,
                                        lambda chunk=chunk, label=label: test_atl1(host, key=f'staged_{chunk}', label=label, mode='staged_send',
                                                                                  fps=args.fps, frames=max(3, min(args.frames, 6)), stall_ms=5000, total_ms=7000,
                                                                                  payload_bytes=payload_bytes, chunk_bytes=chunk, poll_status=False),
                                        context='chunk-size sensitivity'))

    primary = {item.key: item for item in ordered}
    diagnosis = diagnose(primary, args.fps)
    ladder: list[TestResult] = []
    if not args.no_load_ladder:
        ladder = run_load_ladder(host, primary, payload_bytes, max(4, min(args.frames, 8)), args.frame_size, args.jpeg_quality)
        ordered.extend(ladder)

    final_status = safe_device_status(host)
    primary = {item.key: item for item in ordered}
    evidence = build_analysis_evidence(primary, diagnosis)
    run_finished_epoch_ms = int(time.time() * 1000)
    run_duration_ms = round((time.perf_counter() - run_started_perf) * 1000.0, 1)
    report = {
        'schema_version': REPORT_SCHEMA_VERSION,
        'benchmark_revision': BENCHMARK_REVISION,
        'firmware': initial.get('firmware'),
        'host': host,
        'pc_local_ip': local_ip,
        'environment_label': args.environment_label,
        'generated_at_ms': run_finished_epoch_ms,
        'run_context': {
            'started_at_ms': run_started_epoch_ms,
            'finished_at_ms': run_finished_epoch_ms,
            'duration_ms': run_duration_ms,
            'python_version': sys.version,
            'platform': platform.platform(),
            'os_name': os.name,
            'console_progress_enabled': not args.quiet,
            'raw_receiver_note': 'ATL1 benchmark receiver only reads framing/JPEG markers; it performs no UI rendering, inference, image decode, or CameraFrameService publication.',
        },
        'settings': settings,
        'reference_frame_bytes': captured_bytes,
        'initial_device': initial,
        'configured_device': configured,
        'final_device': final_status,
        'diagnosis': diagnosis,
        'analysis_evidence': evidence,
        'results': [asdict(item) for item in ordered],
        'test_plan': [
            {'stage': 'camera', 'tests': ['capture_single', 'snapshot_polling']},
            {'stage': 'persistent transports', 'tests': ['mjpeg', 'direct_sendmsg_1200', 'direct_sendmsg_5000', 'direct_send']},
            {'stage': 'memory source', 'tests': ['staged_send', 'dram_copy_sendmsg', 'dram_copy_send']},
            {'stage': 'synthetic controls', 'tests': ['synthetic_sendmsg', 'synthetic_send']},
            {'stage': 'TCP bypass', 'tests': ['udp']},
            {'stage': 'optional', 'tests': ['chunk sweep', '10/15 FPS load ladder']},
        ],
        'interpretation_notes': {
            'raw_receiver': 'ATL1 tests use a minimal Python socket receiver with no image decode/UI/inference. A pass here but failure in V038 managed-worker diagnostics isolates PC Studio integration/backpressure.',
            'websocket': 'Assessed but intentionally not benchmarked: WebSocket still uses TCP/lwIP and therefore cannot bypass a lower-level TCP stall.',
            'rtsp': 'Assessed but intentionally not benchmarked: it changes the transport stack substantially and is not required unless simpler stable transports are insufficient.',
            'status_samples': 'Key persistent phases retain up to 160 /status samples with control latency, RSSI, heap/internal-memory and transport counters so transient pressure is visible.',
            'progress_trace': 'ESP progress_trace shows bytes accepted versus elapsed send time for the most recent bounded send and is preserved in device snapshots.',
        },
    }
    args.output.write_text(json.dumps(report, indent=2), encoding='utf-8')

    _PROGRESS.section('FINAL RESULT')
    print_table(ordered, args.fps)
    print(f"\nDiagnosis: {diagnosis['diagnosis_code']}\n{diagnosis['likely_bottleneck']}")
    print(f"\nRecommended path: {diagnosis['recommended_key']}\n{diagnosis['recommendation']}")
    print(f'\nTotal benchmark time: {run_duration_ms / 1000.0:.1f} s')
    print(f'Saved detailed report: {args.output.resolve()}')
    return 0 if single.status == 'PASS' else 2


if __name__ == '__main__':
    raise SystemExit(main())
