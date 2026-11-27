"""Offline phase-map and runtime ownership tests; no native package needed."""
from pathlib import Path
import sys
import tempfile
from threading import Event
import time
import unittest
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'apps/pc-studio/backend'))
from app.services.sumo_shadow_adapter import ShadowAgent
from app.services.sumo_shadow_fixture import PhaseMap, write_scenario
from app.services.sumo_shadow_runtime import ShadowRuntime


def fixture(path, *, conflict=False):
    root = ET.Element('net')
    for name in ('WC', 'CW', 'EC', 'CE', 'NC', 'CN', 'SC', 'CS'):
        ET.SubElement(root, 'edge', id=name)
    for i in range(4):
        ET.SubElement(root, 'edge', id=f':C_c{i}', function='crossing')
    junction = ET.SubElement(root, 'junction', id='C')
    for i in range(20):
        bits = '0' * 20
        if conflict and i == 5:
            bits = bits[:6] + '1' + bits[7:]
        ET.SubElement(junction, 'request', index=str(i), foes=bits)
        a, b = ('NC', 'CE')
        if i == 5:
            a, b = 'EC', 'CW'
        elif i == 13:
            a, b = 'WC', 'CE'
        elif i >= 16:
            a, b = f':C_w{i-16}', f':C_c{i-16}'
        ET.SubElement(root, 'connection', {'from': a, 'to': b, 'fromLane': '1', 'toLane': '1',
                      'dir': 's', 'tl': 'C', 'linkIndex': str(i)})
    ET.ElementTree(root).write(path)


class FakeSession:
    def __init__(self, seed):
        self.seed = seed
        self.tick = 0
        self.closed = False
        self.last_permission = None
        self.fail = False

    def set_phase(self, phase):
        self.last_permission = phase

    def advance(self):
        if self.fail:
            raise RuntimeError('engine lost')
        self.tick += 1

    def agents(self):
        return (ShadowAgent('vehicle', '0', self.tick, 0, 1, 'WC'),)

    def close(self):
        self.closed = True


def until(predicate):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.005)
    raise AssertionError('Timed out waiting for worker')


class Tests(unittest.TestCase):
    def test_mapping_conflict_and_clearance(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'network.xml'
            fixture(path)
            mapping = PhaseMap.load(path)
            def state(phase, vehicle=False, pedestrian=False):
                return mapping.state(phase, vehicle_inside=vehicle, pedestrian_inside=pedestrian)
            self.assertEqual([i for i, c in enumerate(state('vehicle_green')) if c == 'G'], [5, 13])
            self.assertEqual([i for i, c in enumerate(state('pedestrian_green')) if c == 'G'], [16, 17, 18, 19])
            for phase in ('all_red', 'vehicle_yellow', 'pedestrian_flashing', 'unknown'):
                self.assertEqual(state(phase), 'r' * 20)
            self.assertEqual(state('vehicle_green', pedestrian=True), 'r' * 20)
            self.assertEqual(state('pedestrian_green', vehicle=True), 'r' * 20)
            fixture(path, conflict=True)
            with self.assertRaises(ValueError):
                PhaseMap.load(path)

    def test_controlled_routes(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            write_scenario(root, controlled=True)
            routes = ET.parse(root / 'routes.xml').getroot()
            self.assertEqual({r.get('edges') for r in routes.findall('route')}, {'WC CE', 'EC CW'})
            self.assertEqual(len(routes.findall('vehicle')), 12)
            self.assertEqual(len(routes.findall('person')), 12)
            write_scenario(root)
            self.assertEqual({r.get('edges') for r in ET.parse(root / 'routes.xml').getroot().findall('route')}, {'WC CE', 'NC CS'})

    def test_bounded_geometry_presets_preserve_demand_and_topology(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            write_scenario(root, controlled=True, density="normal")
            routes=(root/"routes.xml").read_bytes()
            edges=(root/"edges.xml").read_bytes()
            for geometry,expected in (("compact",("60","60")),("elongated",("100","60"))):
                write_scenario(root, controlled=True, density="normal", geometry=geometry)
                self.assertEqual((root/"routes.xml").read_bytes(),routes)
                self.assertEqual((root/"edges.xml").read_bytes(),edges)
                nodes=ET.parse(root/"nodes.xml").getroot()
                self.assertEqual((nodes.find("node[@id='E']").get("x"),nodes.find("node[@id='N']").get("y")),expected)
            with self.assertRaises(ValueError):
                write_scenario(root, controlled=True, density="normal", geometry="unknown")
            with self.assertRaises(ValueError):
                write_scenario(root, geometry="compact")

    def test_fixed_step_reset_stop_and_phase_mapping(self):
        sessions = []
        def factory(seed):
            sessions.append(FakeSession(seed))
            return sessions[-1]
        runtime = ShadowRuntime(factory)
        self.addCleanup(runtime.close)
        runtime.reset(42)
        until(lambda: runtime.status()['status'] == 'running')
        for phase in ['vehicle_green'] * 4 + ['vehicle_green'] * 3 + ['all_red']:
            runtime.observe(phase)
        until(lambda: runtime.status()['snapshot']['tick'] == 2)
        status = runtime.status()
        self.assertEqual(status['legacy_steps'], 8)
        self.assertEqual(status['requested_phase'], 'all_red')
        self.assertEqual(status['snapshot']['agents'][0]['id'], 'sumo:vehicle:0')
        runtime.reset(43)
        until(lambda: runtime.status()['status'] == 'running')
        self.assertTrue(sessions[0].closed)
        self.assertEqual(runtime.status()['snapshot']['seed'], 43)
        runtime.stop()
        self.assertIsNone(runtime.status()['snapshot'])
        until(lambda: sessions[-1].closed)
        runtime.observe('vehicle_green')
        self.assertEqual(runtime.status()['status'], 'idle')

    def test_engine_failure_and_overload_do_not_publish(self):
        gate = Event()
        sessions = []
        def factory(seed):
            gate.wait(5)
            sessions.append(FakeSession(seed))
            return sessions[-1]
        runtime = ShadowRuntime(factory, max_backlog=2)
        self.addCleanup(runtime.close)
        self.addCleanup(gate.set)
        runtime.reset(42)
        for _ in range(16):
            runtime.observe('vehicle_green')
        self.assertEqual(runtime.status()['reason'], 'backlog_exceeded')
        self.assertIsNone(runtime.status()['snapshot'])
        gate.set()
        runtime.reset(43)
        until(lambda: runtime.status()['status'] == 'running')
        sessions[-1].fail = True
        for _ in range(4):
            runtime.observe('pedestrian_green')
        until(lambda: runtime.status()['status'] == 'unavailable')
        self.assertIsNone(runtime.status()['snapshot'])
        self.assertTrue(sessions[-1].closed)


if __name__ == '__main__':
    unittest.main()
