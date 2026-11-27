"""Discover and execute the same offline regressions on Windows and CI."""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys

EXCLUDED_TESTS = frozenset({
    "test_backend_smoke.py",
    "test_camera_transport_benchmark.py",
    "test_camera_transport_isolation.py",
})
PREFLIGHT_TESTS = frozenset({"test_update_test_run_script.py"})


def discover_tests(directory: Path, *, skip_preflight: bool = False) -> list[str]:
    excluded = EXCLUDED_TESTS | (PREFLIGHT_TESTS if skip_preflight else frozenset())
    return sorted(path.name for path in directory.glob("test_*.py")
                  if path.is_file() and path.name not in excluded)


def run_tests(directory: Path, *, focused: list[str] | None = None,
              skip_preflight: bool = False, list_only: bool = False) -> int:
    available = discover_tests(directory, skip_preflight=skip_preflight)
    if focused is not None:
        requested = set(focused) - (PREFLIGHT_TESTS if skip_preflight else frozenset())
        unknown = requested.difference(available)
        if unknown:
            raise ValueError("Unknown or excluded offline tests: " + ", ".join(sorted(unknown)))
        available = [name for name in available if name in requested]
    if list_only:
        for name in available:
            print(name)
        return 0
    print(f"Offline regressions selected: {len(available)}", flush=True)
    for name in available:
        print(f"=== Backend regression: {name} ===", flush=True)
        result = subprocess.run([sys.executable, str((directory / name).resolve())],
                                cwd=directory.parent, check=False)
        if result.returncode:
            print(f"Failed: {name} (exit {result.returncode})", file=sys.stderr, flush=True)
            return result.returncode if result.returncode > 0 else 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true", help="Print the selected test names only")
    parser.add_argument("--skip-preflight", action="store_true", help="Runner already ran preflight")
    parser.add_argument("--focused", nargs="*", default=None, help="Run only listed offline tests")
    args = parser.parse_args()
    try:
        return run_tests(Path(__file__).resolve().parent, focused=args.focused,
                         skip_preflight=args.skip_preflight, list_only=args.list)
    except ValueError as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
