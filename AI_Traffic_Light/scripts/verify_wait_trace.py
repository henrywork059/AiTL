"""Independent replay of sampled service-gate waiting; no engine imports."""
import hashlib
import json
import math

CONTRACT = "normalized_stationary_approach_wait_v1"
STEP_S = 0.2
KINDS = ("vehicle", "pedestrian")


def record_rows(rows):
    return sorted([[a.ident, a.kind, a.progress, a.x, a.y, a.span, a.gate]
                   for a in rows], key=lambda r: r[0])


def replay(frames):
    previous, active = {}, {}
    completed = {k: [] for k in KINDS}
    censored = {k: [] for k in KINDS}
    timeline = []
    for frame in frames:
        current, continuous, queued = {}, set(), set()
        for row in frame:
            ident, kind, progress, x, y, span, gate = row
            if (not isinstance(ident, str) or not ident or ident in current or
                    not isinstance(gate, str) or not gate or kind not in KINDS or
                    span <= 0 or not all(math.isfinite(v) for v in (progress, x, y, span))):
                raise ValueError("Invalid wait trace observation")
            current[ident] = row
            old = previous.get(ident)
            if old is None:
                continue
            if old[1] != kind:
                raise ValueError("Agent kind changed")
            distance = math.hypot(x - old[3], y - old[4])
            key = (ident, gate, kind)
            if (old[6] != gate or old[5] != span or progress < old[2] - .25 or
                    distance > span * .5):
                continue
            continuous.add(key)
            if -1 <= progress < 0 and -1 <= old[2] < 0 and distance / span / STEP_S <= .01:
                queued.add(key)
        for key, count in active.items():
            if key not in queued:
                (completed if key in continuous else censored)[key[2]].append(count)
        active = {key: active.get(key, 0) + 1 for key in queued}
        timeline.append({kind: sum(key[2] == kind for key in queued) for kind in KINDS})
        previous = current
    for key, count in active.items():
        censored[key[2]].append(count)
    return timeline, {kind: {
        "completed_seconds": sorted(round(n * STEP_S, 6) for n in completed[kind]),
        "censored_observed_seconds": sorted(round(n * STEP_S, 6) for n in censored[kind]),
        "observed_agent_seconds": round(sum(row[kind] for row in timeline) * STEP_S, 6),
    } for kind in KINDS}


def qualify(frames, timeline, summary, episodes):
    counts, waits = replay(frames)
    if len(counts) != len(timeline) or summary["samples"] != len(frames):
        raise ValueError("Wait trace length mismatch")
    for tick, (actual, expected) in enumerate(zip(counts, timeline), 1):
        if (expected["tick"] != tick or expected["t_seconds"] != round(tick * STEP_S, 6) or
                any(actual[k] != expected[k + "_queue"] for k in KINDS)):
            raise ValueError(f"Wait trace queue mismatch at tick {tick}")
    for kind, actual in waits.items():
        expected = episodes[kind]
        for field in ("completed_seconds", "censored_observed_seconds"):
            if actual[field] != sorted(expected[field]):
                raise ValueError(f"Wait episode mismatch: {kind} {field}")
        if (actual["observed_agent_seconds"] != expected["observed_agent_seconds"] or
                actual["observed_agent_seconds"] != summary[kind + "_wait_agent_s"] or
                max((row[kind] for row in counts), default=0) != summary["peak_" + kind + "_queue"] or
                expected["completed_count"] != len(actual["completed_seconds"]) or
                expected["censored_count"] != len(actual["censored_observed_seconds"])):
            raise ValueError(f"Wait integral or count mismatch: {kind}")
    digest = hashlib.sha256(json.dumps(frames, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    return {"contract": CONTRACT, "step_s": STEP_S, "trace_sha256": digest,
            "samples": len(frames), "independent_replay_passed": True, "waiting": waits}


def retain(out, engine, repeat, result):
    frames = result.pop("wait_trace")
    episodes = result.pop("wait_episodes")
    audit = qualify(frames, result["timeline"], result["summary"], episodes)
    (out / f"{engine}-{repeat}-wait-trace.json").write_text(json.dumps({
        "contract": CONTRACT, "step_s": STEP_S, "frames": frames,
        "episodes": episodes, "audit": audit}, separators=(",", ":"), allow_nan=False), encoding="utf-8")
    result["wait_audit"] = audit


def comparison(runs, left, right, matched_demand):
    arms = {name: [r for r in runs if r["engine"] == name] for name in (left, right)}
    for name, rows in arms.items():
        if len(rows) != 2 or rows[0]["wait_audit"] != rows[1]["wait_audit"]:
            raise ValueError(f"Nonrepeatable wait evidence: {name}")
    deltas = {k: round(arms[right][0]["summary"][k + "_wait_agent_s"] -
                       arms[left][0]["summary"][k + "_wait_agent_s"], 6) for k in KINDS}
    return {"contract": CONTRACT, "measurement_replay": "pass", "within_engine_repeat": "pass",
            "left": left, "right": right, "matched_offered_demand": matched_demand,
            "right_minus_left_agent_seconds": deltas,
            "exact_wait_totals_equal": all(v == 0 for v in deltas.values()),
            "production_wait_parity": "not_established", "default_migration_allowed": False}
