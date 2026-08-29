from __future__ import annotations

import math
import statistics
from typing import Any

EXPECTED_CONTROL_PROBES = 8


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * max(0.0, min(1.0, fraction))
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def phase_clean(phase: dict[str, Any]) -> bool:
    return (
        safe_int(phase.get("frames")) > 0
        and safe_int(phase.get("disconnects")) == 0
        and safe_int(phase.get("bad_frames")) == 0
        and safe_int(phase.get("unexpected_send_failures")) == 0
        and safe_int(phase.get("deadline_drops")) == 0
    )


def phase_ratio(phase: dict[str, Any]) -> float:
    return safe_float(phase.get("measured_fps")) / max(1, safe_int(phase.get("target_fps"), 1))


def analyze_camera_bottlenecks(
    *,
    control_successes: int,
    control_failures: int,
    control_p95_ms: float | None,
    control_jitter_ms: float | None,
    rssi_min: int | None,
    rssi_max: int | None,
    load_phases: list[dict[str, Any]],
    contention_phase: dict[str, Any],
    contention_reference: dict[str, Any] | None,
    stability_phase: dict[str, Any],
    managed_phase: dict[str, Any],
    saved_target_fps: int,
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []

    def add(fid: str, layer: str, severity: str, title: str, evidence: str, impact: str, recommendation: str) -> None:
        findings.append({
            "id": fid,
            "layer": layer,
            "severity": severity,
            "title": title,
            "evidence": evidence,
            "impact": impact,
            "recommendation": recommendation,
        })

    if control_failures:
        add(
            "control_failures", "control", "critical" if control_successes == 0 else "warning",
            "ESP HTTP control is intermittent",
            f"{control_successes}/{control_successes + control_failures} control probes succeeded.",
            "Connect/config/start/stop may fail even when image transport works.",
            "Treat HTTP control responsiveness separately from the JPEG data path.",
        )
    elif control_p95_ms is not None and control_p95_ms >= 600:
        add(
            "control_latency", "control", "warning", "ESP HTTP control latency is high",
            f"Control p95 latency was {control_p95_ms:.0f} ms.",
            "Button actions and automatic recovery can become slow or time out.",
            "Keep status polling low-rate and inspect ESP loop/control-server responsiveness.",
        )
    elif control_jitter_ms is not None and control_jitter_ms >= 150:
        add(
            "control_jitter", "control", "warning", "ESP HTTP control latency is inconsistent",
            f"Control latency standard deviation was {control_jitter_ms:.0f} ms.",
            "Latency spikes can create occasional 502 responses.",
            "Inspect control-loop scheduling and local Wi-Fi latency variation.",
        )

    if rssi_min is not None:
        span = (rssi_max - rssi_min) if rssi_max is not None else 0
        if rssi_min <= -75:
            add(
                "weak_wifi", "wifi", "critical", "Wi-Fi margin is weak",
                f"RSSI reached {rssi_min} dBm.",
                "TCP acknowledgements and HTTP control are more likely to stall.",
                "Improve antenna/AP placement and verify the intended nearby BSSID.",
            )
        elif rssi_min <= -68 or span >= 12:
            add(
                "variable_wifi", "wifi", "warning", "Wi-Fi margin or variation is marginal",
                f"RSSI range was {rssi_min}..{rssi_max} dBm (span {span} dB).",
                "An idle-stable link may lose throughput margin under camera load.",
                "Repeat the test in the camera's final physical position and verify BSSID.",
            )

    all_direct = [*load_phases, contention_phase, stability_phase]
    send_failures = sum(safe_int(p.get("unexpected_send_failures")) for p in all_direct)
    deadlines = sum(safe_int(p.get("deadline_drops")) for p in all_direct)
    if send_failures or deadlines:
        add(
            "sender_failures", "esp_tcp_sender", "critical", "ESP TCP sender failed during active measurement",
            f"Unexpected send failures={send_failures}, deadline drops={deadlines}.",
            "The stream can disconnect independently of the browser/frontend.",
            "Focus on ESP/lwIP send progress and TCP acknowledgement/backpressure behavior.",
        )

    completed = [p for p in load_phases if safe_int(p.get("frames")) > 0]
    peak_throughput = max((safe_float(p.get("throughput_mbps")) for p in completed), default=0.0)
    peak_measured = max((safe_float(p.get("measured_fps")) for p in completed), default=0.0)
    sustainable_targets = [
        safe_int(p.get("target_fps"))
        for p in completed
        if phase_clean(p) and phase_ratio(p) >= 0.80
    ]
    sustainable_target = max(sustainable_targets, default=0)
    highest = max(completed, key=lambda p: safe_int(p.get("target_fps")), default=None)
    if highest is not None and phase_clean(highest) and phase_ratio(highest) < 0.80:
        add(
            "payload_capacity", "throughput", "warning", "Current JPEG payload reaches an FPS/throughput ceiling",
            f"Target {safe_int(highest.get('target_fps'))} FPS measured {safe_float(highest.get('measured_fps')):.2f} FPS ({phase_ratio(highest)*100:.0f}% of target).",
            "Requesting more FPS will not proportionally produce more fresh frames.",
            "Use the measured sustainable FPS before reducing image quality/resolution.",
        )

    stable_ratio = phase_ratio(stability_phase) if safe_int(stability_phase.get("frames")) else 0.0
    if not phase_clean(stability_phase) or stable_ratio < 0.50:
        grade = "unstable"
    elif stable_ratio < 0.75 or safe_int(stability_phase.get("stall_intervals")) > 0:
        grade = "degraded"
    else:
        grade = "stable"

    if grade == "unstable":
        add(
            "sustained_instability", "stability", "critical", "Sustained stream stability failed",
            f"disconnects={safe_int(stability_phase.get('disconnects'))}, invalid JPEGs={safe_int(stability_phase.get('bad_frames'))}, achieved={stable_ratio*100:.0f}% of target.",
            "Continuous camera operation is not reliable at the saved target.",
            "Use the phase timing/send evidence to fix the failing layer before increasing load.",
        )
    elif grade == "degraded":
        add(
            "sustained_jitter", "stability", "warning", "Sustained stream timing is degraded",
            f"Achieved {stable_ratio*100:.0f}% of target; p95 interval={safe_float(stability_phase.get('interval_p95_ms')):.0f} ms; long stalls={safe_int(stability_phase.get('stall_intervals'))}.",
            "The preview can remain connected but feel uneven or stale.",
            "Use the measured sustainable FPS instead of demanding more frames than the path can deliver consistently.",
        )

    if contention_reference is not None and safe_int(contention_phase.get("frames")) > 0:
        reference_fps = max(0.01, safe_float(contention_reference.get("measured_fps")))
        polled_fps = safe_float(contention_phase.get("measured_fps"))
        ratio = polled_fps / reference_fps
        if safe_int(contention_phase.get("status_poll_failures")) or safe_int(contention_phase.get("disconnects")) or ratio < 0.75:
            add(
                "control_stream_contention", "control_vs_stream",
                "critical" if safe_int(contention_phase.get("disconnects")) else "warning",
                "HTTP status traffic competes with image streaming",
                f"Same-load FPS changed {reference_fps:.2f}→{polled_fps:.2f}; status failures={safe_int(contention_phase.get('status_poll_failures'))}.",
                "Frequent status work can reduce image throughput or cause reconnects.",
                "Keep ESP status polling serial and low-rate while streaming.",
            )

    managed_fps = safe_float(managed_phase.get("measured_fps"))
    stability_fps = safe_float(stability_phase.get("measured_fps"))
    if safe_int(managed_phase.get("failed_fetches")) or safe_int(managed_phase.get("reconnects")):
        add(
            "managed_worker_errors", "pc_studio", "critical" if phase_clean(stability_phase) else "warning",
            "PC Studio managed stream worker recorded transport failures",
            f"failures={safe_int(managed_phase.get('failed_fetches'))}, reconnects={safe_int(managed_phase.get('reconnects'))}.",
            "The normal app receive path may be less stable than the direct ESP path.",
            "Inspect RemoteCameraService receive/reconnect state if direct phases remain clean.",
        )
    elif stability_fps > 0 and managed_fps < stability_fps * 0.70:
        add(
            "managed_worker_throughput", "pc_studio", "warning", "PC Studio managed receive path is slower than direct receiving",
            f"Direct sustained={stability_fps:.2f} FPS, managed={managed_fps:.2f} FPS.",
            "Backend receive/session overhead is reducing usable frame rate.",
            "Profile the managed receive path before changing ESP image quality.",
        )

    period_ms = 1000.0 / max(1, safe_int(stability_phase.get("target_fps"), saved_target_fps))
    send_ewma = safe_float(stability_phase.get("device_send_ewma_ms"))
    capture_ms = safe_float(stability_phase.get("device_last_capture_ms"))
    if send_ewma > period_ms * 0.80:
        add(
            "send_time_pressure", "esp_tcp_sender", "warning", "ESP send time consumes most of the frame budget",
            f"Send EWMA={send_ewma:.0f} ms versus frame period={period_ms:.0f} ms.",
            "Small network delays can push achieved FPS below target.",
            "Lower target FPS before sacrificing JPEG quality; investigate ACK/backpressure latency when RSSI is strong.",
        )
    if capture_ms > max(20.0, period_ms * 0.60):
        add(
            "capture_time_pressure", "camera_capture", "warning", "Camera capture time consumes a large part of the frame budget",
            f"Last capture={capture_ms:.0f} ms versus frame period={period_ms:.0f} ms.",
            "Sensor/capture timing may cap FPS before TCP throughput is reached.",
            "Only reduce frame size if higher FPS is actually required.",
        )

    rank = {"critical": 0, "warning": 1, "info": 2}
    findings.sort(key=lambda item: (rank.get(str(item.get("severity")), 9), str(item.get("id"))))

    score = 100
    score -= min(50, 25 * safe_int(stability_phase.get("disconnects")))
    score -= min(20, 4 * safe_int(stability_phase.get("sequence_gaps")))
    score -= min(20, 10 * safe_int(stability_phase.get("bad_frames")))
    score -= min(20, 10 * safe_int(stability_phase.get("unexpected_send_failures")))
    if stable_ratio < 0.75:
        score -= min(25, round((0.75 - stable_ratio) * 50))
    score = max(0, min(100, score))

    return {
        "primary_bottleneck": findings[0]["id"] if findings else "none_detected",
        "findings": findings,
        "estimated_sustainable_target_fps": sustainable_target,
        "peak_measured_fps": round(peak_measured, 2),
        "peak_throughput_mbps": round(peak_throughput, 3),
        "stability_grade": grade,
        "stability_score": score,
        "saved_target_fps": saved_target_fps,
    }


def classify_camera_diagnostic(
    *,
    control_successes: int,
    protocol_ok: bool,
    camera_ready: bool,
    clean_frames: int,
    clean_disconnects: int,
    clean_bad_frames: int,
    polled_frames: int,
    polled_disconnects: int,
    polled_bad_frames: int,
    status_poll_failures: int,
    managed_frames: int,
    managed_failed_fetches: int,
    send_failures_delta: int,
    deadline_drops_delta: int,
    rssi_min: int | None,
    stability_grade: str = "stable",
    saved_target_fps: int = 5,
    estimated_sustainable_fps: float | None = None,
    phase_boundary_send_resets: int = 0,
) -> dict[str, Any]:
    clean_good = clean_frames >= 8 and clean_disconnects == 0 and clean_bad_frames == 0
    polled_good = polled_frames >= 8 and polled_disconnects == 0 and polled_bad_frames == 0
    managed_good = managed_frames >= 6 and managed_failed_fetches == 0

    def result(overall: str, code: str, title: str, summary: str, confidence: str, causes: list[str], recs: list[str]) -> dict[str, Any]:
        return {"overall": overall, "diagnosis_code": code, "title": title, "summary": summary, "confidence": confidence, "likely_causes": causes, "recommendations": recs}

    if control_successes == 0:
        return result("failed", "control_unreachable", "ESP control endpoint is unreachable", "No valid /status response was obtained.", "high", ["Wrong/changing IP, unreachable LAN path, or unresponsive ESP HTTP server"], ["Confirm the Serial Monitor IP and local network reachability."])
    if not protocol_ok:
        return result("failed", "firmware_incompatible", "Camera firmware protocol is incompatible", "The ESP responded but does not expose the accepted AiTL camera/TCP protocol.", "high", ["Older or mismatched firmware"], ["Flash the current compatible ESP firmware."])
    if not camera_ready:
        return result("failed", "camera_not_ready", "ESP camera sensor is not ready", "Control works but camera_ready is false.", "high", ["Camera ribbon/module or sensor initialization failure"], ["Power-cycle, reseat the ribbon, and inspect Serial Monitor camera-init errors."])
    if not clean_good and (send_failures_delta or deadline_drops_delta):
        return result("failed", "esp_camera_tcp_send_stall", "ESP camera-to-TCP sender is stalling", "The direct receiver failed and active-phase ESP send/deadline counters increased.", "high", ["ESP/lwIP backpressure or camera/network scheduling"], ["Use active-phase send/accepted-byte timing before changing frontend code."])
    if not clean_good:
        return result("failed", "direct_camera_stream_failure", "Direct camera stream is unstable", "Direct ATL1/JPEG receiving failed with the normal PC Studio worker bypassed.", "high", ["ESP stream sender, Wi-Fi/TCP path, or camera/network interaction"], ["Use direct phase timing and transport errors to isolate the sender/network path."])
    if clean_good and not polled_good and (status_poll_failures or polled_disconnects > clean_disconnects):
        return result("failed", "control_stream_contention", "HTTP control traffic disrupts camera streaming", "The same direct stream becomes unstable when /status polling is added.", "high", ["ESP control handling competes with TCP image sending"], ["Keep status polling serial and low-rate."])
    if clean_good and polled_good and not managed_good:
        return result("failed", "pc_studio_stream_integration", "Direct stream works, but PC Studio's managed stream path fails", "Direct receiving passes while the normal managed worker fails.", "high", ["RemoteCameraService/manager receive or reconnect state"], ["Focus the next repair on the PC managed receive path."])
    if stability_grade == "unstable":
        return result("failed", "stream_stability_failure", "Camera functions, but sustained streaming is unstable", "Short checks passed but the longer saved-target phase was unstable.", "high", ["Intermittent sender/network stalls"], ["Use the stability and bottleneck evidence to identify the limiting layer."])
    if control_successes < EXPECTED_CONTROL_PROBES or status_poll_failures:
        return result("warning", "control_plane_instability", "Image transport works, but ESP control requests are intermittent", "One or more control/status probes failed during the run.", "medium", ["Intermittent ESP HTTP responsiveness or latency spikes"], ["Keep image transport unchanged and focus on low-rate control reliability."])
    if rssi_min is not None and rssi_min <= -75:
        return result("warning", "wifi_margin_low", "Camera works, but Wi-Fi margin is weak", "Transport passed while RSSI entered a weak range.", "medium", ["Weak/variable 2.4 GHz AP association"], ["Improve antenna/AP placement or verify BSSID."])
    if stability_grade == "degraded":
        return result("warning", "stream_stability_degraded", "Camera path works, but frame timing is degraded", "The sustained test remained functional but FPS/jitter margin is below the preferred threshold.", "medium", ["Current payload/FPS demand is close to practical capacity"], ["Use the measured sustainable FPS before reducing image quality."])
    if estimated_sustainable_fps is not None and saved_target_fps > estimated_sustainable_fps * 1.20:
        return result("warning", "throughput_capacity_limited", "Camera works, but saved FPS exceeds measured capacity", f"Peak measured camera rate was about {estimated_sustainable_fps:.1f} FPS versus saved target {saved_target_fps} FPS.", "medium", ["Current JPEG payload and transport timing limit fresh-frame rate"], ["Set FPS near the measured sustainable level before reducing quality/resolution."])
    note = f" {phase_boundary_send_resets} diagnostic phase-boundary reset(s) were excluded from failure classification." if phase_boundary_send_resets else ""
    return result("healthy", "healthy_now", "Camera path is healthy in this diagnostic run", "Control, functionality, direct transport, sustained stability, status-poll coexistence and managed streaming passed." + note, "medium", [], ["Repeat the test while an intermittent failure is visible if needed."])
