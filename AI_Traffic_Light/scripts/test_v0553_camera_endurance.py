"""Deterministic, hardware-free regression for Update 09/H05 endurance export."""
from __future__ import annotations

import csv
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from camera_endurance_benchmark import CameraStats, _extract_status, run_benchmark


class FakeClock:
    def __init__(self) -> None:
        self.seconds = 0.0

    def monotonic(self) -> float:
        return self.seconds

    def epoch(self) -> float:
        return 1700000000.0 + self.seconds

    def sleep(self, seconds: float) -> None:
        assert seconds >= 0
        self.seconds += seconds


def camera(source: str, *, connected: bool, age: int | None, gaps: int,
           reconnects: int = 0, repeated: int = 0) -> dict:
    return {
        "source_id": source, "kind": "esp32", "host": "192.168.1.90", "settings": {
            "frame_size": "QVGA", "jpeg_quality": 24,
        }, "target_fps": 10, "stream_connected": connected,
        "streaming": True, "frame_stale": not connected, "frame_age_ms": age,
        "measured_fps": 10.0 if connected else 0.0,
        "last_frame_interval_ms": 100.0 if connected else None,
        "last_frame_number": gaps + 10, "last_success_at_ms": 1700000000000,
        "source_sequence_gaps": gaps, "repeated_source_frames": repeated,
        "source_sequence_resets": 0, "stream_reconnects": reconnects,
        "session_recoveries": 0,
    }


def test_report_and_independence() -> None:
    clock = FakeClock()
    snapshots = [
        [camera("A", connected=True, age=100, gaps=0), camera("B", connected=False, age=None, gaps=0)],
        [camera("A", connected=False, age=1200, gaps=2), camera("B", connected=True, age=30, gaps=1)],
        [camera("A", connected=True, age=100, gaps=3, reconnects=1), camera("B", connected=True, age=50, gaps=2)],
        [camera("A", connected=True, age=80, gaps=0, reconnects=0), camera("B", connected=False, age=1000, gaps=2)],
    ]
    index = [0]

    def provider() -> dict:
        i = index[0]
        index[0] += 1
        if i == 4:
            raise OSError("backend unreachable")
        # Deliberately inconsistent selected-camera top level. The recorder MUST
        # use only keyed cameras[] observations, not mixed selected state.
        return {"active_source_id": "B", "source_id": "A", "measured_fps": 999, "cameras": snapshots[i]}

    with TemporaryDirectory() as temp:
        folder = Path(temp) / "recorded"
        report = run_benchmark(
            provider=provider, output_dir=folder, duration_seconds=5, interval_seconds=1,
            environment="SYNTHETIC test only; no ESP", provenance="illustrative/synthetic",
            version="0_5_53", resource_probe=lambda: {
                "backend_cpu_percent_one_core": 12.5, "backend_rss_mib": 120.0,
            }, monotonic=clock.monotonic, epoch=clock.epoch, sleep=clock.sleep,
        )
        assert report["schema_version"] == 1
        assert report["provenance"] == "illustrative/synthetic"
        assert (report["status_poll_successes"], report["status_poll_failures"]) == (4, 1)
        assert (report["started_at_ms"], report["duration_observed_ms"]) == (1700000000000, 5000)
        assert len(report["sources"]) == 2
        a, b = report["sources"]
        assert (a["source_id"], b["source_id"]) == ("A", "B")
        assert (a["samples"], b["samples"]) == (4, 4)
        assert a["counter_increases"]["source_sequence_gaps"] == 3
        assert a["counter_resets"]["source_sequence_gaps"] == 1
        assert a["counter_increases"]["stream_reconnects"] == 1
        assert a["counter_resets"]["stream_reconnects"] == 1
        assert b["counter_increases"]["source_sequence_gaps"] == 2
        assert (a["fresh_frame_age_ms"]["samples"], b["fresh_frame_age_ms"]["samples"]) == (3, 2)
        assert a["observed_recovery_ms"]["mean"] == 1000
        assert b["observed_recovery_ms"]["samples"] == 0
        assert b["unresolved_outage_at_end"]
        assert a["backend_cpu_percent_one_core"]["mean"] == 12.5
        assert a["backend_rss_mib"]["mean"] == 120
        on_disk = json.loads((folder / "summary.json").read_text(encoding="utf-8"))
        assert on_disk == report
        with (folder / "samples.csv").open(encoding="utf-8", newline="") as inp:
            rows = list(csv.DictReader(inp))
        assert len(rows) == 9
        assert rows[-1]["poll_ok"] == "False"
        assert "backend unreachable" in rows[-1]["poll_error"]
        assert rows[0]["source_id"] == "A" and rows[1]["source_id"] == "B"
        assert rows[0]["measured_fps"] == "10.0"  # Not contradictory top-level 999.
        assert "192.168.1.90" not in (folder / "summary.json").read_text(encoding="utf-8")
        assert "192.168.1.90" not in (folder / "samples.csv").read_text(encoding="utf-8")
        try:
            run_benchmark(provider=provider, output_dir=folder, duration_seconds=2,
                          interval_seconds=1, environment="fixture", provenance="illustrative/synthetic")
        except FileExistsError:
            pass
        else:
            raise AssertionError("Pre-existing evidence directory must not be overwritten")


def test_counter_epoch_and_censored_outage() -> None:
    stats = CameraStats("C", {"frame_size": "VGA"}, 20)
    for i, (connected, gaps, repeated) in enumerate([
        (True, 10, 0), (False, 12, 3), (False, 0, 0), (True, 2, 1),
    ]):
        stats.add(camera("C", connected=connected, age=i*100, gaps=gaps, repeated=repeated), i*500)
    result = stats.report()
    assert result["counter_increases"]["source_sequence_gaps"] == 4
    assert result["counter_resets"]["source_sequence_gaps"] == 1
    assert result["counter_increases"]["repeated_source_frames"] == 4
    assert result["observed_recovery_ms"]["mean"] == 1000
    assert not result["unresolved_outage_at_end"]
    stats.add(camera("C", connected=False, age=1000, gaps=2), 2500)
    assert stats.report()["unresolved_outage_at_end"]


def test_api_validation() -> None:
    assert _extract_status({"ok": True, "data": {"cameras": []}}) == {"cameras": []}
    for payload in ({"ok": False, "data": {"cameras": []}}, {"ok": True, "data": {}}, {}):
        try:
            _extract_status(payload)
        except ValueError:
            pass
        else:
            raise AssertionError("Invalid API envelope accepted")


def main() -> int:
    test_report_and_independence()
    test_counter_epoch_and_censored_outage()
    test_api_validation()
    print("[PASS] V0553 synthetic status samples, two-camera identity, outage timing, counters, JSON/CSV, privacy and validation")
    return 0


if __name__ == "__main__":
    sys.exit(main())
