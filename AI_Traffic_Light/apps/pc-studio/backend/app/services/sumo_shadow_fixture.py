"""Trusted synthetic scenario and conservative virtual movement mapping."""
from __future__ import annotations

from dataclasses import dataclass
from importlib.metadata import distribution
import os
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

PHASES = frozenset({'vehicle_green', 'vehicle_yellow', 'pedestrian_green',
                    'pedestrian_flashing', 'all_red'})
PIN = '1.28.0'


def write_scenario(root: Path, *, controlled: bool = False) -> None:
    nodes = ET.Element('nodes')
    ET.SubElement(nodes, 'node', id='C', x='0', y='0', type='traffic_light')
    edges = ET.Element('edges')
    for name, x, y in [('W', -100, 0), ('E', 100, 0), ('N', 0, 100), ('S', 0, -100)]:
        ET.SubElement(nodes, 'node', id=name, x=str(x), y=str(y))
        for a, b in [(name, 'C'), ('C', name)]:
            ET.SubElement(edges, 'edge', {'id': a+b, 'from': a, 'to': b,
                          'numLanes': '1', 'speed': '10', 'sidewalkWidth': '2'})
    routes = ET.Element('routes')
    ET.SubElement(routes, 'vType', id='car', vClass='passenger', sigma='0.5')
    ET.SubElement(routes, 'route', id='we', edges='WC CE')
    alternate = 'ew' if controlled else 'ns'
    ET.SubElement(routes, 'route', id=alternate, edges='EC CW' if controlled else 'NC CS')
    for i in range(12):
        ET.SubElement(routes, 'vehicle', id=f'v{i}', type='car', route='we' if i % 2 == 0 else alternate, depart=str(i*5))
        person = ET.SubElement(routes, 'person', id=f'p{i}', depart=str(i*5))
        ET.SubElement(person, 'walk', edges='WC CN')
    for name, element in [('nodes.xml', nodes), ('edges.xml', edges), ('routes.xml', routes)]:
        ET.ElementTree(element).write(root / name, encoding='utf-8', xml_declaration=True)


@dataclass(frozen=True)
class PhaseMap:
    links: tuple[tuple[str, str, str], ...]
    vehicles: tuple[int, ...]
    pedestrians: tuple[int, ...]
    crossing_edges: frozenset[str]

    @classmethod
    def load(cls, path: Path) -> PhaseMap:
        network = ET.parse(path).getroot()
        external = {e.get('id') for e in network.findall('edge') if e.get('function') is None}
        crossings = frozenset(e.attrib['id'] for e in network.findall('edge') if e.get('function') == 'crossing')
        if external != {'WC', 'CW', 'EC', 'CE', 'NC', 'CN', 'SC', 'CS'} or len(crossings) != 4:
            raise ValueError('Unexpected shadow topology')
        connections = {}
        vehicles, pedestrians = [], []
        for c in network.findall('connection'):
            if c.get('tl') != 'C':
                continue
            idx = int(c.attrib['linkIndex'])
            if idx in connections:
                raise ValueError('Duplicate shadow link')
            a, b = c.attrib['from'], c.attrib['to']
            connections[idx] = (a + '_' + c.attrib['fromLane'], b + '_' + c.attrib['toLane'], c.get('via', ''))
            if (a, b) in {('WC', 'CE'), ('EC', 'CW')} and c.get('dir') == 's':
                vehicles.append(idx)
            if b in crossings:
                pedestrians.append(idx)
        if set(connections) != set(range(20)) or len(vehicles) != 2 or len(pedestrians) != 4:
            raise ValueError('Unexpected controlled links')
        foes = {int(r.attrib['index']): r.attrib['foes'][::-1]
                for r in network.findall("junction[@id='C']/request")}
        if set(foes) != set(connections) or any(len(bits) != 20 or set(bits) - {'0', '1'} for bits in foes.values()):
            raise ValueError('Missing conflict matrix')
        for group in (vehicles, pedestrians):
            if any(foes[a][b] != '0' for a in group for b in group if a != b):
                raise ValueError('Conflicting permissions')
        return cls(tuple(connections[i] for i in range(20)), tuple(sorted(vehicles)),
                   tuple(sorted(pedestrians)), crossings)

    def state(self, phase: str, *, vehicle_inside: bool, pedestrian_inside: bool) -> str:
        # Yellow/flashing/mixed/unknown phases grant no new shadow entry.
        allowed = self.vehicles if phase == 'vehicle_green' and not pedestrian_inside else (
            self.pedestrians if phase == 'pedestrian_green' and not vehicle_inside else ())
        return ''.join('G' if i in allowed else 'r' for i in range(len(self.links)))


def native_netconvert() -> Path:
    dist = distribution('eclipse-sumo')
    if dist.version != PIN:
        raise RuntimeError('Unexpected eclipse-sumo version')
    matches = [Path(dist.locate_file(f)).resolve() for f in (dist.files or ())
               if str(f).replace('\\', '/').endswith('sumo/bin/netconvert.exe')]
    if len(matches) != 1 or not matches[0].is_file():
        raise RuntimeError('Pinned Windows native netconvert unavailable')
    return matches[0]


def generate_controlled_fixture(root: Path) -> None:
    native = native_netconvert()
    binary = str(native)
    env = {**os.environ, "SUMO_HOME": str(native.parent.parent)}
    version = subprocess.run([binary, '--version'], cwd=root, env=env, capture_output=True, text=True, check=True, timeout=15)
    banner = version.stdout.splitlines()[0] if version.stdout else ''
    if banner.strip() not in (f'Eclipse SUMO netconvert {PIN}', f'Eclipse SUMO netconvert Version {PIN}'):
        raise RuntimeError('Unexpected netconvert version')
    write_scenario(root, controlled=True)
    subprocess.run([binary, '--node-files', 'nodes.xml', '--edge-files', 'edges.xml',
                    '--crossings.guess', 'true', '--output-file', 'network.xml'],
                   cwd=root, env=env, capture_output=True, check=True, timeout=15)
    PhaseMap.load(root / 'network.xml')
