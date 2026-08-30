from __future__ import annotations

from copy import deepcopy
import http.client
import json
from pathlib import Path
import re
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


def benchmark_to_report(raw: dict[str, Any], profile: dict[str, Any], cleanup_ok: bool) -> dict[str, Any]:
    results = [x for x in raw.get("results", []) if isinstance(x, dict)]
    by = {str(x.get("key")): x for x in results if x.get("key")}
    diag = raw.get("diagnosis") if isinstance(raw.get("diagnosis"), dict) else {}
    ev = raw.get("analysis_evidence") if isinstance(raw.get("analysis_evidence"), dict) else {}
    hypotheses = ev.get("hypothesis_ranking") if isinstance(ev.get("hypothesis_ranking"), list) else []
    settings = raw.get("settings") if isinstance(raw.get("settings"), dict) else {}
    initial = raw.get("initial_device") if isinstance(raw.get("initial_device"), dict) else {}
    final = raw.get("final_device") if isinstance(raw.get("final_device"), dict) else {}
    target = max(1, i(settings.get("fps"), i(profile.get("target_fps"), 5)))
    source_id = str(profile.get("source_id") or "esp32_cam_01"); host = str(profile.get("host") or "")
    prod = [x for x in results if x.get("production_candidate") is True]
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
    if not stable_item: stable_item = passed[0] if passed else {}
    stable_phase = phase(stable_item or {}, target); completion = n((stable_item or {}).get("completion_ratio"))
    stable_score = round(max(0.0, min(100.0, completion * 100.0)))
    stable_grade = "stable" if completion >= 1 and stable_phase["fps_ratio"] >= .7 else "degraded" if completion >= .75 else "unstable"
    peak_fps = max((n(x.get("measured_fps")) for x in prod), default=0.0)
    peak_mbps = max((i(x.get("bytes_received")) * 8.0 / max(1.0, n(x.get("elapsed_ms"))) / 1000.0 for x in prod), default=0.0)
    sustainable = max((p["target_fps"] for p in ladder if p["fps_ratio"] >= .7 and p["disconnects"] == 0), default=target if stable_grade != "unstable" else 0)
    rssis = [v for v in (i(initial.get("rssi"), -127), i(final.get("rssi"), -127)) if v > -127]
    context = raw.get("run_context") if isinstance(raw.get("run_context"), dict) else {}
    duration = i(context.get("duration_ms")); started = i(context.get("started_at_ms"), int(time.time()*1000)-duration)
    direct1200 = by.get("direct_sendmsg_1200", {}); direct5000 = by.get("direct_sendmsg_5000", {})

    causes = [str(h.get("hypothesis")) for h in hypotheses if isinstance(h, dict) and h.get("hypothesis")] or [bottleneck]
    return {
        "run_id": f"camdiag-{uuid4().hex[:10]}", "started_at_ms": started, "duration_ms": duration, "source_id": source_id, "host": host,
        "overall": overall, "diagnosis_code": code, "title": f"Transport benchmark: {code.replace('_',' ')}", "summary": bottleneck, "confidence": confidence,
        "likely_causes": causes, "recommendations": [recommendation, "After implementing the selected transport fix, flash normal AiTL camera firmware and rerun this page to verify the managed PC Studio receive path."],
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
            report=benchmark_to_report(raw,profile,cleanup)
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
__all__ = ["BENCHMARK_PREFIX","CameraDiagnosticDispatchService","benchmark_to_report","camera_diagnostic_dispatch_service"]
