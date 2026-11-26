"""Locate the actual Windows SUMO distribution, not pip console launchers."""
from importlib.metadata import distribution
from pathlib import Path


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


if __name__ == '__main__':
    engine = distribution('eclipse-sumo')
    data = distribution('sumo-data')
    if engine.version != '1.28.0' or data.version != engine.version:
        raise RuntimeError('SUMO binary/data version mismatch')
    print(locate_native_bin(engine))
