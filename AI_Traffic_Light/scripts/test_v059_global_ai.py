"""Focused V059 tests: model upload, global settings and camera inference wiring."""
from __future__ import annotations

import asyncio
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "apps/pc-studio/backend"
FRONTEND = ROOT / "apps/pc-studio/frontend/src"
sys.path.insert(0, str(BACKEND))

from app.core.exceptions import AppError  # noqa: E402
from app.services.model_registry import ModelRegistryService  # noqa: E402
from app.services.runtime_settings import RuntimeSettingsService  # noqa: E402


async def chunks(data: bytes):
    yield data


def main() -> None:
    with TemporaryDirectory(prefix="aitl-v059-") as directory:
        path = Path(directory)
        settings = RuntimeSettingsService(settings_path=path / "settings.json")
        original = settings.get()
        assert original["inference_interval_ms"] == 500
        updated = settings.save({**original, "default_confidence": 0.65, "inference_interval_ms": 250})
        assert updated["inference_interval_ms"] == 250
        assert settings.get()["default_confidence"] == 0.65
        try:
            settings.save({**original, "inference_interval_ms": 50})
        except AppError as exc:
            assert exc.status_code == 422
        else:
            raise AssertionError("Unsupported inference interval accepted")

        registry = ModelRegistryService(output_root=path / "training")
        asyncio.run(registry.upload_model("imported_1", chunks(b"test-bytes")))
        assert (path / "training/imported_1/weights/best.pt").read_bytes() == b"test-bytes"
        try:
            asyncio.run(registry.upload_model("imported_1", chunks(b"overwrite")))
        except AppError as exc:
            assert exc.status_code == 409
        else:
            raise AssertionError("Existing imported model overwritten")
        assert (path / "training/imported_1/weights/best.pt").read_bytes() == b"test-bytes"
        try:
            asyncio.run(registry.upload_model("../escape", chunks(b"bad")))
        except AppError as exc:
            assert exc.status_code == 422
        else:
            raise AssertionError("Unsafe model ID accepted")

    nav = (FRONTEND / "constants/appNavigation.ts").read_text(encoding="utf-8")
    preview = (FRONTEND / "pages/LiveAiPage.tsx").read_text(encoding="utf-8")
    counts = (FRONTEND / "lib/regionCounts.ts").read_text(encoding="utf-8")
    api = (FRONTEND / "api.ts").read_text(encoding="utf-8")
    polling = (FRONTEND / "lib/useSerialPolling.ts").read_text(encoding="utf-8")
    assert nav.index('id: "traffic"') < nav.index('id: "ai"')
    assert "PAGE_DETAILS.settings" not in nav
    # V0563 retains the selected camera endpoint while adding scoped cancellation.
    assert "fetchCameraInference(sourceId, context.signal)" in preview
    guard = "if (!context.isCurrent() || next.source_id !== sourceId) return;"
    assert guard in preview and preview.index(guard) < preview.index("setFrame(next.frame)")
    assert "restartKey: JSON.stringify([sourceId, model?.active_model_id ?? null])" in preview
    assert "fetchCameraInference(sourceId: string, signal?: AbortSignal)" in api
    assert 'requestJsonStrict<CameraInferenceResult>(`${API_BASE}/api/inference/cameras/${encodeURIComponent(sourceId)}`, { signal })' in api
    assert "return () => scope.retire()" in polling
    assert "fetchCrosswalks()" in preview
    assert "regionClassCounts" in preview and "onConfidenceChange" not in preview
    assert "vertices_by_side?.[side]" in counts
    assert "pointInRegion(point, item.polygon)" in counts

    print("[PASS] global inference interval validation and persistence")
    print("[PASS] bounded model import prevents overwrite and invalid IDs")
    print("[PASS] region preview and Traffic-first sidebar wiring")


if __name__ == "__main__":
    main()
