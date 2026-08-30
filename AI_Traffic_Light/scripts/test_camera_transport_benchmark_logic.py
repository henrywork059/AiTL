from __future__ import annotations

from test_camera_transport_benchmark import TestResult, build_analysis_evidence, diagnose, score_candidate


def result(
    key: str,
    status: str = "PASS",
    *,
    frames: int = 8,
    requested: int = 8,
    fps: float = 5.0,
    production_candidate: bool = True,
) -> TestResult:
    return TestResult(
        key=key,
        name=key,
        transport="test",
        status=status,
        requested_frames=requested,
        frames=frames if status == "PASS" else 0,
        elapsed_ms=1600.0,
        measured_fps=fps if status == "PASS" else 0.0,
        completion_ratio=(frames / requested) if status == "PASS" and requested else 0.0,
        production_candidate=production_candidate,
    )


def baseline() -> dict[str, TestResult]:
    return {
        "capture_single": result("capture_single", frames=1, requested=1),
        "snapshot_polling": result("snapshot_polling"),
    }


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print(f"[PASS] {message}")


def main() -> int:
    rows = baseline()
    rows.update({
        "direct_sendmsg_1200": result("direct_sendmsg_1200", "FAIL"),
        "direct_sendmsg_5000": result("direct_sendmsg_5000"),
    })
    diagnosis = diagnose(rows, 5)
    check(diagnosis["diagnosis_code"] == "timeout_too_aggressive", "benchmark logic identifies an overly aggressive configured timeout")

    rows = baseline()
    rows.update({
        "direct_sendmsg_1200": result("direct_sendmsg_1200", "FAIL"),
        "direct_sendmsg_5000": result("direct_sendmsg_5000", "FAIL"),
        "direct_send": result("direct_send"),
    })
    diagnosis = diagnose(rows, 5)
    check(diagnosis["diagnosis_code"] == "sendmsg_specific_failure", "benchmark logic isolates sendmsg from plain send")

    rows = baseline()
    rows.update({
        "direct_sendmsg_5000": result("direct_sendmsg_5000", "FAIL"),
        "direct_send": result("direct_send", "FAIL"),
        "staged_send": result("staged_send"),
        "dram_copy_send": result("dram_copy_send"),
    })
    diagnosis = diagnose(rows, 5)
    check(diagnosis["diagnosis_code"] == "direct_psram_socket_source_failure", "benchmark logic isolates direct PSRAM-to-socket failure")
    check(diagnosis["recommended_key"] == "dram_copy_send", "whole-frame DRAM copy is preferred when it is healthy")

    rows = baseline()
    rows.update({
        "direct_sendmsg_5000": result("direct_sendmsg_5000", "FAIL"),
        "direct_send": result("direct_send", "FAIL"),
        "staged_send": result("staged_send", "FAIL"),
        "dram_copy_send": result("dram_copy_send", "FAIL"),
        "mjpeg": result("mjpeg"),
    })
    diagnosis = diagnose(rows, 5)
    check(diagnosis["diagnosis_code"] == "custom_tcp_sender_failure", "benchmark logic recognizes stable MJPEG with failed custom ATL1 direct transport")
    check(diagnosis["recommended_key"] == "mjpeg", "stable MJPEG becomes the fallback when ATL1 candidates fail")

    rows = baseline()
    rows.update({
        "direct_sendmsg_5000": result("direct_sendmsg_5000", "FAIL"),
        "direct_send": result("direct_send", "FAIL"),
        "staged_send": result("staged_send", "FAIL"),
        "dram_copy_send": result("dram_copy_send", "FAIL"),
        "mjpeg": result("mjpeg", "FAIL"),
        "udp": result("udp"),
    })
    diagnosis = diagnose(rows, 5)
    check(diagnosis["diagnosis_code"] == "persistent_tcp_backpressure", "benchmark logic identifies persistent TCP/backpressure when UDP and snapshots survive")

    fast_incomplete = result("fast_incomplete", "PASS", frames=4, requested=8, fps=15.0)
    fast_incomplete.completion_ratio = 0.5
    stable = result("stable", "PASS", frames=8, requested=8, fps=5.0)
    check(score_candidate(stable, 5) > score_candidate(fast_incomplete, 5), "candidate ranking prioritizes complete reliable frames over nominal speed")

    rows = baseline()
    rows.update({
        "direct_sendmsg_1200": result("direct_sendmsg_1200", "FAIL"),
        "direct_sendmsg_5000": result("direct_sendmsg_5000"),
        "direct_send": result("direct_send"),
        "staged_send": result("staged_send"),
        "dram_copy_send": result("dram_copy_send"),
        "dram_copy_sendmsg": result("dram_copy_sendmsg"),
        "synthetic_sendmsg": result("synthetic_sendmsg", production_candidate=False),
        "synthetic_send": result("synthetic_send", production_candidate=False),
        "mjpeg": result("mjpeg"),
        "udp": result("udp"),
    })
    diagnosis = diagnose(rows, 5)
    evidence = build_analysis_evidence(rows, diagnosis)
    check("timeout_1200_vs_5000" in evidence["comparative_pairs"], "analysis evidence preserves the timeout A/B comparison")
    check("direct_psram_vs_full_dram_copy" in evidence["comparative_pairs"], "analysis evidence preserves the PSRAM-vs-DRAM comparison")
    check(bool(evidence["hypothesis_ranking"]), "analysis evidence emits at least one ranked hypothesis")

    print("\nCamera transport benchmark offline regression passed. No ESP hardware or --host argument was required.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
