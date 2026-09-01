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
    "apps/pc-studio/backend/app/core/json_store.py",
    "apps/pc-studio/backend/app/routes/health.py",
    "apps/pc-studio/backend/app/services/smoke_test.py",
    "apps/pc-studio/backend/app/services/template_state.py",
    "apps/pc-studio/backend/app/services/traffic_history.py",
    "apps/pc-studio/backend/app/services/traffic_flow.py",
    "apps/pc-studio/backend/app/services/object_tracking.py",
    "apps/pc-studio/backend/app/services/traffic_recorder.py",
    "apps/pc-studio/backend/app/services/traffic_logic.py",
    "apps/pc-studio/backend/app/services/signal_rules.py",
    "apps/pc-studio/backend/app/services/intersection_network.py",
    "apps/pc-studio/backend/app/services/junction_network_overview.py",
    "apps/pc-studio/frontend/src/App.tsx",
    "apps/pc-studio/frontend/src/styles.css",
    "apps/pc-studio/frontend/src/styles/tokens.css",
    "apps/pc-studio/frontend/src/styles/base.css",
    "apps/pc-studio/frontend/src/styles/layout.css",
    "apps/pc-studio/frontend/src/styles/components.css",
    "apps/pc-studio/frontend/src/api.ts",
    "apps/pc-studio/frontend/src/lib/useSerialPolling.ts",
    "apps/pc-studio/frontend/src/lib/junctionNetworkApi.ts",
    "apps/pc-studio/frontend/src/lib/junctionNetworkView.ts",
    "apps/pc-studio/frontend/src/pages/DashboardPage.tsx",
    "apps/pc-studio/frontend/src/pages/TrafficAnalyticsPage.tsx",
    "apps/pc-studio/frontend/src/pages/TrafficLogicPage.tsx",
    "apps/pc-studio/frontend/src/pages/JunctionNetworkPage.tsx",
    "apps/pc-studio/frontend/src/pages/signalRules.css",
    "apps/pc-studio/frontend/src/components/TrafficHistoryChart.tsx",
    "apps/pc-studio/frontend/src/components/TrafficFlowChart.tsx",
    "apps/pc-studio/frontend/src/components/junctions/JunctionNodeCard.tsx",
    "apps/pc-studio/frontend/src/constants/appNavigation.ts",
    "apps/pc-studio/frontend/src/constants/projectVersion.ts",
    "apps/device-camera/esp32-cam/src/main.cpp",
    "packages/schema/detection-frame.schema.json",
    "packages/schema/zones.schema.json",
    "docs/START_HERE.md",
    "docs/DOCUMENTATION_MAP.md",
    "docs/PROJECT_SCOPE.md",
    "docs/ARCHITECTURE.md",
    "docs/PATCH_PLAYBOOK.md",
    "docs/AI_AGENT_GUIDE.md",
    "docs/AI_AGENT_CHECKLIST.md",
    "docs/CODE_STRUCTURE.md",
    "docs/DEVELOPMENT_WORKFLOW.md",
    "docs/PC_STUDIO_DESIGN_SYSTEM.md",
    "docs/LOCAL_TESTING.md",
    "docs/TEST_READY_CHECKLIST.md",
    "docs/VERSIONING.md",
    "scripts/validate_patch_zip.py",
    "scripts/test_atomic_json_store.py",
    "scripts/test_frontend_polling_structure.py",
    "scripts/test_junction_network_frontend_structure.py",
    "scripts/test_junction_network_overview.py",
    "scripts/update_test_run.ps1",
    "scripts/test_update_test_run_script.py",
    "scripts/test_object_tracking_flow.py",
    "scripts/test_signal_rules_service.py",
)

BACKEND_VERSION_SURFACES = (
    "apps/pc-studio/backend/app/main.py",
    "apps/pc-studio/backend/app/routes/health.py",
    "apps/pc-studio/backend/app/services/smoke_test.py",
    "apps/pc-studio/backend/app/services/template_state.py",
)

FRONTEND_VERSION_SOURCE = "apps/pc-studio/frontend/src/constants/projectVersion.ts"

CURRENT_CANDIDATE_DOCS = (
    "docs/START_HERE.md",
    "docs/LOCAL_TESTING.md",
    "docs/TEST_READY_CHECKLIST.md",
)

FRONTEND_STYLE_ENTRYPOINT = "apps/pc-studio/frontend/src/styles.css"
REQUIRED_STYLE_IMPORTS = (
    './styles/tokens.css',
    './styles/base.css',
    './styles/layout.css',
    './styles/components.css',
)
FRONTEND_VERSION_SURFACES = (
    "apps/pc-studio/frontend/src/api.ts",
    "apps/pc-studio/frontend/src/pages/DashboardPage.tsx",
    "apps/pc-studio/frontend/src/constants/appNavigation.ts",
)

ATOMIC_JSON_SERVICES = (
    "apps/pc-studio/backend/app/services/runtime_settings.py",
    "apps/pc-studio/backend/app/services/zones.py",
    "apps/pc-studio/backend/app/services/model_registry.py",
    "apps/pc-studio/backend/app/services/intersection_network.py",
)

SERIAL_POLLING_SURFACES = (
    "apps/pc-studio/frontend/src/App.tsx",
    "apps/pc-studio/frontend/src/pages/JunctionNetworkPage.tsx",
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
        add_error(errors, "Current version differs from passed_baseline but VERSION status does not identify the release as a candidate.")
    patch_doc = root / "docs" / f"PATCH_{fields['version']}.md"
    if not patch_doc.exists():
        add_error(errors, f"Missing current patch document: docs/{patch_doc.name}")
    changelog = root / "CHANGELOG.md"
    if changelog.exists() and f"## {fields['version']}" not in changelog.read_text(encoding="utf-8"):
        add_error(errors, f"CHANGELOG.md has no section for {fields['version']}")
    return fields


def validate_current_candidate_docs(root: Path, fields: dict[str, str], errors: list[str]) -> None:
    current = fields.get("version", "")
    previous = fields.get("previous_version", "")
    baseline = fields.get("passed_baseline", "")
    if not current or not previous or not baseline:
        return

    for relative_path in CURRENT_CANDIDATE_DOCS:
        path = root / relative_path
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        if current not in text:
            add_error(errors, f"Current-candidate document does not identify {current}: {relative_path}")
        if baseline not in text:
            add_error(errors, f"Current-candidate document does not disclose passed baseline {baseline}: {relative_path}")

    for relative_path in ("docs/START_HERE.md", "docs/LOCAL_TESTING.md"):
        path = root / relative_path
        if path.exists() and previous not in path.read_text(encoding="utf-8"):
            add_error(errors, f"Current-candidate document does not identify previous version {previous}: {relative_path}")

    patch_path = root / "docs" / f"PATCH_{current}.md"
    if patch_path.exists():
        patch_text = patch_path.read_text(encoding="utf-8")
        if current not in patch_text:
            add_error(errors, f"Current patch document does not identify {current}: docs/{patch_path.name}")
        if baseline not in patch_text:
            add_error(errors, f"Current patch document does not disclose passed baseline {baseline}: docs/{patch_path.name}")


def validate_durable_workflow_guards(root: Path, errors: list[str]) -> None:
    playbook = root / "docs/PATCH_PLAYBOOK.md"
    if playbook.exists():
        text = playbook.read_text(encoding="utf-8")
        for marker, message in (
            ("update root `VERSION` last", "Patch playbook must preserve the VERSION-last release safeguard."),
            ("scripts/test_*.py", "Patch playbook must document automatic regression naming."),
            ("update_test_run.ps1", "Patch playbook must identify the normal owner validation command."),
        ):
            if marker not in text:
                add_error(errors, message)

    workflow = root / "docs/DEVELOPMENT_WORKFLOW.md"
    if workflow.exists():
        text = workflow.read_text(encoding="utf-8")
        if "VERSION` last" not in text:
            add_error(errors, "Development workflow must preserve VERSION-last release ordering.")
        if "auto-discovers zero-argument `scripts/test_*.py`" not in text:
            add_error(errors, "Development workflow must preserve automatic regression discovery guidance.")

    architecture = root / "docs/ARCHITECTURE.md"
    if architecture.exists():
        text = architecture.read_text(encoding="utf-8")
        if "FB1 + CAMERA_GRAB_LATEST" not in text:
            add_error(errors, "Durable architecture must describe the tuned FB1 + CAMERA_GRAB_LATEST production camera path.")
        if "2 PSRAM framebuffers" in text:
            add_error(errors, "Durable architecture reintroduced the obsolete two-framebuffer production claim.")
        if "JunctionNetworkOverviewService" not in text:
            add_error(errors, "Durable architecture must document JunctionNetworkOverviewService ownership.")


def validate_backend_version_source(root: Path, errors: list[str]) -> None:
    for relative_path in BACKEND_VERSION_SURFACES:
        path = root / relative_path
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        literals = sorted(set(VERSION_TOKEN_PATTERN.findall(text)))
        if literals:
            add_error(errors, f"Backend version surface must use project_version metadata, not literal release token(s): {relative_path}: {literals}")
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
            add_error(errors, f"Frontend projectVersion source must contain only current version {current_version}: {FRONTEND_VERSION_SOURCE}: {source_tokens}")
    for relative_path in FRONTEND_VERSION_SURFACES:
        path = root / relative_path
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        tokens = sorted(set(VERSION_TOKEN_PATTERN.findall(text)))
        if tokens:
            add_error(errors, f"Frontend version surface must use shared PROJECT_VERSION metadata, not literal token(s): {relative_path}: {tokens}")
        if "PROJECT_VERSION" not in text:
            add_error(errors, f"Frontend version surface does not reference shared PROJECT_VERSION metadata: {relative_path}")


def validate_frontend_style_system(root: Path, errors: list[str]) -> None:
    entrypoint = root / FRONTEND_STYLE_ENTRYPOINT
    if not entrypoint.exists():
        return
    text = entrypoint.read_text(encoding="utf-8")
    for relative_import in REQUIRED_STYLE_IMPORTS:
        if f'@import "{relative_import}";' not in text:
            add_error(errors, f"Frontend style entrypoint is missing required import: {relative_import}")
    if "gradient(" in text.lower():
        add_error(errors, "Frontend shared style entrypoint must not contain decorative gradient styling; use the design-system layers/tokens.")

    token_path = root / "apps/pc-studio/frontend/src/styles/tokens.css"
    if token_path.exists():
        token_text = token_path.read_text(encoding="utf-8")
        required_tokens = (
            "--color-canvas",
            "--color-surface",
            "--color-text-primary",
            "--color-primary",
            "--color-on-primary",
            "--color-secondary",
            "--color-on-secondary",
            "--color-accent",
            "--color-success",
            "--color-warning",
            "--color-danger",
            "--color-dark-surface-0",
            "--color-dark-surface-1",
            "--color-dark-surface-2",
            "--color-dark-surface-4",
            "--color-dark-surface-8",
        )
        for token in required_tokens:
            if token not in token_text:
                add_error(errors, f"Frontend design tokens are missing required role: {token}")
        if "color-scheme: light dark" not in token_text or "prefers-color-scheme: dark" not in token_text:
            add_error(errors, "Frontend design tokens must preserve system-adaptive light/dark appearance support.")
        if "--color-dark-surface-0: #121212;" not in token_text:
            add_error(errors, "Frontend dark design tokens must preserve the Material-derived #121212 base surface.")

    signal_css = root / "apps/pc-studio/frontend/src/pages/signalRules.css"
    if signal_css.exists():
        signal_text = signal_css.read_text(encoding="utf-8")
        if re.search(r"#[0-9a-fA-F]{3,8}\b", signal_text):
            add_error(errors, "Traffic Logic page CSS must consume shared color tokens instead of page-local hex colors.")


def validate_frontend_presentation_copy(root: Path, errors: list[str]) -> None:
    stale_text = {
        "apps/pc-studio/frontend/src/layout/AppShell.tsx": ("Confirm layout first",),
        "apps/pc-studio/frontend/src/pages/DashboardPage.tsx": ("traffic analytics + counting regions candidate",),
        "apps/pc-studio/frontend/src/pages/LiveAiPage.tsx": ("in 0_2_0",),
    }
    for relative_path, forbidden_phrases in stale_text.items():
        path = root / relative_path
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8")
        for phrase in forbidden_phrases:
            if phrase in content:
                add_error(errors, f"Frontend working-page copy contains stale development text in {relative_path}: {phrase!r}")

    components = root / "apps/pc-studio/frontend/src/styles/components.css"
    if components.exists():
        content = components.read_text(encoding="utf-8")
        neutral_marker = ".status-pill,"
        if neutral_marker not in content or "background: var(--color-surface-muted);" not in content:
            add_error(errors, "Generic status pills must remain neutral; semantic status colors require explicit status classes.")


def validate_atomic_json_persistence(root: Path, errors: list[str]) -> None:
    helper = root / "apps/pc-studio/backend/app/core/json_store.py"
    if helper.exists():
        helper_text = helper.read_text(encoding="utf-8")
        for required in ("tempfile.mkstemp", "os.fsync", "os.replace", "_REPLACE_LOCK", "PermissionError", "time.sleep"):
            if required not in helper_text:
                add_error(errors, f"Atomic JSON helper is missing required operation: {required}")

    for relative_path in ATOMIC_JSON_SERVICES:
        path = root / relative_path
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        if "write_json_atomic" not in text:
            add_error(errors, f"Persistent JSON service must use shared atomic writer: {relative_path}")
        if '.with_suffix(".tmp")' in text or ".with_suffix('.tmp')" in text:
            add_error(errors, f"Persistent JSON service reintroduces a shared fixed .tmp path: {relative_path}")
        if "write_text(json.dumps" in text:
            add_error(errors, f"Persistent JSON service bypasses the shared atomic writer: {relative_path}")


def validate_frontend_polling(root: Path, errors: list[str]) -> None:
    hook = root / "apps/pc-studio/frontend/src/lib/useSerialPolling.ts"
    if hook.exists():
        hook_text = hook.read_text(encoding="utf-8")
        if "window.setTimeout" not in hook_text or "finally" not in hook_text:
            add_error(errors, "Serial polling hook must schedule the next poll after the previous async task settles.")
        if "window.setInterval" in hook_text:
            add_error(errors, "Serial polling hook must not use setInterval because async polls may overlap.")

    for relative_path in SERIAL_POLLING_SURFACES:
        path = root / relative_path
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        if "useSerialPolling" not in text:
            add_error(errors, f"High-frequency frontend surface must use serial polling helper: {relative_path}")
        if "window.setInterval" in text:
            add_error(errors, f"High-frequency frontend surface must not use overlapping setInterval polling: {relative_path}")


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    errors: list[str] = []
    validate_required_paths(root, errors)
    fields = validate_version(root, errors)
    validate_current_candidate_docs(root, fields, errors)
    validate_durable_workflow_guards(root, errors)
    validate_backend_version_source(root, errors)
    validate_frontend_version_surfaces(root, fields.get("version", ""), errors)
    validate_frontend_style_system(root, errors)
    validate_frontend_presentation_copy(root, errors)
    validate_atomic_json_persistence(root, errors)
    validate_frontend_polling(root, errors)
    if errors:
        print("AiTL structure/version validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("AiTL structure/version validation OK")
    if fields:
        print(f"version={fields['version']} status={fields['status']} passed_baseline={fields['passed_baseline']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())