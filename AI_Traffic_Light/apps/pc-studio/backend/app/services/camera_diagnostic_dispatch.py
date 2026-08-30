from __future__ import annotations

from copy import deepcopy
import http.client
import json
from pathlib import Path
import re
import statistics
import subprocess
import sys
import tempfile
from threading import Lock
import time
from typing import Any
from urllib.parse import urlencode
from uuid import uuid4

from app.core.error_codes import ErrorCode
from app.core.exceptions import AppError
from app.services.camera_diagnostics import camera_diagnostic_service
from app.services.remote_camera_manager import remote_camera_manager

BENCHMARK_PREFIX = "aitl-0_3_8-r5-transport-benchmark"
BENCHMARK_SCRIPT = "test_camera_transport_benchmark.py"
START_RE = re.compile(r"^\[(\d+)\]\s+START\s+\+\s*[\d.]+s\s+\|\s+(.+?)(?:\s+\|\s+(.+))?$")
FRAME_RE = re.compile(r"^\s*RUN\s+(\d+)\s*/\s*(\d+)\s+\|\s+(.+)$")
FINISH_RE = re.compile(r"^\s*(PASS|FAIL|SKIP)\s+(\d+)\s*/\s*(\d+)\s+frames\s+\|\s+(.+)$")
SECTION_RE = re.compile(r"^---\s+(.+?)\s+---$")


def n(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def i(value: Any, default: int = 0) -> int:
    return int(n(value, default))


def stats(values: list[float]) -> dict[str, float | None]:
    clean = [float(v) for v in values if isinstance(v, (int, float))]
    if not clean:
        return {"count": 0, "avg": None, "p95": None, "max": None}
    ordered = sorted(clean)
    p95_index = max(0, min(len(ordered) - 1, int((len(ordered) * 0.95) + 0.999999) - 1))
    return {
        "count": len(clean),
        "avg": round(statistics.mean(clean), 1),
        "p95": round(ordered[p95_index], 1),
        "max": round(max(clean), 1),
    }


def phase(result: dict[str, Any], target: int) -> dict[str, Any]:
    frames = i(result.get("frames")); elapsed = max(1.0, n(result.get("elapsed_ms"))); bytes_in = i(result.get("bytes_received")); fps = n(result.get("measured_fps"))
    failed = str(result.get("status")) == "FAIL"
    return {
        "target_fps": target, "duration_seconds": round(elapsed / 1000.0, 2), "frames": frames,
        "bytes_received": bytes_in, "throughput_mbps": round(bytes_in * 8.0 / elapsed / 1000.0, 3),
        "measured_fps": round(fps, 2), "fps_ratio": round(fps / max(1, target), 3), "connections": 1 if frames else 0,
        "disconnects": 1 if failed and not frames else 0, "sequence_gaps": max(0, i(result.get("packet_loss"))), "bad_frames": 0,
        "payload_avg_bytes": round(bytes_in / frames) if frames else 0, "payload_min_bytes": 0, "payload_max_bytes": 0,
        "interval_avg_ms": None, "interval_p50_ms": None, "interval_p95_ms": None, "interval_max_ms": None, "jitter_ms": None,
        "stall_intervals": 0, "status_poll_successes": i(result.get("status_poll_successes")), "status_poll_failures": i(result.get("status_poll_failures")),
        "status_poll_avg_ms": None, "unexpected_send_failures": 0, "deadline_drops": 0, "slow_frames": 0,
        "rssi_avg": None, "rssi_min": None, "rssi_max": None, "device_send_ewma_ms": None, "device_last_capture_ms": None,
        "phase_boundary_send_resets": 0, "errors": [],
    }


def _telemetry(item: dict[str, Any]) -> dict[str, Any]:
    value = item.get("telemetry")
    return value if isinstance(value, dict) else {}


def _after_status(item: dict[str, Any]) -> dict[str, Any]:
    telemetry = _telemetry(item)
    after = telemetry.get("device_after")
    if isinstance(after, dict):
        return after
    return telemetry


def _unique_frame_samples(item: dict[str, Any]) -> list[dict[str, Any]]:
    telemetry = _telemetry(item)
    poll = telemetry.get("status_poll") if isinstance(telemetry.get("status_poll"), dict) else {}
    samples = poll.get("samples") if isinstance(poll.get("samples"), list) else []
    output: list[dict[str, Any]] = []
    seen: set[int] = set()
    for sample in samples:
        if not isinstance(sample, dict):
            continue
        frame_count = i(sample.get("frame_count"), -1)
        if frame_count <= 0 or frame_count in seen:
            continue
        seen.add(frame_count)
        output.append(sample)
    if output:
        return output
    after = _after_status(item)
    if after and (after.get("last_capture_ms") is not None or after.get("last_send_ms") is not None):
        return [after]
    return []


def _timing_row(item: dict[str, Any], target_fps: int) -> dict[str, Any]:
    samples = _unique_frame_samples(item)
    capture_values = [n(sample.get("last_capture_ms")) for sample in samples if sample.get("last_capture_ms") is not None]
    send_values = [n(sample.get("last_send_ms")) for sample in samples if sample.get("last_send_ms") is not None]
    telemetry = _telemetry(item)
    intervals = telemetry.get("interval_ms") if isinstance(telemetry.get("interval_ms"), dict) else {}
    interval_avg = n(intervals.get("avg"), 0.0) or (1000.0 / max(0.01, n(item.get("measured_fps"), 0.0)) if n(item.get("measured_fps")) > 0 else 0.0)
    capture_stats = stats(capture_values)
    send_stats = stats(send_values)
    capture_avg = n(capture_stats.get("avg")); send_avg = n(send_stats.get("avg"))
    accounted = capture_avg + send_avg
    residual = max(0.0, interval_avg - accounted) if interval_avg > 0 else 0.0
    return {
        "key": str(item.get("key") or "unknown"),
        "status": str(item.get("status") or "SKIP"),
        "measured_fps": n(item.get("measured_fps")),
        "target_fps": target_fps,
        "target_period_ms": round(1000.0 / max(1, target_fps), 1),
        "observed_interval_ms": round(interval_avg, 1) if interval_avg > 0 else None,
        "capture_ms": capture_stats,
        "send_ms": send_stats,
        "accounted_ms": round(accounted, 1),
        "unexplained_ms": round(residual, 1),
        "accounted_ratio": round(accounted / interval_avg, 3) if interval_avg > 0 else None,
        "sample_count": max(i(capture_stats.get("count")), i(send_stats.get("count"))),
    }


def build_pipeline_timing_analysis(raw: dict[str, Any], capture_probe: dict[str, Any]) -> dict[str, Any]:
    results = [x for x in raw.get("results", []) if isinstance(x, dict)]
    by = {str(x.get("key")): x for x in results if x.get("key")}
    diag = raw.get("diagnosis") if isinstance(raw.get("diagnosis"), dict) else {}
    settings = raw.get("settings") if isinstance(raw.get("settings"), dict) else {}
    target = max(1, i(settings.get("fps"), 5))
    recommended = str(diag.get("recommended_key") or "")
    candidate = by.get(recommended) if recommended else None
    if not isinstance(candidate, dict):
        candidate = next((x for x in results if x.get("production_candidate") is True and x.get("status") == "PASS" and i(x.get("requested_frames")) >= 2), {})
    candidate_row = _timing_row(candidate or {}, target)
    direct_row = _timing_row(by.get("direct_send", {}), target) if "direct_send" in by else None
    dram_row = _timing_row(by.get("dram_copy_send", {}), target) if "dram_copy_send" in by else None
    synthetic_row = _timing_row(by.get("synthetic_send", {}), target) if "synthetic_send" in by else None

    probe_capture = capture_probe.get("esp_capture_ms") if isinstance(capture_probe.get("esp_capture_ms"), dict) else {}
    probe_request = capture_probe.get("request_ms") if isinstance(capture_probe.get("request_ms"), dict) else {}
    probe_overhead = capture_probe.get("request_minus_capture_ms") if isinstance(capture_probe.get("request_minus_capture_ms"), dict) else {}
    observed = n(candidate_row.get("observed_interval_ms"))
    candidate_capture = n((candidate_row.get("capture_ms") or {}).get("avg")) or n(probe_capture.get("avg"))
    candidate_send = n((candidate_row.get("send_ms") or {}).get("avg"))
    accounted = candidate_capture + candidate_send
    residual = max(0.0, observed - accounted) if observed > 0 else 0.0
    capture_share = candidate_capture / observed if observed > 0 else 0.0
    send_share = candidate_send / observed if observed > 0 else 0.0
    residual_share = residual / observed if observed > 0 else 0.0

    if capture_share >= 0.40:
        dominant = "camera_capture_wait"
        next_action = "Measure OV2640/framebuffer acquisition more closely and test camera driver buffering/grab behavior before changing network protocol again."
    elif send_share >= 0.40:
        dominant = "tcp_send_backpressure"
        next_action = "Focus on the plain-send socket path, receiver draining and ESP TCP buffering because send time consumes most of the real-frame interval."
    elif residual_share >= 0.35:
        dominant = "unmeasured_camera_or_scheduler_overhead"
        next_action = "Add firmware-level allocation/copy/framebuffer-hold/scheduler timers because capture+send do not explain enough of the observed frame interval."
    else:
        dominant = "mixed_real_camera_pipeline"
        next_action = "Profile camera acquisition and plain-send timing together; no single measured stage dominates the remaining FPS ceiling."

    conclusions: list[str] = []
    candidate_fps = n(candidate_row.get("measured_fps"))
    if candidate_fps and candidate_fps < target * 0.70:
        conclusions.append(f"The recommended transport is reliable but reaches only {candidate_fps:.2f}/{target} FPS, so transport reliability is fixed before throughput is fixed.")
    if direct_row and dram_row and n(direct_row.get("measured_fps")) > 0 and n(dram_row.get("measured_fps")) > 0:
        ratio = n(dram_row.get("measured_fps")) / max(0.01, n(direct_row.get("measured_fps")))
        if ratio >= 0.85:
            conclusions.append("Whole-frame DRAM copy does not create the ~1 FPS ceiling because DRAM-copy and direct plain-send throughput are similar.")
        elif ratio < 0.70:
            conclusions.append("Whole-frame DRAM copy materially reduces throughput and should be timed separately before production use.")
    if synthetic_row:
        synthetic_fps = n(synthetic_row.get("measured_fps")); synthetic_send = n((synthetic_row.get("send_ms") or {}).get("avg"))
        if candidate_fps > 0 and synthetic_fps >= candidate_fps * 1.8 and synthetic_send <= max(20.0, candidate_send * 0.25):
            conclusions.append("Synthetic internal-DRAM data is much faster than real camera JPEGs, so the remaining ceiling is tied to the real camera/framebuffer path rather than generic TCP throughput.")
    if n(probe_request.get("avg")) > 0 and n(probe_capture.get("avg")) >= 0:
        conclusions.append(
            f"HTTP capture requests average {n(probe_request.get('avg')):.1f} ms while ESP camera acquisition reports {n(probe_capture.get('avg')):.1f} ms; the remaining {n(probe_overhead.get('avg')):.1f} ms is outside esp_camera_fb_get()."
        )
    if observed > 0:
        conclusions.append(
            f"For the recommended path, measured capture+send account for about {accounted:.1f} of {observed:.1f} ms per frame; roughly {residual:.1f} ms remains outside those two timers."
        )

    confidence = "high" if i(capture_probe.get("successes")) >= 3 and i(candidate_row.get("sample_count")) >= 2 else "medium"
    return {
        "candidate_key": str(candidate_row.get("key") or recommended or "unknown"),
        "dominant_remaining_stage": dominant,
        "confidence": confidence,
        "target_fps": target,
        "target_period_ms": round(1000.0 / max(1, target), 1),
        "candidate": candidate_row,
        "direct_plain_send": direct_row,
        "dram_copy_send": dram_row,
        "synthetic_send": synthetic_row,
        "capture_probe": capture_probe,
        "accounted_ms": round(accounted, 1),
        "unexplained_ms": round(residual, 1),
        "unexplained_ratio": round(residual_share, 3) if observed > 0 else None,
        "conclusions": conclusions,
        "next_action": next_action,
    }


def benchmark_to_report(raw: dict[str, Any], profile: dict[str, Any], cleanup_ok: bool) -> dict[str, Any]:
    results = [x for x in raw.get("results", []) if isinstance(x, dict)]
    by = {str(x.get("key")): x for x in results if x.get("key")}
    diag = raw.get("diagnosis") if isinstance(raw.get("diagnosis"), dict) else {}
    ev = raw.get("analysis_evidence") if isinstance(raw.get("analysis_evidence"), dict) else {}
    hypotheses = ev.get("hypothesis_ranking") if isinstance(ev.get("hypothesis_ranking"), list) else []
    settings = raw.get("settings") if isinstance(raw.get("settings"), dict) else {}
    initial = raw.get("initial_device") if isinstance(raw.get("initial_device"), dict) else {}
    final = raw.get("final_device") if isinstance(raw.get("final_device"), dict) else {}
    pipeline = raw.get("pipeline_timing_analysis") if isinstance(raw.get("pipeline_timing_analysis"), dict) else None
    target = max(1, i(settings.get("fps"), i(profile.get("target_fps"), 5)))
    source_id = str(profile.get("source_id") or "esp32_cam_01"); host = str(profile.get("host") or "")
    prod = [x for x in results if x.get("production_candidate") is True]
    live_prod = [x for x in prod if i(x.get("requested_frames")) >= 2]
    passed = [x for x in prod if x.get("status") == "PASS"]
    capture_ok = by.get("capture_single", {}).get("status") == "PASS"
    current_ok = by.get("direct_sendmsg_1200", {}).get("status") == "PASS"
    code = str(diag.get("diagnosis_code") or "transport_benchmark_complete")
    bottleneck = str(diag.get("likely_bottleneck") or "Transport benchmark completed.")
    recommended = diag.get("recommended_key"); recommendation = str(diag.get("recommendation") or "Use the ranked transport evidence.")
    overall = "failed" if not capture_ok or not passed else "healthy" if current_ok and code in {"mixed_or_healthy", "healthy_under_isolation_test"} else "warning"
    top_conf = str(hypotheses[0].get("confidence")) if hypotheses and isinstance(hypotheses[0], dict) else "medium"
    confidence = "high" if top_conf in {"high", "medium-high"} else "low" if top_conf == "low" else "medium"

    checks = []
    for x in results:
        key = str(x.get("key") or "transport"); status = "pass" if x.get("status") == "PASS" else "fail" if x.get("status") == "FAIL" else "skip"
        checks.append({"id": f"transport_{key}", "category": "functionality" if key in {"capture_single", "snapshot_polling"} else "bottleneck",
                       "label": str(x.get("name") or key), "status": status, "detail": str(x.get("detail") or ""), "metrics": x})
    if pipeline:
        checks.append({"id":"pipeline_timing","category":"bottleneck","label":"Real-frame timing attribution","status":"pass" if pipeline.get("confidence") == "high" else "warn",
                       "detail":f"Remaining stage: {pipeline.get('dominant_remaining_stage')}; unexplained {pipeline.get('unexplained_ms')} ms/frame.","metrics":pipeline})
    checks += [
        {"id": "pc_studio_managed_production", "category": "functionality", "label": "Normal PC Studio stream worker", "status": "skip",
         "detail": "R5 benchmark firmware isolates transport paths. Verify the managed worker after the selected fix is moved back into normal AiTL firmware.", "metrics": {}},
        {"id": "benchmark_cleanup", "category": "functionality", "label": "Stop/reset benchmark transport state", "status": "pass" if cleanup_ok else "warn",
         "detail": "Benchmark transports stopped/reset." if cleanup_ok else "Benchmark finished but automatic transport cleanup needs attention.", "metrics": {}},
    ]
    fchecks = [x for x in checks if x["category"] == "functionality" and x["status"] != "skip"]
    fpass = sum(1 for x in fchecks if x["status"] == "pass"); fscore = round(100 * fpass / len(fchecks)) if fchecks else 0

    matrix_keys = ["capture_single", "snapshot_polling", "mjpeg", "direct_sendmsg_1200", "direct_sendmsg_5000", "direct_send", "staged_send",
                   "dram_copy_sendmsg", "dram_copy_send", "synthetic_sendmsg", "synthetic_send", "udp"]
    matrix = {k: by[k].get("status") == "PASS" for k in matrix_keys if k in by}
    cfind = []; bfind = []
    for idx, h in enumerate(hypotheses):
        if not isinstance(h, dict): continue
        evidence = "; ".join(str(v) for v in h.get("evidence", []) if v) or bottleneck
        title = str(h.get("hypothesis") or "Transport hypothesis")
        cfind.append({"code": re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_"), "layer": "transport", "confidence": str(h.get("confidence") or "medium"), "evidence": evidence, "action": recommendation})
        bfind.append({"id": f"transport_{idx+1}", "layer": "transport", "severity": "critical" if idx == 0 and overall == "failed" else "warning",
                      "title": title, "evidence": evidence, "impact": bottleneck, "recommendation": recommendation})

    ladder = []
    if recommended:
        if str(recommended) in by: ladder.append(phase(by[str(recommended)], target))
        for fps in (10, 15):
            if f"{recommended}_{fps}" in by: ladder.append(phase(by[f"{recommended}_{fps}"], fps))
    stable_item = by.get(str(recommended)) if recommended else None
    if not stable_item: stable_item = next((x for x in passed if i(x.get("requested_frames")) >= 2), passed[0] if passed else {})
    stable_phase = phase(stable_item or {}, target); completion = n((stable_item or {}).get("completion_ratio")); speed_ratio = min(1.0, max(0.0, stable_phase["fps_ratio"]))
    stable_score = round(max(0.0, min(100.0, 100.0 * (0.70 * completion + 0.30 * speed_ratio))))
    stable_grade = "stable" if completion >= 1 and speed_ratio >= .7 else "degraded" if completion >= .75 and speed_ratio >= .25 else "unstable"
    peak_fps = max((n(x.get("measured_fps")) for x in live_prod), default=0.0)
    peak_mbps = max((i(x.get("bytes_received")) * 8.0 / max(1.0, n(x.get("elapsed_ms"))) / 1000.0 for x in live_prod), default=0.0)
    sustainable = max((p["target_fps"] for p in ladder if p["fps_ratio"] >= .7 and p["disconnects"] == 0), default=0)
    rssis = [v for v in (i(initial.get("rssi"), -127), i(final.get("rssi"), -127)) if v > -127]
    context = raw.get("run_context") if isinstance(raw.get("run_context"), dict) else {}
    duration = i(context.get("duration_ms")); started = i(context.get("started_at_ms"), int(time.time()*1000)-duration)
    direct1200 = by.get("direct_sendmsg_1200", {}); direct5000 = by.get("direct_sendmsg_5000", {})

    causes = [str(h.get("hypothesis")) for h in hypotheses if isinstance(h, dict) and h.get("hypothesis")] or [bottleneck]
    recommendations = [recommendation]
    if pipeline:
        stage = str(pipeline.get("dominant_remaining_stage") or "")
        if stage and stage not in causes:
            causes.append(stage)
        timing_action = str(pipeline.get("next_action") or "")
        if timing_action:
            recommendations.append(timing_action)
    recommendations.append("After implementing the selected transport fix, flash normal AiTL camera firmware and rerun this page to verify the managed PC Studio receive path.")

    return {
        "run_id": f"camdiag-{uuid4().hex[:10]}", "started_at_ms": started, "duration_ms": duration, "source_id": source_id, "host": host,
        "overall": overall, "diagnosis_code": code, "title": f"Transport benchmark: {code.replace('_',' ')}", "summary": bottleneck, "confidence": confidence,
        "likely_causes": causes, "recommendations": recommendations,
        "checks": checks,
        "metrics": {"control_successes": 1, "control_failures": 0, "control_avg_ms": None, "control_p50_ms": None, "control_p95_ms": None, "control_max_ms": None, "control_jitter_ms": None,
                    "rssi_avg": round(sum(rssis)/len(rssis),1) if rssis else None, "rssi_min": min(rssis) if rssis else None, "rssi_max": max(rssis) if rssis else None,
                    "wifi_bssid": final.get("bssid") or initial.get("bssid"), "wifi_channel": final.get("channel") or initial.get("channel"),
                    "direct_clean_frames": i(direct1200.get("frames")), "direct_clean_fps": n(direct1200.get("measured_fps")), "direct_clean_disconnects": 0 if direct1200.get("status") == "PASS" else 1, "direct_clean_bad_frames": 0,
                    "direct_polled_frames": i(direct5000.get("frames")), "direct_polled_fps": n(direct5000.get("measured_fps")), "direct_polled_disconnects": 0 if direct5000.get("status") == "PASS" else 1, "direct_polled_bad_frames": 0,
                    "status_poll_failures": i(direct5000.get("status_poll_failures")), "managed_frames": 0, "managed_fps": 0.0, "managed_failed_fetches": 0, "managed_reconnects": 0, "managed_session_recoveries": 0,
                    "device_send_failures_delta": i(final.get("send_failures")), "device_deadline_drops_delta": i(final.get("deadline_drops")), "phase_boundary_send_resets": 0,
                    "last_send_errno": final.get("last_errno"), "last_send_accepted_bytes": final.get("last_accepted_bytes"), "last_frame_bytes": final.get("last_frame_bytes"), "send_ewma_ms": None,
                    "wifi_disconnects": None, "wifi_reconnects": None, "functionality_score": fscore, "stability_score": stable_score, "stability_grade": stable_grade,
                    "peak_measured_fps": round(peak_fps,2), "peak_throughput_mbps": round(peak_mbps,3), "estimated_sustainable_target_fps": sustainable,
                    "stability_target_fps": target, "stability_measured_fps": stable_phase["measured_fps"], "stability_interval_p95_ms": None, "stability_interval_max_ms": None,
                    "stability_jitter_ms": None, "stability_stall_intervals": 0, "stability_disconnects": stable_phase["disconnects"], "stability_sequence_gaps": stable_phase["sequence_gaps"], "stability_bad_frames": 0},
        "functionality": {"score": fscore, "passed": fpass, "total": len(fchecks), "config_roundtrip": True, "session_lifecycle": True},
        "stability": {"grade": stable_grade, "score": stable_score, "phase": stable_phase},
        "bottleneck_analysis": {"primary_bottleneck": code, "findings": bfind, "estimated_sustainable_target_fps": sustainable, "peak_measured_fps": round(peak_fps,2), "peak_throughput_mbps": round(peak_mbps,3), "stability_grade": stable_grade, "stability_score": stable_score, "saved_target_fps": i(profile.get("target_fps"), target)},
        "candidate_isolation": {"supported": True, "primary_candidate": str(recommended or code), "findings": cfind, "ruled_out": [], "matrix": matrix},
        "candidate_phases": {k: by[k] for k in matrix_keys if k in by}, "load_ladder": ladder, "contention_phase": phase(direct5000, target),
        "managed_phase": {"target_fps": i(profile.get("target_fps"), target), "duration_seconds": 0, "frames": 0, "failed_fetches": 0, "reconnects": 0, "session_recoveries": 0, "measured_fps": 0.0, "throughput_mbps": 0.0, "fps_ratio": 0.0, "error": "Not applicable while R5 transport firmware is flashed."},
        "device": {"protocol": "aitl-r5-transport-benchmark", "stream_protocol": "ATL1/MJPEG/UDP benchmark", "firmware_revision": raw.get("firmware"), "camera_ready": final.get("camera_ready", initial.get("camera_ready")), "rssi": final.get("rssi", initial.get("rssi")), "wifi_bssid": final.get("bssid", initial.get("bssid")), "wifi_channel": final.get("channel", initial.get("channel"))},
        "state_restored": cleanup_ok, "restore_error": None if cleanup_ok else "Benchmark transport state could not be reset automatically.", "diagnostic_target_fps": target, "diagnostic_load_targets": [target,10,15], "prototype_only": True,
        "pipeline_timing": pipeline,
        "transport_benchmark": raw,
    }


class CameraDiagnosticDispatchService:
    def __init__(self) -> None:
        self._lock = Lock(); self._state = self._idle()

    @staticmethod
    def _idle() -> dict[str, Any]:
        return {"status":"idle","engine":None,"stage":"Idle","current_test":None,"test_index":None,"frame_current":None,"frame_total":None,"detail":None,"last_line":None,"started_at_ms":None,"elapsed_ms":0,"error":None,"log_tail":[]}

    def _set(self, **changes: Any) -> None:
        with self._lock:
            state = dict(self._state); logs = list(state.get("log_tail") or []); line = changes.pop("log_line", None)
            if line: logs = (logs + [str(line)])[-80:]
            state.update(changes); state["log_tail"] = logs
            if state.get("started_at_ms"): state["elapsed_ms"] = max(0, int(time.time()*1000)-i(state["started_at_ms"]))
            self._state = state

    def progress(self) -> dict[str, Any]:
        with self._lock: state = deepcopy(self._state)
        if state.get("started_at_ms") and state.get("status") == "running": state["elapsed_ms"] = max(0,int(time.time()*1000)-i(state["started_at_ms"]))
        return state

    @staticmethod
    def _profile() -> dict[str, Any] | None:
        status = remote_camera_manager.status(refresh_device=False); sid = status.get("active_source_id"); cameras = status.get("cameras") if isinstance(status.get("cameras"), list) else []
        item = next((x for x in cameras if isinstance(x,dict) and x.get("source_id") == sid), None)
        return dict(item) if item else None

    @staticmethod
    def _http(host: str, path: str, method: str = "GET", query: dict[str,str] | None = None) -> tuple[int, dict[str,Any]]:
        target = path + (("?"+urlencode(query)) if query else ""); conn = http.client.HTTPConnection(host,80,timeout=2.5)
        try:
            conn.request(method,target,body=b"" if method != "GET" else None,headers={"Connection":"close","Accept":"application/json"}); r=conn.getresponse(); payload=r.read(65536)
            try: parsed=json.loads(payload.decode("utf-8"))
            except Exception: parsed={}
            return r.status, parsed if isinstance(parsed,dict) else {}
        except Exception: return 0, {}
        finally: conn.close()

    def _capture_timing_probe(self, host: str, attempts: int = 4) -> dict[str, Any]:
        records: list[dict[str, Any]] = []
        request_values: list[float] = []; capture_values: list[float] = []; overhead_values: list[float] = []
        errors: list[str] = []
        for index in range(1, attempts + 1):
            self._set(stage="TARGETED REAL-FRAME TIMING", current_test="HTTP capture vs ESP camera acquisition", frame_current=index-1, frame_total=attempts, detail=f"Capture timing sample {index}/{attempts}")
            started = time.perf_counter(); conn = http.client.HTTPConnection(host, 80, timeout=8.0)
            try:
                conn.request("GET", "/capture", headers={"Connection":"close", "User-Agent":"AiTL-PC-Studio-Pipeline-Timing"})
                response = conn.getresponse(); payload = response.read(512 * 1024)
                request_ms = (time.perf_counter() - started) * 1000.0
                _, status = self._http(host, "/status")
                capture_ms = n(status.get("last_capture_ms"), 0.0)
                overhead_ms = max(0.0, request_ms - capture_ms)
                valid = response.status == 200 and len(payload) >= 4 and payload.startswith(b"\xff\xd8") and payload.endswith(b"\xff\xd9")
                records.append({"index":index,"ok":valid,"http_status":response.status,"bytes":len(payload),"request_ms":round(request_ms,1),"esp_capture_ms":round(capture_ms,1),"request_minus_capture_ms":round(overhead_ms,1),"rssi":status.get("rssi"),"internal_free":status.get("internal_free")})
                if valid:
                    request_values.append(request_ms); capture_values.append(capture_ms); overhead_values.append(overhead_ms)
                else:
                    errors.append(f"sample {index}: HTTP {response.status} or invalid JPEG")
            except Exception as exc:
                errors.append(f"sample {index}: {type(exc).__name__}: {exc}")
            finally:
                conn.close()
            self._set(frame_current=index, frame_total=attempts, detail=records[-1].__str__() if records and records[-1].get("index") == index else errors[-1] if errors else f"sample {index} complete")
            time.sleep(0.08)
        return {"attempts":attempts,"successes":len(request_values),"failures":attempts-len(request_values),"request_ms":stats(request_values),"esp_capture_ms":stats(capture_values),"request_minus_capture_ms":stats(overhead_values),"records":records,"errors":errors[:8]}

    def _parse(self, line: str) -> None:
        text=line.rstrip()
        if not text: return
        m=SECTION_RE.match(text)
        if m: self._set(stage=m.group(1),detail=None,last_line=text,log_line=text); return
        m=START_RE.match(text)
        if m: self._set(test_index=i(m.group(1)),current_test=m.group(2).strip(),detail=(m.group(3) or "").strip() or None,frame_current=None,frame_total=None,last_line=text,log_line=text); return
        m=FRAME_RE.match(text)
        if m: self._set(frame_current=i(m.group(1)),frame_total=i(m.group(2)),detail=m.group(3).strip(),last_line=text,log_line=text); return
        m=FINISH_RE.match(text)
        if m: self._set(frame_current=i(m.group(2)),frame_total=i(m.group(3)),detail=f"{m.group(1)} | {m.group(4).strip()}",last_line=text,log_line=text); return
        self._set(last_line=text,log_line=text)

    def _benchmark(self, profile: dict[str, Any]) -> dict[str, Any]:
        host=str(profile.get("host") or ""); settings=profile.get("settings") if isinstance(profile.get("settings"),dict) else {}; frame=str(settings.get("frame_size") or "QVGA").upper()
        if frame not in {"QQVGA","HQVGA","QVGA","CIF","VGA"}: frame="VGA"
        quality=max(4,min(63,i(settings.get("jpeg_quality"),24))); fps=max(1,min(15,i(profile.get("target_fps"),5)))
        root=Path(__file__).resolve().parents[5]; script=root/"scripts"/BENCHMARK_SCRIPT
        if not script.is_file(): raise AppError(ErrorCode.INVALID_REQUEST,f"Camera benchmark script is missing: {script}",status_code=500)
        self._set(engine="transport_benchmark",stage="Preparing full transport benchmark",current_test="R5 firmware detected",detail=f"{frame} / JPEG q={quality} / primary {fps} FPS")
        with tempfile.TemporaryDirectory(prefix="aitl-camera-diagnostic-") as td:
            output=Path(td)/"camera_transport_benchmark.json"; cmd=[sys.executable,str(script),"--host",host,"--frames","8","--fps",str(fps),"--frame-size",frame,"--jpeg-quality",str(quality),"--output",str(output),"--environment-label","pc-studio-camera-diagnostics","--chunk-sweep"]
            p=subprocess.Popen(cmd,cwd=str(root),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding="utf-8",errors="replace",bufsize=1)
            assert p.stdout is not None
            for line in p.stdout: self._parse(line)
            code=p.wait()
            if not output.is_file(): raise RuntimeError(f"Transport benchmark exited with code {code} before producing its JSON report.")
            raw=json.loads(output.read_text(encoding="utf-8")); cleanup=True
            for path,query in [("/udp/stop",None),("/stop",None),("/mode",{"mode":"direct_sendmsg","stall_ms":"1200","total_ms":"2000"})]: cleanup = (200 <= self._http(host,path,"POST",query)[0] < 300) and cleanup
            followup_started = time.perf_counter()
            capture_probe = self._capture_timing_probe(host)
            raw["pipeline_timing_analysis"] = build_pipeline_timing_analysis(raw, capture_probe)
            raw["pipeline_timing_analysis"]["followup_duration_ms"] = round((time.perf_counter() - followup_started) * 1000.0, 1)
            report=benchmark_to_report(raw,profile,cleanup)
            report["duration_ms"] += i(raw["pipeline_timing_analysis"].get("followup_duration_ms"))
            if code not in (0,2): report["overall"]="failed"; report["summary"]=f"Benchmark process exited with code {code}. {report['summary']}"
            return report

    def run(self) -> dict[str, Any]:
        self._state=self._idle(); self._set(status="running",engine="probing",stage="Preflight",current_test="Detecting selected ESP diagnostic capability",started_at_ms=int(time.time()*1000),error=None)
        try:
            profile=self._profile()
            if profile:
                _,device=self._http(str(profile.get("host") or ""),"/status"); firmware=str(device.get("firmware") or "")
            else: firmware=""
            if profile and firmware.startswith(BENCHMARK_PREFIX): report=self._benchmark(profile)
            else:
                self._set(engine="standard",stage="Production diagnostics",current_test="Running control, stream, stability and managed-worker diagnostics",detail="Normal AiTL firmware path")
                report=camera_diagnostic_service.run()
            self._set(status="completed",stage="Complete",current_test="Diagnosis ready",frame_current=None,frame_total=None,detail=str(report.get("summary") or "Camera diagnostics completed.")); return report
        except Exception as exc:
            self._set(status="failed",stage="Failed",current_test=None,detail=f"{type(exc).__name__}: {exc}",error=f"{type(exc).__name__}: {exc}"); raise


camera_diagnostic_dispatch_service = CameraDiagnosticDispatchService()
__all__ = ["BENCHMARK_PREFIX","CameraDiagnosticDispatchService","benchmark_to_report","build_pipeline_timing_analysis","camera_diagnostic_dispatch_service"]
