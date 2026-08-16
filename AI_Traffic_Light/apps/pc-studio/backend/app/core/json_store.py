from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
from typing import Any


def read_json(path: Path) -> Any:
    """Read one UTF-8 JSON document.

    Domain services remain responsible for mapping filesystem/JSON failures to
    their stable project error codes.
    """

    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json_atomic(path: Path, payload: Any, *, indent: int = 2) -> None:
    """Atomically replace a JSON document without exposing a partial target file.

    A unique temporary file is created beside the destination so `os.replace`
    stays on the same filesystem. The previous destination remains untouched if
    serialization or the temporary write fails.
    """

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.",
        suffix=".tmp",
        dir=destination.parent,
    )
    temporary = Path(temporary_name)

    descriptor_open = True
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            descriptor_open = False
            json.dump(payload, handle, indent=indent, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
    except Exception:
        if descriptor_open:
            try:
                os.close(descriptor)
            except OSError:
                pass
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise
