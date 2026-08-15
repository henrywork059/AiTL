from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

VERSION_PATTERN = re.compile(r"^\d+_\d+_\d+$")
VERSION_TOKEN_PATTERN = re.compile(r"\b\d+_\d+_\d+\b")
REQUIRED_VERSION_FIELDS = ("version", "status", "previous_version", "passed_baseline", "notes")

REQUIRED_PATHS = (
    "AGENTS.md",
    "VERSION",
    "CHANGELOG.md",
    "README.md",
    "apps/pc-studio/backend/app/main.py",
    "apps/pc-studio/backend/app/core/project_version.py",
    "apps/pc-studio/backend/app/routes/health.py",
    "apps/pc-studio/backend/app/services/smoke_test.py",
    "apps/pc-studio/backend/app/services/template_state.py",
    "apps/pc-studio/backend/app/services/traffic_history.py",
    "apps/pc-studio/backend/app/services/traffic_recorder.py",
    "apps/pc-studio/backend/app/services/traffic_logic.py",
    "apps/pc-studio/frontend/src/App.tsx",
    "apps/pc-studio/frontend/src/api.ts",
    "apps/pc-studio/frontend/src/pages/DashboardPage.tsx",
    "apps/pc-studio/frontend/src/pages/TrafficAnalyticsPage.tsx",
    "apps/pc-studio/frontend/src/components/TrafficHistoryChart.tsx",
    "apps/pc-studio/frontend/src/constants/appNavigation.ts",
    "apps/pc-studio/frontend/src/constants/projectVersion.ts",
    "apps/device-camera/esp32-cam/src/main.cpp",
    "packages/schema/detection-frame.schema.json",
    "packages/schema/zones.schema.json",
    "docs/START_HERE.md",
    "docs/AI_AGENT_GUIDE.md",
    "docs/AI_AGENT_CHECKLIST.md",
    "docs/CODE_STRUCTURE.md",
    "docs/DEVELOPMENT_WORKFLOW.md",
    "docs/LOCAL_TESTING.md",
    "docs/TEST_READY_CHECKLIST.md",
    "docs/VERSIONING.md",
    "scripts/validate_patch_zip.py",
)

BACKEND_VERSION_SURFACES = (
    "apps/pc-studio/backend/app/main.py",
    "apps/pc-studio/backend/app/routes/health.py",
    "apps/pc-studio/backend/app/services/smoke_test.py",
    "apps/pc-studio/backend/app/services/template_state.py",
)

FRONTEND_VERSION_SOURCE = "apps/pc-studio/frontend/src/constants/projectVersion.ts"
FRONTEND_VERSION_SURFACES = (
    "apps/pc-studio/frontend/src/api.ts",
    "apps/pc-studio/frontend/src/pages/DashboardPage.tsx",
    "apps/pc-studio/frontend/src/constants/appNavigation.ts",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate AiTL repository structure and release-version consistency.")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="AI_Traffic_Light project root (defaults to the repository copy containing this script).",
    )
    return parser.parse_args()


def parse_version_file(path: Path) -> dict[str, str]:
    fields: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition(":")
        if not separator:
            raise ValueError(f"Invalid VERSION line without ':': {raw_line!r}")
        fields[key.strip()] = value.strip()
    return fields


def add_error(errors: list[str], message: str) -> None:
    errors.append(message)


def validate_required_paths(root: Path, errors: list[str]) -> None:
    for relative_path in REQUIRED_PATHS:
        if not (root / relative_path).exists():
            add_error(errors, f"Missing required path: {relative_path}")


def validate_version(root: Path, errors: list[str]) -> dict[str, str]:
    version_path = root / "VERSION"
    if not version_path.exists():
        return {}

    try:
        fields = parse_version_file(version_path)
    except (OSError, ValueError) as exc:
        add_error(errors, f"Unable to parse VERSION: {exc}")
        return {}

    missing = [field for field in REQUIRED_VERSION_FIELDS if not fields.get(field)]
    if missing:
        add_error(errors, f"VERSION missing required field(s): {', '.join(missing)}")
        return fields

    for field in ("version", "previous_version", "passed_baseline"):
        if not VERSION_PATTERN.fullmatch(fields[field]):
            add_error(errors, f"VERSION field {field!r} is invalid: {fields[field]!r}")

    if fields["version"] != fields["passed_baseline"] and "candidate" not in fields["status"].lower():
        add_error(
            errors,
            "Current version differs from passed_baseline but VERSION status does not identify the release as a candidate.",
        )

    patch_doc = root / "docs" / f"PATCH_{fields['version']}.md"
    if not patch_doc.exists():
        add_error(errors, f"Missing current patch document: docs/{patch_doc.name}")

    changelog = root / "CHANGELOG.md"
    if changelog.exists() and f"## {fields['version']}" not in changelog.read_text(encoding="utf-8"):
        add_error(errors, f"CHANGELOG.md has no section for {fields['version']}")

    return fields


def validate_backend_version_source(root: Path, errors: list[str]) -> None:
    for relative_path in BACKEND_VERSION_SURFACES:
        path = root / relative_path
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        literals = sorted(set(VERSION_TOKEN_PATTERN.findall(text)))
        if literals:
            add_error(
                errors,
                f"Backend version surface must use project_version metadata, not literal release token(s): "
                f"{relative_path}: {literals}",
            )
        if "PROJECT_VERSION" not in text:
            add_error(errors, f"Backend version surface does not reference PROJECT_VERSION: {relative_path}")


def validate_frontend_version_surfaces(root: Path, current_version: str, errors: list[str]) -> None:
    if not current_version:
        return

    source_path = root / FRONTEND_VERSION_SOURCE
    if source_path.exists():
        source_text = source_path.read_text(encoding="utf-8")
        source_tokens = sorted(set(VERSION_TOKEN_PATTERN.findall(source_text)))
        if source_tokens != [current_version]:
            add_error(
                errors,
                f"Frontend projectVersion source must contain only current version {current_version}: "
                f"{FRONTEND_VERSION_SOURCE}: {source_tokens}",
            )

    for relative_path in FRONTEND_VERSION_SURFACES:
        path = root / relative_path
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        tokens = sorted(set(VERSION_TOKEN_PATTERN.findall(text)))
        if tokens:
            add_error(
                errors,
                f"Frontend version surface must use shared PROJECT_VERSION metadata, not literal token(s): "
                f"{relative_path}: {tokens}",
            )
        if "PROJECT_VERSION" not in text:
            add_error(errors, f"Frontend version surface does not reference shared PROJECT_VERSION metadata: {relative_path}")


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    errors: list[str] = []

    validate_required_paths(root, errors)
    fields = validate_version(root, errors)
    validate_backend_version_source(root, errors)
    validate_frontend_version_surfaces(root, fields.get("version", ""), errors)

    if errors:
        print("AiTL structure/version validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("AiTL structure/version validation OK")
    if fields:
        print(
            f"version={fields['version']} status={fields['status']} "
            f"passed_baseline={fields['passed_baseline']}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
