"""CI-only diagnostic run of the S01 synthetic fixture; never imported by PC Studio."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET


def inspect_topology(network: Path, persons: Path) -> dict:
    net = ET.parse(network).getroot()
    edges = net.findall('edge')
    external = {e.attrib['id']: e for e in edges if not e.get('function')}
    expected = {'WC', 'CW', 'EC', 'CE', 'NC', 'CN', 'SC', 'CS'}
    crossings = {e.attrib['id'] for e in edges if e.get('function') == 'crossing'}
    sidewalks = {edge_id for edge_id, edge in external.items()
                 if any('pedestrian' in lane.get('allow', '').split() for lane in edge.findall('lane'))}
    signalized = any(j.get('id') == 'C' and j.get('type') == 'traffic_light'
                     for j in net.findall('junction')) and any(t.get('id') == 'C' for t in net.findall('tlLogic'))
    observed = set()
    crossed = set()
    for _, step in ET.iterparse(persons, events=('end',)):
        if step.tag == 'timestep':
            for person in step.findall('person'):
                observed.add(person.attrib['id'])
                if person.get('edge') in crossings:
                    crossed.add(person.attrib['id'])
            step.clear()
    expected_persons = {f'p{i}' for i in range(12)}
    passed = set(external) == expected and sidewalks == expected and signalized and bool(crossings) and observed == expected_persons and crossed == expected_persons
    return {'external_edges': sorted(external), 'sidewalk_edges': sorted(sidewalks),
            'signalized_center': signalized, 'crossing_edges': sorted(crossings),
            'observed_person_ids': sorted(observed), 'persons_observed_on_crossings': sorted(crossed),
            'topology_and_crossing_pass': passed}


def command(args: list[str], root: Path, name: str) -> None:
    result = subprocess.run(args, cwd=root, capture_output=True, text=True, timeout=120)
    (root / f'{name}.stdout.txt').write_text(result.stdout, encoding='utf-8')
    (root / f'{name}.stderr.txt').write_text(result.stderr, encoding='utf-8')
    result.check_returncode()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', required=True, type=Path)
    args = parser.parse_args()
    project = Path(__file__).resolve().parents[2] / 'AI_Traffic_Light'
    sys.path.insert(0, str(project / 'scripts'))
    from evaluate_simulation_engine import write_scenario, SEED, STEP, DURATION

    root = args.output_dir.resolve()
    root.mkdir(parents=True, exist_ok=False)
    sumo, netconvert = shutil.which('sumo'), shutil.which('netconvert')
    if not sumo or not netconvert:
        raise RuntimeError('Required SUMO executables not found')
    write_scenario(root)
    command([netconvert, '--node-files', 'nodes.xml', '--edge-files', 'edges.xml',
             '--crossings.guess', 'true', '--output-file', 'network.xml'], root, 'netconvert')
    command([sumo, '-n', 'network.xml', '-r', 'routes.xml', '--seed', str(SEED),
             '--step-length', str(STEP), '--end', str(DURATION), '--time-to-teleport', '-1',
             '--fcd-output', 'vehicles.xml', '--person-fcd-output', 'persons.xml',
             '--tripinfo-output', 'tripinfo.xml', '--collision-output', 'collisions.xml',
             '--no-step-log', 'true'], root, 'sumo')
    result = inspect_topology(root / 'network.xml', root / 'persons.xml')
    trips = ET.parse(root / 'tripinfo.xml').getroot()
    result['completed_vehicle_trips'] = len(trips.findall('tripinfo'))
    result['completed_person_trips'] = len(trips.findall('personinfo'))
    result['reported_collisions'] = len(ET.parse(root / 'collisions.xml').getroot().findall('collision'))
    result['status'] = 'pass' if result['topology_and_crossing_pass'] and result['reported_collisions'] == 0 else 'fail'
    result['evidence'] = 'executed synthetic diagnostic; not field data or safety certification'
    rendered = json.dumps(result, indent=2) + '\n'
    (root / 'topology-summary.json').write_text(rendered, encoding='utf-8')
    print(rendered, end='')
    return 0 if result['status'] == 'pass' else 1


if __name__ == '__main__':
    raise SystemExit(main())
