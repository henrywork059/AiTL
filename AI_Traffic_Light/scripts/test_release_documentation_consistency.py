from __future__ import annotations

from pathlib import Path
import re

PROJECT_ROOT = Path(__file__).resolve().parents[1]
VERSION_PATTERN = re.compile(r"^\d+_\d+_\d+$")


def parse_version() -> dict[str, str]:
    fields: dict[str, str] = {}
    for raw in (PROJECT_ROOT / "VERSION").read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition(":")
        assert separator, f"invalid VERSION line: {raw!r}"
        fields[key.strip()] = value.strip()
    return fields


def require_token(path: Path, token: str, label: str) -> str:
    assert path.is_file(), f"missing {label}: {path.relative_to(PROJECT_ROOT)}"
    text = path.read_text(encoding="utf-8")
    assert token in text, f"{label} does not contain required token {token!r}: {path.relative_to(PROJECT_ROOT)}"
    return text


def main() -> int:
    fields = parse_version()
    current = fields["version"]
    previous = fields["previous_version"]
    baseline = fields["passed_baseline"]

    assert VERSION_PATTERN.fullmatch(current)
    assert VERSION_PATTERN.fullmatch(previous)
    assert VERSION_PATTERN.fullmatch(baseline)

    current_docs = {
        "START_HERE": PROJECT_ROOT / "docs" / "START_HERE.md",
        "LOCAL_TESTING": PROJECT_ROOT / "docs" / "LOCAL_TESTING.md",
        "TEST_READY_CHECKLIST": PROJECT_ROOT / "docs" / "TEST_READY_CHECKLIST.md",
    }
    for label, path in current_docs.items():
        text = require_token(path, current, label)
        assert baseline in text, f"{label} must disclose passed baseline {baseline}"

    start_text = current_docs["START_HERE"].read_text(encoding="utf-8")
    local_text = current_docs["LOCAL_TESTING"].read_text(encoding="utf-8")
    assert previous in start_text, f"START_HERE must identify previous version {previous}"
    assert previous in local_text, f"LOCAL_TESTING must identify previous version {previous}"

    patch = PROJECT_ROOT / "docs" / f"PATCH_{current}.md"
    patch_text = require_token(patch, current, "current patch document")
    assert baseline in patch_text, f"current patch document must disclose passed baseline {baseline}"

    changelog_text = (PROJECT_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert f"## {current}" in changelog_text, f"CHANGELOG missing current section {current}"

    frontend_version = (PROJECT_ROOT / "apps" / "pc-studio" / "frontend" / "src" / "constants" / "projectVersion.ts").read_text(encoding="utf-8")
    tokens = sorted(set(re.findall(r"\b\d+_\d+_\d+\b", frontend_version)))
    assert tokens == [current], f"frontend version source is not exactly current version: {tokens}"

    playbook = (PROJECT_ROOT / "docs" / "PATCH_PLAYBOOK.md").read_text(encoding="utf-8")
    assert "update root `VERSION` last" in playbook, "patch playbook must preserve release-bundle VERSION-last safeguard"
    assert "scripts/test_*.py" in playbook, "patch playbook must document automatic regression naming"
    assert "update_test_run.ps1" in playbook, "patch playbook must identify the normal owner validation command"

    workflow = (PROJECT_ROOT / "docs" / "DEVELOPMENT_WORKFLOW.md").read_text(encoding="utf-8")
    assert "VERSION` last" in workflow, "development workflow must preserve VERSION-last release ordering"
    assert "auto-discovers zero-argument `scripts/test_*.py`" in workflow, "development workflow must preserve automatic regression convention"

    architecture = (PROJECT_ROOT / "docs" / "ARCHITECTURE.md").read_text(encoding="utf-8")
    assert "FB1 + CAMERA_GRAB_LATEST" in architecture, "architecture must describe tuned production framebuffer/grab path"
    assert "2 PSRAM framebuffers" not in architecture, "durable architecture reintroduced obsolete two-framebuffer production claim"
    assert "JunctionNetworkOverviewService" in architecture, "architecture must document Junction Network projection ownership"

    print("[PASS] current candidate docs match VERSION / previous / passed baseline")
    print("[PASS] patch, changelog and frontend release surfaces are synchronized")
    print("[PASS] fast patch playbook preserves VERSION-last and auto-regression safeguards")
    print("[PASS] durable architecture matches FB1/LATEST production path and Junction Network ownership")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
