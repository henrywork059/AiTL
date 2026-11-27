"""Real controlled fixture/async runtime check; separate from the native-plan reference."""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'AI_Traffic_Light/apps/pc-studio/backend'))
from app.services.sumo_shadow_fixture import PhaseMap
from app.services.sumo_shadow_runtime import GeneratedSession, ShadowRuntime


def run(seed):
    session = GeneratedSession(seed)
    digest = hashlib.sha256()
    observed = set()
    states = set()
    phase_map = PhaseMap.load(Path(session._temp.name) / 'network.xml')
    cycle = ['vehicle_green'] * 60 + ['vehicle_yellow'] * 15 + ['all_red'] * 10 + ['pedestrian_green'] * 60 + ['pedestrian_flashing'] * 25 + ['all_red'] * 10
    try:
        for tick in range(1500):
            phase = cycle[tick % len(cycle)]
            session.set_phase(phase)
            session.advance()
            state = session.last_permission
            assert len(state) == len(phase_map.links) and set(state) <= {'r', 'G'}
            grants = {i for i, value in enumerate(state) if value == 'G'}
            expected = set(phase_map.vehicles if phase == 'vehicle_green' else phase_map.pedestrians if phase == 'pedestrian_green' else ())
            assert grants in (set(), expected), (phase, state)
            rows = sorted(session.agents(), key=lambda row: row.id)
            states.add(state)
            observed.update(row.id for row in rows)
            digest.update(json.dumps([tick, phase, state, [asdict(row) for row in rows]], sort_keys=True).encode())
        assert any(s.count('G') == 2 for s in states) and any(s.count('G') == 4 for s in states)
        return {'digest': digest.hexdigest(), 'observed_agents': len(observed), 'states': sorted(states),
                'vehicle_arrivals': len(session.arrived), 'pedestrian_arrivals': len(session.person_arrived)}
    finally:
        session.close()
        assert not session.proc.is_alive()


def wait_for(runtime, predicate):
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        status = runtime.status()
        if status['status'] == 'unavailable':
            raise RuntimeError(status['reason'])
        if predicate(status):
            return status
        time.sleep(0.01)
    raise TimeoutError('Shadow runtime did not reach expected state')


def main():
    a, b = run(42), run(42)
    assert a == b, 'Controlled scenario not repeatable'
    runtime = ShadowRuntime()
    try:
        runtime.reset(42)
        wait_for(runtime, lambda s: s['status'] == 'running')
        for phase in ['vehicle_green'] * 4 + ['vehicle_green'] * 3 + ['all_red']:
            runtime.observe(phase)
        state = wait_for(runtime, lambda s: s['snapshot'] is not None and s['snapshot']['tick'] == 2)
        assert state['legacy_steps'] == 8 and state['requested_phase'] == 'all_red'
        assert state['applied_permission'] == 'r' * 20
        runtime.stop()
        assert runtime.status()['snapshot'] is None
    finally:
        runtime.close()
    result = {'evidence': 'executed synthetic controlled fixture', 'seed': 42, 'duration_s': 300,
              'step_s': 0.2, 'repetitions': [a, b], 'asynchronous_runtime': 'passed',
              'limitation': 'restricted east-west demand; illustrative phase cycle; not a matched legacy controller benchmark'}
    Path(sys.argv[1]).write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()
