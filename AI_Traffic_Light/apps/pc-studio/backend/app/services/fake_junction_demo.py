"""Execute one bounded fake-only bench demonstration using virtual time.

No camera, signal, hardware, audio, network, persistence or worker integration.
"""
from dataclasses import asdict
from typing import Literal

from .bench_output import FakeBenchAdapter
from .bench_lighting import FakeLightingDemo
from .bench_speaker import FakeSpeakerDemo

DemoScenario = Literal["nominal", "missing_ack", "rejected_ack", "wrong_ack",
                       "late_ack", "disconnect", "manual_stop"]
SCENARIOS = ("nominal", "missing_ack", "rejected_ack", "wrong_ack",
             "late_ack", "disconnect", "manual_stop")
FAULTS = {"missing_ack": "missing", "rejected_ack": "rejected",
          "wrong_ack": "wrong_id", "late_ack": "late"}
LEASE_MS = 1000


def run_fake_junction_demo(scenario: DemoScenario, *, authorized: bool = False) -> dict:
    if scenario not in SCENARIOS or type(authorized) is not bool:
        raise ValueError("Invalid fake demonstration input")
    time_ms = 0

    def clock():
        return time_ms / 1000

    light_adapter, speaker_adapter = FakeBenchAdapter(clock), FakeBenchAdapter(clock)
    light = FakeLightingDemo(enabled=True, clock=clock, adapter=light_adapter)
    speaker = FakeSpeakerDemo(enabled=True, clock=clock, adapter=speaker_adapter)
    trace = []

    def record(event, ack=None):
        trace.append({"time_ms": time_ms, "event": event,
                      "lighting": light.status(), "speaker": speaker.status(),
                      "ack": asdict(ack) if ack is not None else None})

    def stop_both(event):
        light.off()
        speaker.off()
        record(event)

    both_armed = False
    light_ack = speaker_ack = None
    try:
        record("initial_off")
        light.connect()
        speaker.connect()
        record("connected")
        light_armed = light.arm(authorized=authorized)
        speaker_armed = speaker.arm(authorized=authorized)
        both_armed = light_armed and speaker_armed
        record("authorization_checked")
        if scenario in FAULTS:
            speaker_adapter.ack_mode = FAULTS[scenario]
        light_ack = light.pulse(LEASE_MS)
        record("lighting_request", light_ack)
        if light_ack is not None:
            speaker_ack = speaker.play("demo_accessibility", 50, LEASE_MS)
        record("speaker_request" if light_ack is not None else "speaker_not_requested", speaker_ack)
        if light_ack is None or speaker_ack is None:
            stop_both("fault_stop" if authorized else "authorization_denied")
        elif scenario == "disconnect":
            speaker.disconnect()
            light.off()
            record("disconnect_stop")
        elif scenario == "manual_stop":
            stop_both("manual_stop")
        else:
            time_ms += LEASE_MS
            light.watchdog_tick()
            speaker.watchdog_tick()
            record("lease_expired")
    finally:
        light.disconnect()
        speaker.disconnect()
        record("final_disconnected")

    final = trace[-1]
    active_both = any(row["lighting"]["active"] and row["speaker"]["active"] for row in trace)
    expected_activation = authorized and scenario not in FAULTS
    terminal_event = "authorization_denied" if not authorized else (
        "fault_stop" if scenario in FAULTS else {
            "disconnect": "disconnect_stop", "manual_stop": "manual_stop",
            "nominal": "lease_expired",
        }[scenario])
    terminal = trace[-2]
    checks = {
        "authorization_matches": both_armed == authorized,
        "activation_matches_scenario": active_both == expected_activation,
        "denied_never_active": authorized or not any(
            row["lighting"]["active"] or row["speaker"]["active"] for row in trace),
        "acknowledgments_match": (light_ack is not None) == authorized and
            (speaker_ack is not None) == expected_activation,
        "expected_stop": terminal["event"] == terminal_event and not any(
            terminal[k][v] for k in ("lighting", "speaker") for v in ("active", "armed")),
        "final_disconnected": not any(
            final[k][v] for k in ("lighting", "speaker") for v in ("active", "armed", "connected")),
        "physical_and_audio_unavailable": all(
            row["lighting"]["physical_output_allowed"] is False and
            row["lighting"]["physical_lighting_available"] is False and
            row["speaker"]["physical_output_allowed"] is False and
            row["speaker"]["physical_speaker_available"] is False and
            row["speaker"]["audio_playback"] is False for row in trace),
    }
    return {"schema_version": 1, "scenario": scenario, "authorization_requested": authorized,
            "provenance": "illustrative/synthetic", "time_basis": "virtual_ms",
            "lease_ms": LEASE_MS, "prototype_only": True, "physical_output_allowed": False,
            "audio_playback": False, "trace": trace, "checks": checks}
