"""Optional, isolated SUMO evaluation; shared pure fixture builder, no installation."""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import shutil
import subprocess
import tempfile
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'apps/pc-studio/backend'))
from app.services.sumo_shadow_fixture import write_scenario

SEED = 42
STEP = 0.2
DURATION = 180


def trace_summary(path: Path, kind: str) -> dict:
    # Canonicalize samples, not XML headers with timestamps/absolute paths.
    digest = hashlib.sha256()
    ids: set[str] = set()
    samples = 0
    last = -1.0
    for _, element in ET.iterparse(path, events=('end',)):
        if element.tag != 'timestep':
            continue
        stamp = float(element.attrib['time'])
        if stamp <= last:
            raise ValueError('trace time is not strictly increasing')
        last = stamp
        rows = []
        for agent in element.findall(kind):
            agent_id = agent.attrib['id']
            ids.add(agent_id)
            rows.append((agent_id, agent.attrib['x'], agent.attrib['y'], agent.attrib.get('speed')))
        samples += len(rows)
        digest.update(json.dumps([stamp, sorted(rows)], separators=(',', ':')).encode() + b'\n')
        element.clear()
    if not ids:
        raise ValueError(f'no {kind} observations')
    return {'sha256': digest.hexdigest(), 'observed_agents': len(ids), 'samples': samples, 'last_time_s': last}


def invoke(args: list[str], root: Path) -> float:
    start = time.perf_counter()
    subprocess.run(args, cwd=root, check=True, timeout=120, capture_output=True, text=True)
    return round(time.perf_counter() - start, 6)


def evaluate() -> dict:
    result = {'schema_version': 1, 'evidence': 'synthetic simulation evaluation', 'platform': platform.platform(),
              'seed': SEED, 'step_s': STEP, 'duration_s': DURATION, 'runs': []}
    binaries = {name: shutil.which(name) for name in ('sumo', 'netconvert')}
    missing = [name for name, path in binaries.items() if not path]
    if missing:
        return {**result, 'status': 'blocked', 'reason': 'Missing executables on PATH: ' + ', '.join(missing)}
    try:
        with tempfile.TemporaryDirectory(prefix='mesh-sumo-eval-') as directory:
            root = Path(directory)
            result['engine_version'] = subprocess.run([binaries['sumo'], '--version'], cwd=root,
                check=True, capture_output=True, text=True, timeout=15).stdout.splitlines()[0]
            write_scenario(root)
            invoke([binaries['netconvert'], '--node-files', 'nodes.xml', '--edge-files', 'edges.xml',
                    '--crossings.guess', 'true', '--output-file', 'network.xml'], root)
            for index in range(2):
                vehicle_file = f'vehicles-{index}.xml'
                person_file = f'persons-{index}.xml'
                elapsed = invoke([binaries['sumo'], '-n', 'network.xml', '-r', 'routes.xml', '--seed', str(SEED),
                    '--step-length', str(STEP), '--end', str(DURATION), '--time-to-teleport', '-1',
                    '--fcd-output', vehicle_file, '--person-fcd-output', person_file, '--no-step-log', 'true'], root)
                result['runs'].append({'wall_s': elapsed, 'vehicles': trace_summary(root / vehicle_file, 'vehicle'),
                                       'persons': trace_summary(root / person_file, 'person')})
            a, b = result['runs']
            repeatable = all(a[k] == b[k] and a[k]['observed_agents'] == 12 for k in ('vehicles', 'persons'))
            return {**result, 'status': 'pass' if repeatable else 'fail', 'same_seed_trace_match': repeatable}
    except (OSError, subprocess.SubprocessError, ValueError, ET.ParseError, KeyError, IndexError) as error:
        return {**result, 'status': 'fail', 'reason': str(error), 'stderr': str(getattr(error, 'stderr', '') or '')[-2000:]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, help='Optional JSON evidence file; defaults to stdout only.')
    args = parser.parse_args()
    result = evaluate()
    rendered = json.dumps(result, indent=2) + '\n'
    if args.output:
        args.output.write_text(rendered, encoding='utf-8')
    print(rendered, end='')
    return {'pass': 0, 'blocked': 2, 'fail': 1}[result['status']]


if __name__ == '__main__':
    raise SystemExit(main())
