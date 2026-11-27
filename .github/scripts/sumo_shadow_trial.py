"""Disposable CI only: exercise the shadow adapter against pinned libsumo in a child process."""
from dataclasses import asdict
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'AI_Traffic_Light/apps/pc-studio/backend'))
from app.services.sumo_shadow_adapter import SumoShadowAdapter
from app.services.sumo_shadow_process import LibsumoSession


def main():
    root = Path(sys.argv[1]).resolve()
    output = Path(sys.argv[2]).resolve()
    for pkg in ('libsumo', 'traci', 'sumolib', 'eclipse-sumo', 'sumo-data'):
        if version(pkg) != '1.28.0':
            raise RuntimeError(f'Unexpected {pkg} version')
    sessions = []
    def factory(seed):
        session = LibsumoSession(root, seed)
        sessions.append(session)
        return session
    adapter = SumoShadowAdapter(factory)
    runs = []
    try:
        for _ in range(2):
            adapter.reset(seed=42)
            digest = hashlib.sha256()
            observed = set()
            first_horizon = None
            for i in range(1500):
                state = adapter.step()
                observed.update(a.id for a in state.agents)
                digest.update(json.dumps(asdict(state), sort_keys=True).encode() + b'\n')
                if i == 899:
                    first_horizon = {'vehicle_arrivals': len(sessions[-1].arrived),
                                     'pedestrian_arrivals': len(sessions[-1].person_arrived)}
                if i == 10:
                    adapter.set_paused(True)
                    assert adapter.step().tick == state.tick
                    adapter.set_paused(False)
            runs.append({'digest': digest.hexdigest(), 'observed': sorted(observed),
                         'at_180_s': first_horizon, 'at_300_s': {
                             'vehicle_arrivals': len(sessions[-1].arrived),
                             'pedestrian_arrivals': len(sessions[-1].person_arrived)}})
        assert runs[0] == runs[1], 'Nonrepeatable shadow runs'
        assert set(runs[0]['observed']) == {f'sumo:{kind}:{prefix}{i}' for kind, prefix in
                                          [('vehicle', 'v'), ('pedestrian', 'p')] for i in range(12)}
        adapter.shutdown()
        assert all(not s.proc.is_alive() for s in sessions)
        # Forced process loss must clear the snapshot and allow a clean reset.
        adapter.reset(seed=42)
        sessions[-1].proc.kill()
        sessions[-1].proc.join(5)
        try:
            adapter.step()
        except Exception:
            assert adapter.snapshot() is None
        else:
            raise AssertionError('Lost process was not detected')
        adapter.reset(seed=42)
        assert adapter.step().tick == 1
    finally:
        adapter.shutdown()
    assert all(not s.proc.is_alive() for s in sessions)
    result = {'evidence': 'executed synthetic shadow trial; native fixture signal plan', 'runs': runs,
              'process_cleanup': True, 'failure_recovery': True, 'transport': 'libsumo_child_pipe',
              'reference_traci_run': 45734614084,
              'reference_digest_match': runs[0]['digest'] == '34c24376cf005cdb3d5f9ab0b4aab822847970f49b380fdf139fb0426ee76097'}
    output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
