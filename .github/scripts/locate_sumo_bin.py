"""Locate and verify the actual Windows SUMO distribution, not pip launchers."""
from importlib.metadata import distribution
from pathlib import Path
import argparse
import re
import subprocess

PINNED_VERSION = '1.28.0'


def locate_native_bin(dist) -> Path:
    candidates = {
        Path(dist.locate_file(file)).resolve().parent
        for file in (dist.files or ())
        if tuple(part.lower() for part in file.parts[-3:]) == ('sumo', 'bin', 'sumo.exe')
    }
    valid = [path for path in candidates if (path / 'sumo.exe').is_file() and (path / 'netconvert.exe').is_file()]
    if len(valid) != 1:
        raise RuntimeError(f'Expected one native SUMO binary directory; found {valid!r} from {candidates!r}')
    return valid[0]


def verify_version_banner(output: str, tool: str, expected: str = PINNED_VERSION) -> None:
    if tool not in {'sumo', 'netconvert'}:
        raise ValueError(f'Unsupported SUMO tool: {tool}')
    # Verify the first nonempty line only, not a version mentioned in license text.
    banner = next((line.strip() for line in output.splitlines() if line.strip()), '')
    pattern = rf'Eclipse SUMO {re.escape(tool)} (?:Version )?{re.escape(expected)}'
    if not re.fullmatch(pattern, banner):
        raise RuntimeError(f'Unexpected {tool} version banner: {banner!r}')


def verify_native_versions(bin_dir: Path) -> None:
    for tool in ('sumo', 'netconvert'):
        completed = subprocess.run([str(bin_dir / f'{tool}.exe'), '--version'],
                                   check=True, capture_output=True, text=True, timeout=30)
        print(completed.stdout, end='')
        verify_version_banner(completed.stdout, tool)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify-versions', action='store_true')
    args = parser.parse_args()
    engine = distribution('eclipse-sumo')
    data = distribution('sumo-data')
    if engine.version != PINNED_VERSION or data.version != engine.version:
        raise RuntimeError('SUMO binary/data version mismatch')
    bin_dir = locate_native_bin(engine)
    if args.verify_versions:
        verify_native_versions(bin_dir)
    else:
        print(bin_dir)
