"""Regression checks for changed-file startup selection."""
from select_changed_tests import select

P = "AI_Traffic_Light/"
TESTS = [
    "test_remote_camera_multi.py", "test_camera_frame_service.py",
    "test_signal_rules_service.py", "test_network_policy_arbiter.py",
    "test_dataset_capture_service.py", "test_frontend_polling_structure.py",
    "test_junction_network_frontend_structure.py", "test_update_test_run_script.py",
    "test_select_changed_tests.py", "test_backend_smoke.py",
]


def main() -> int:
    camera = select([P + "apps/pc-studio/backend/app/services/remote_camera_manager.py"], TESTS)
    assert not camera["all"] and "test_remote_camera_multi.py" in camera["tests"]
    assert "test_signal_rules_service.py" not in camera["tests"]
    assert not camera["frontend"]

    frontend = select([P + "apps/pc-studio/frontend/src/pages/LiveAiPage.tsx"], TESTS)
    assert frontend["frontend"] and not frontend["all"]
    assert frontend["tests"] == ["test_frontend_polling_structure.py"]

    docs = select([P + "docs/PATCH_0_3_16.md", P + "VERSION"], TESTS)
    assert not docs["all"] and docs["tests"] == [] and not docs["frontend"]

    edited_test = select([P + "scripts/test_signal_rules_service.py"], TESTS)
    assert edited_test["tests"] == ["test_signal_rules_service.py"]

    shared = select([P + "apps/pc-studio/backend/app/core/api_response.py"], TESTS)
    assert shared["all"]
    assert select([P + "packages/schema/detection-frame.schema.json"], TESTS)["all"]
    assert select([], TESTS)["all"]

    combined = select([
        P + "apps/pc-studio/backend/app/services/signal_rules.py",
        P + "apps/pc-studio/frontend/src/pages/JunctionNetworkPage.tsx",
    ], TESTS)
    assert not combined["all"] and combined["frontend"]
    assert "test_signal_rules_service.py" in combined["tests"]
    assert "test_junction_network_frontend_structure.py" in combined["tests"]

    manifest = select([P + "apps/pc-studio/frontend/package.json"], TESTS)
    assert manifest["all"] and manifest["frontend"]

    print("[PASS] changed-test selector targets related regressions and falls back safely")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
