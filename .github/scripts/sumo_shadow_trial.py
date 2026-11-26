"""Disposable CI only: exercise the shadow adapter against pinned SUMO/TraCI."""
from dataclasses import asdict
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import socket
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'AI_Traffic_Light/apps/pc-studio/backend'))
from app.services.sumo_shadow_adapter import ShadowAgent, SumoShadowAdapter, STEP_S


class Session:
    def __init__(self, binary, root, seed):
        import traci
        self.conn = None
        self.proc = None
        self.tick = 0
        self.arrived = set()
        self.person_arrived = set()
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        try:
            self.proc = subprocess.Popen([str(binary), '-n', 'network.xml', '-r', 'routes.xml',
                '--seed', str(seed), '--step-length', str(STEP_S), '--time-to-teleport', '-1',
                '--no-step-log', 'true', '--remote-port', str(port)], cwd=root)
            self.conn = traci.connect(port=port, host='127.0.0.1', proc=self.proc,
                                      numRetries=20, waitBetweenRetries=0.25)
            # Private TraCI socket seam deliberately restricted to this pinned CI trial.
            self.conn._socket.settimeout(5)
            if self.conn.getVersion()[1].split()[-1] != '1.28.0':
                raise RuntimeError('Unexpected SUMO version')
        except Exception:
            self.close()
            raise

    def advance(self):
        self.conn.simulationStep()
        self.tick += 1
        if abs(self.conn.simulation.getTime() - self.tick * STEP_S) > 1e-6:
            raise RuntimeError('Clock mismatch')
        self.arrived.update(self.conn.simulation.getArrivedIDList())
        self.person_arrived.update(self.conn.simulation.getArrivedPersonIDList())

    def agents(self):
        rows = []
        for kind, domain in [('vehicle', self.conn.vehicle), ('pedestrian', self.conn.person)]:
            for engine_id in domain.getIDList():
                x, y = domain.getPosition(engine_id)
                rows.append(ShadowAgent(kind, engine_id, x, y, domain.getSpeed(engine_id),
                                        domain.getRoadID(engine_id)))
        return tuple(rows)

    def close(self):
        try:
            if self.conn is not None:
                try:
                    self.conn.close(wait=False)
                except Exception:
                    pass  # Still reap the owned process after a broken connection.
                finally:
                    self.conn = None
        finally:
            if self.proc is not None:
                try:
                    self.proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self.proc.kill()
                    self.proc.wait(timeout=5)


def main():
    root = Path(sys.argv[1]).resolve()
    binary = Path(sys.argv[2]).resolve()
    output = Path(sys.argv[3]).resolve()
    for pkg in ('traci', 'sumolib', 'eclipse-sumo', 'sumo-data'):
        if version(pkg) != '1.28.0':
            raise RuntimeError(f'Unexpected {pkg} version')
    sessions = []
    def factory(seed):
        session = Session(binary, root, seed)
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
        assert all(s.proc.poll() is not None for s in sessions)
        # Forced process loss must clear the snapshot and allow a clean reset.
        adapter.reset(seed=42)
        sessions[-1].proc.kill()
        sessions[-1].proc.wait(timeout=5)
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
    assert all(s.proc.poll() is not None for s in sessions)
    result = {'evidence': 'executed synthetic shadow trial; native fixture signal plan', 'runs': runs,
              'process_cleanup': True, 'failure_recovery': True}
    output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
