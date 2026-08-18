from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import threading
import time
from typing import Any


_REPLACE_LOCK = threading.RLock()
_REPLACE_RETRY_DELAYS_SECONDS = (0.01, 0.02, 0.05, 0.1)


def read_json(path: Path) -> Any:
    """Read one UTF-8 JSON document.

    Domain services remain responsible for mapping filesystem/JSON failures to
    their stable project error codes.
    """

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _replace_with_retry(temporary: Path, destination: Path) -> None:
    """Serialize final replacement and retry transient sharing violations.

    Windows may briefly reject concurrent ``os.replace`` calls targeting the
    same destination even when each writer uses its own temporary file. The
    lock covers only the final atomic replacement, while the bounded retries
    absorb short-lived sharing/antivirus/indexer interference. Persistent
    permission failures are still raised to the owning domain service.
    """

    with _REPLACE_LOCK:
        for attempt in range(len(_REPLACE_RETRY_DELAYS_SECONDS) + 1):
            try:
                os.replace(temporary, destination)
                return
            except PermissionError:
                if attempt >= len(_REPLACE_RETRY_DELAYS_SECONDS):
                    raise
                time.sleep(_REPLACE_RETRY_DELAYS_SECONDS[attempt])


def write_json_atomic(path: Path, payload: Any, *, indent: int = 2) -> None:
    """Atomically replace a JSON document without exposing a partial target file.

    A unique temporary file is created beside the destination so replacement
    stays on the same filesystem. The previous destination remains untouched if
    serialization or the temporary write fails. Concurrent in-process writers
    serialize only the final replacement step.
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
        _replace_with_retry(temporary, destination)
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
