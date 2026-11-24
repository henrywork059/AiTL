"""Read-only, per-camera endurance sampling of PC Studio's existing status API.

No stream control, camera decoding, extra transport connection or firmware changes.
Actual runs must be identified as measured; fixture tests must say synthetic.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import json
import re
import subprocess
from pathlib import Path
import platform
import sys
import time
from typing import Any, Callable
from urllib.request import Request, urlopen

SCHEMA_VERSION = 1
CAMERA_SETTINGS_KEYS = frozenset({
    "frame_size", "jpeg_quality", "brightness", "contrast", "saturation", "special_effect",
    "awb", "awb_gain", "wb_mode", "aec", "aec2", "ae_level", "aec_value",
    "agc", "agc_gain", "gainceiling", "bpc", "wpc", "raw_gma", "lenc",
    "hmirror", "vflip", "dcw", "colorbar",
})


def _project_settings(value: Any) -> dict[str, Any]:
    return {key: val for key, val in value.items() if key in CAMERA_SETTINGS_KEYS} if isinstance(value, dict) else {}


def _repository_metadata() -> tuple[str, str | None]:
    root = Path(__file__).resolve().parents[1]
    version = "unverified"
    try:
        for line in (root / "VERSION").read_text(encoding="utf-8").splitlines():
            if line.startswith("version:"):
                version = line.split(":", 1)[1].strip()
                break
    except OSError:
        pass
    try:
        git = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                             capture_output=True, text=True, check=False, timeout=3)
        sha = git.stdout.strip()
        if git.returncode != 0 or not re.fullmatch(r"[0-9a-f]{40}", sha):
            sha = None
    except (OSError, subprocess.TimeoutExpired):
        sha = None
    return version, sha
COUNTERS = ("source_sequence_gaps", "repeated_source_frames", "source_sequence_resets",
            "stream_reconnects", "session_recoveries")
FIELDS = (
    "observed_at_ms", "elapsed_ms", "source_id", "poll_ok", "poll_error",
    "streaming", "stream_connected", "frame_stale", "frame_age_ms", "measured_fps",
    "last_frame_interval_ms", "last_frame_number", "last_success_at_ms",
    *COUNTERS, "backend_cpu_percent_one_core", "backend_rss_mib",
)


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        return None
    v = float(value)
    return v if 0 <= v < float("inf") else None


class OnlineMetric:
    """Bounded-memory aggregates; no percentile is inferred from a few samples."""

    def __init__(self) -> None:
        self.n = 0
        self.total = 0.0
        self.minimum: float | None = None
        self.maximum: float | None = None

    def add(self, value: Any) -> None:
        v = _number(value)
        if v is None:
            return
        self.n += 1
        self.total += v
        self.minimum = v if self.minimum is None else min(self.minimum, v)
        self.maximum = v if self.maximum is None else max(self.maximum, v)

    def report(self) -> dict[str, float | int | None]:
        return {"samples": self.n, "min": self.minimum,
                "mean": round(self.total / self.n, 3) if self.n else None,
                "max": self.maximum}


class CameraStats:
    def __init__(self, source_id: str, settings: dict[str, Any], target_fps: int) -> None:
        self.source_id = source_id
        self.settings = _project_settings(settings)
        self.latest_settings = dict(self.settings)
        self.target_fps = target_fps
        self.latest_target_fps = target_fps
        self.configuration_changes = 0
        self.sample_count = 0
        self.connected_samples = 0
        self.stale_samples = 0
        self.age = OnlineMetric()
        self.fps = OnlineMetric()
        self.interval = OnlineMetric()
        self.recovery = OnlineMetric()
        self.backend_cpu = OnlineMetric()
        self.backend_rss = OnlineMetric()
        self.counters = {key: 0 for key in COUNTERS}
        self.counter_resets = {key: 0 for key in COUNTERS}
        self._previous_counters: dict[str, int] = {}
        self._previous_connected: bool | None = None
        self._outage_started_ms: int | None = None
        self._last_elapsed_ms = 0

    def add(self, sample: dict[str, Any], elapsed_ms: int, *, settings: Any = None, target_fps: int | None = None) -> None:
        if settings is not None and target_fps is not None:
            latest = _project_settings(settings)
            if latest != self.latest_settings or target_fps != self.latest_target_fps:
                self.configuration_changes += 1
                self.latest_settings = latest
                self.latest_target_fps = target_fps
        self.sample_count += 1
        self._last_elapsed_ms = elapsed_ms
        connected = sample.get("stream_connected") is True
        stale = sample.get("frame_stale") is True or not connected
        if connected:
            self.connected_samples += 1
        if stale:
            self.stale_samples += 1
        if connected and not stale:
            self.age.add(sample.get("frame_age_ms"))
            self.fps.add(sample.get("measured_fps"))
            self.interval.add(sample.get("last_frame_interval_ms"))
        self.backend_cpu.add(sample.get("backend_cpu_percent_one_core"))
        self.backend_rss.add(sample.get("backend_rss_mib"))

        if self._previous_connected is True and not connected:
            self._outage_started_ms = elapsed_ms
        elif self._outage_started_ms is not None and connected:
            self.recovery.add(elapsed_ms - self._outage_started_ms)
            self._outage_started_ms = None
        self._previous_connected = connected
        for key in COUNTERS:
            value = sample.get(key)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                continue
            previous = self._previous_counters.get(key)
            if previous is not None:
                if value < previous:
                    self.counter_resets[key] += 1
                    self.counters[key] += value  # New stream-start counter epoch.
                else:
                    self.counters[key] += value - previous
            self._previous_counters[key] = value

    def report(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id, "settings": self.settings, "target_fps": self.target_fps,
            "final_settings": self.latest_settings, "final_target_fps": self.latest_target_fps,
            "configuration_changes": self.configuration_changes,
            "samples": self.sample_count, "connected_samples": self.connected_samples,
            "stale_or_disconnected_samples": self.stale_samples,
            "fresh_frame_age_ms": self.age.report(), "measured_fps": self.fps.report(),
            "frame_interval_ms": self.interval.report(),
            "observed_recovery_ms": self.recovery.report(),
            "unresolved_outage_at_end": self._outage_started_ms is not None,
            "counter_increases": self.counters, "counter_resets": self.counter_resets,
            "backend_cpu_percent_one_core": self.backend_cpu.report(),
            "backend_rss_mib": self.backend_rss.report(),
        }


def _extract_status(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("ok") is not True or not isinstance(payload.get("data"), dict):
        raise ValueError("Invalid PC Studio status API response envelope")
    data = payload["data"]
    if not isinstance(data.get("cameras"), list):
        raise ValueError("Status API response lacks cameras[]")
    return data


def status_provider(base_url: str, timeout_seconds: float = 8.0) -> dict[str, Any]:
    request = Request(base_url.rstrip("/") + "/api/camera/remote/status",
                      headers={"Accept": "application/json"}, method="GET")
    with urlopen(request, timeout=timeout_seconds) as response:
        if response.status != 200:
            raise OSError(f"Camera status HTTP {response.status}")
        payload = response.read(512 * 1024 + 1)
    if len(payload) > 512 * 1024:
        raise ValueError("Camera status response exceeded 512 KiB")
    return _extract_status(json.loads(payload))


def backend_resource_probe(pid: int | None) -> tuple[Callable[[], dict[str, float | None]], str | None]:
    if pid is None:
        return (lambda: {"backend_cpu_percent_one_core": None, "backend_rss_mib": None}), "No --backend-pid supplied"
    try:
        import psutil  # Optional only; never a mandatory runtime dependency.
        process = psutil.Process(pid)
        process.cpu_percent(interval=None)
    except Exception as exc:  # Optional process telemetry must never abort camera evidence.
        return (lambda: {"backend_cpu_percent_one_core": None, "backend_rss_mib": None}), f"Process metrics unavailable: {exc}"
    initial = [True]
    def probe() -> dict[str, float | None]:
        try:
            cpu = process.cpu_percent(interval=None)
            if initial[0]:
                cpu = None  # Initial CPU reading has no meaningful elapsed sampling interval.
                initial[0] = False
            return {"backend_cpu_percent_one_core": round(cpu, 3) if cpu is not None else None,
                    "backend_rss_mib": round(process.memory_info().rss / (1024 * 1024), 3)}
        except (OSError, ValueError, psutil.Error):
            return {"backend_cpu_percent_one_core": None, "backend_rss_mib": None}
    return probe, None


def run_benchmark(*, provider: Callable[[], dict[str, Any]], output_dir: Path,
                  duration_seconds: float, interval_seconds: float, source_ids: list[str] | None = None,
                  environment: str = "unspecified", provenance: str = "measured",
                  backend_pid: int | None = None, version: str = "unverified",
                  commit_sha: str | None = None,
                  resource_probe: Callable[[], dict[str, float | None]] | None = None,
                  monotonic: Callable[[], float] = time.monotonic,
                  epoch: Callable[[], float] = time.time,
                  sleep: Callable[[float], None] = time.sleep) -> dict[str, Any]:
    if duration_seconds <= 0 or interval_seconds <= 0 or interval_seconds > duration_seconds:
        raise ValueError("Require 0 < sample interval <= duration")
    if provenance not in {"measured", "illustrative/synthetic"}:
        raise ValueError("Provenance must be measured or illustrative/synthetic")
    if not environment.strip():
        raise ValueError("Environment description cannot be blank")
    if source_ids is not None and len(set(source_ids)) != len(source_ids):
        raise ValueError("Duplicate source ID filter")
    output_dir.mkdir(parents=True, exist_ok=False)
    probe, resource_limit = backend_resource_probe(backend_pid) if resource_probe is None else (resource_probe, None)
    cameras: dict[str, CameraStats] = {}
    poll_successes = 0
    poll_failures = 0
    first_ms = round(epoch() * 1000)
    start = monotonic()
    deadline = start + duration_seconds
    next_poll = start
    with (output_dir / "samples.csv").open("x", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        while True:
            now = monotonic()
            if now >= deadline and poll_successes + poll_failures:
                break
            if now < next_poll:
                sleep(min(next_poll - now, max(0, deadline - now)))
                continue
            next_poll = now + interval_seconds  # Slow status queries never create a sample backlog.
            sampled_ms = round(epoch() * 1000)
            elapsed_ms = max(0, round((monotonic() - start) * 1000))
            try:
                status = provider()
                if not isinstance(status, dict) or not isinstance(status.get("cameras"), list):
                    raise ValueError("Camera status lacks cameras[]")
                poll_successes += 1
            except (OSError, ValueError, TimeoutError, KeyError) as exc:
                poll_failures += 1
                writer.writerow({"observed_at_ms": sampled_ms, "elapsed_ms": elapsed_ms,
                                 "source_id": "", "poll_ok": False,
                                 "poll_error": f"{type(exc).__name__}: {exc}"[:300]})
                continue
            resource = probe()
            for profile in status["cameras"]:
                if not isinstance(profile, dict) or profile.get("kind") != "esp32":
                    continue
                source = profile.get("source_id")
                if not isinstance(source, str) or not source or (source_ids is not None and source not in source_ids):
                    continue
                if source not in cameras:
                    cameras[source] = CameraStats(source, profile.get("settings"),
                                                  int(profile.get("target_fps") or 0))
                row = {field: profile.get(field) for field in FIELDS}
                row.update(resource)
                row.update({"observed_at_ms": sampled_ms, "elapsed_ms": elapsed_ms,
                            "source_id": source, "poll_ok": True, "poll_error": ""})
                # Never write host/private LAN IPs or raw camera images into evidence.
                writer.writerow(row)
                cameras[source].add(row, elapsed_ms, settings=profile.get("settings"),
                                    target_fps=int(profile.get("target_fps") or 0))
    elapsed = max(0, round((monotonic() - start) * 1000))
    report = {
        "schema_version": SCHEMA_VERSION, "provenance": provenance,
        "version": version, "commit_sha": commit_sha, "started_at_ms": first_ms, "duration_requested_ms": round(duration_seconds * 1000),
        "duration_observed_ms": elapsed, "sampling_interval_requested_ms": round(interval_seconds * 1000),
        "environment": environment, "platform": platform.platform(), "backend_pid": backend_pid,
        "backend_resource_limitation": resource_limit,
        "status_poll_successes": poll_successes, "status_poll_failures": poll_failures,
        "sources": [cameras[key].report() for key in sorted(cameras)],
        "measurement_notes": [
            "FPS and frame intervals are receiver-side status estimates, not camera exposure or transport latency.",
            "Frame age is from original PC receipt; per-source profiles are sampled without changing selection.",
            "Counter increases are observed between successful polls; decreasing counters start new epochs.",
            "Recovery durations measure status-poll visibility only, with sample-period uncertainty; unresolved outages are censored.",
            "CPU percent, when available, is per one logical processor; memory is backend process resident MiB.",
            "Camera images and host/profile-IP fields are not automatically exported; user-supplied environment text is retained.",
            "Configuration changes in the saved profile are counted; run comparisons need stable settings.",
        ],
    }
    with (output_dir / "summary.json").open("x", encoding="utf-8") as file:
        json.dump(report, file, ensure_ascii=False, indent=2, allow_nan=False)
        file.write("\n")
    return report


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base-url", default="http://127.0.0.1:8000")
    p.add_argument("--duration-seconds", type=float, default=600)
    p.add_argument("--sample-seconds", type=float, default=1)
    p.add_argument("--source-id", action="append", default=None, help="Repeat for each ESP source (default: all)")
    p.add_argument("--environment", required=True, help="Wi-Fi/AP, power, firmware, placement, conditions")
    p.add_argument("--backend-pid", type=int, default=None, help="Explicit PC Studio backend PID; needs optional psutil")
    p.add_argument("--version", default=None, help="Override automatic VERSION detection")
    p.add_argument("--commit-sha", default=None, help="Override automatic repository HEAD detection")
    p.add_argument("--output-dir", type=Path, default=None)
    args = p.parse_args(argv)
    if args.backend_pid is not None and args.backend_pid <= 0:
        p.error("--backend-pid must be positive")
    if not 0.2 <= args.sample_seconds <= 60 or not 0.2 <= args.duration_seconds <= 24 * 3600:
        p.error("sample interval must be 0.2–60 seconds; duration 0.2–86400 seconds")
    observed_version, observed_sha = _repository_metadata()
    if args.commit_sha is not None and not re.fullmatch(r"[0-9a-f]{40}", args.commit_sha):
        p.error("--commit-sha must contain 40 lowercase hexadecimal digits")
    dest = args.output_dir or (Path.home() / "MESH_camera_endurance" /
                               datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ"))
    try:
        report = run_benchmark(provider=lambda: status_provider(args.base_url), output_dir=dest,
                               duration_seconds=args.duration_seconds, interval_seconds=args.sample_seconds,
                               source_ids=args.source_id, environment=args.environment,
                               backend_pid=args.backend_pid, version=args.version or observed_version,
                               commit_sha=args.commit_sha or observed_sha)
    except (ValueError, FileExistsError, PermissionError, OSError) as exc:
        p.exit(2, f"Benchmark failed: {exc}\n")
    print(f"Samples: {dest / 'samples.csv'}\nSummary: {dest / 'summary.json'}")
    print(f"Status polls: {report['status_poll_successes']} success, {report['status_poll_failures']} failed; "
          f"ESP sources: {len(report['sources'])}")
    return 0 if report["sources"] and any(x["samples"] for x in report["sources"]) else 1


if __name__ == "__main__":
    sys.exit(main())
