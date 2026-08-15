from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

_VERSION_PATTERN = re.compile(r"^\d+_\d+_\d+$")
_REQUIRED_FIELDS = ("version", "status", "previous_version", "passed_baseline", "notes")
VERSION_FILE = Path(__file__).resolve().parents[5] / "VERSION"


@dataclass(frozen=True, slots=True)
class ProjectVersionInfo:
    """Validated project release metadata loaded from the root VERSION file."""

    version: str
    status: str
    previous_version: str
    passed_baseline: str
    notes: str


def _read_fields(path: Path) -> dict[str, str]:
    fields: dict[str, str] = {}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(f"Unable to read project VERSION file: {path}") from exc

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition(":")
        if not separator:
            raise RuntimeError(f"Invalid VERSION line without ':': {raw_line!r}")
        fields[key.strip()] = value.strip()
    return fields


def load_project_version(path: Path = VERSION_FILE) -> ProjectVersionInfo:
    """Load and validate the canonical release metadata for backend version surfaces."""
    fields = _read_fields(path)
    missing = [field for field in _REQUIRED_FIELDS if not fields.get(field)]
    if missing:
        raise RuntimeError(f"VERSION is missing required field(s): {', '.join(missing)}")

    for field in ("version", "previous_version", "passed_baseline"):
        value = fields[field]
        if not _VERSION_PATTERN.fullmatch(value):
            raise RuntimeError(f"VERSION field {field!r} has invalid underscore version: {value!r}")

    return ProjectVersionInfo(
        version=fields["version"],
        status=fields["status"],
        previous_version=fields["previous_version"],
        passed_baseline=fields["passed_baseline"],
        notes=fields["notes"],
    )


PROJECT_VERSION_INFO = load_project_version()
PROJECT_VERSION = PROJECT_VERSION_INFO.version
PROJECT_MODE = "cross_frame_tracking_and_flow_analytics_candidate"
