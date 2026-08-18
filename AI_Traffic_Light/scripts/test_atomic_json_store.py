"""Focused regression checks for shared atomic JSON persistence."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "apps" / "pc-studio" / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from app.core import json_store  # noqa: E402
from app.core.json_store import read_json, write_json_atomic  # noqa: E402


def main() -> int:
    with TemporaryDirectory(prefix="aitl-json-store-") as temporary_directory:
        root = Path(temporary_directory)
        path = root / "nested" / "settings.json"

        write_json_atomic(path, {"version": 1, "name": "initial"})
        assert read_json(path) == {"version": 1, "name": "initial"}
        assert path.read_text(encoding="utf-8").endswith("\n")

        original = path.read_bytes()
        try:
            write_json_atomic(path, {"bad": object()})
        except TypeError:
            pass
        else:
            raise AssertionError("non-serializable payload unexpectedly succeeded")
        assert path.read_bytes() == original

        original_replace = json_store.os.replace
        replace_attempts = 0

        def transient_windows_replace(source: Path, destination: Path) -> None:
            nonlocal replace_attempts
            replace_attempts += 1
            if replace_attempts <= 2:
                raise PermissionError("simulated transient Windows sharing violation")
            original_replace(source, destination)

        with patch.object(json_store.os, "replace", side_effect=transient_windows_replace):
            write_json_atomic(path, {"retry": "succeeded"})
        assert replace_attempts == 3
        assert read_json(path) == {"retry": "succeeded"}

        with ThreadPoolExecutor(max_workers=8) as executor:
            list(executor.map(lambda writer_id: write_json_atomic(path, {"writer": writer_id}), range(32)))
        concurrent_result = read_json(path)
        assert isinstance(concurrent_result.get("writer"), int)
        assert 0 <= concurrent_result["writer"] < 32
        assert not list(path.parent.glob(f".{path.name}.*.tmp"))

        write_json_atomic(path, {"version": 2, "items": [1, 2, 3]})
        assert read_json(path) == {"version": 2, "items": [1, 2, 3]}
        assert not list(path.parent.glob(f".{path.name}.*.tmp"))

        path.write_text("{not-json", encoding="utf-8")
        try:
            read_json(path)
        except json.JSONDecodeError:
            pass
        else:
            raise AssertionError("invalid JSON did not raise JSONDecodeError")

    print("[PASS] atomic JSON writes replace complete documents and preserve prior data on serialization failure")
    print("[PASS] transient PermissionError during atomic replace is retried without corrupting the destination")
    print("[PASS] concurrent writers produce one complete document without temporary-name or replace collisions")
    print("[PASS] unique temporary files are cleaned and invalid JSON remains visible to domain error mapping")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
