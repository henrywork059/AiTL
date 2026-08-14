"""Filesystem-isolated checks for model registry listing, default selection, and deletion."""
from __future__ import annotations

from pathlib import Path
import sys
from tempfile import TemporaryDirectory

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "apps" / "pc-studio" / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from app.core.error_codes import ErrorCode  # noqa: E402
from app.core.exceptions import AppError  # noqa: E402
from app.services.model_registry import ModelRegistryService  # noqa: E402


def main() -> int:
    with TemporaryDirectory(prefix="aitl-model-registry-") as temporary_directory:
        output_root = Path(temporary_directory) / "outputs" / "training"
        model_a = output_root / "run_a" / "weights" / "best.pt"
        model_b = output_root / "run_b" / "weights" / "best.pt"
        model_a.parent.mkdir(parents=True)
        model_b.parent.mkdir(parents=True)
        model_a.write_bytes(b"aaa")
        model_b.write_bytes(b"bbb")

        service = ModelRegistryService(output_root=output_root)
        listed = service.status()
        assert listed["total"] == 2

        service.set_default_model("run_b")
        listed = service.status()
        assert listed["default_model_id"] == "run_b"
        assert any(item["model_id"] == "run_b" and item["is_default"] for item in listed["models"])

        service.delete_model("run_a")
        assert not (output_root / "run_a").exists()
        assert service.status()["total"] == 1

        try:
            service.delete_model("missing")
        except AppError as exc:
            assert exc.code == ErrorCode.MODEL_VERSION_NOT_FOUND
        else:
            raise AssertionError("Deleting a missing model should fail")

    print("[PASS] model registry lists discovered local runs")
    print("[PASS] default model selection is persisted")
    print("[PASS] deleting a model removes the run directory")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
