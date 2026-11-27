"""Fail-closed source/mode capture and AI workflow contracts for 0_5_75."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/pc-studio/backend"))

from app.core.error_codes import ErrorCode
from app.core.exceptions import AppError
from app.models import CaptureFrameRequest
from app.routes import dataset
from app.services.camera_frames import CameraFrame


def main():
    frame = CameraFrame(content=b"synthetic-bytes", content_type="image/png",
                        source_id="cam_source_a", width=1280, height=720,
                        received_at_ms=123456, frame_number=7, origin="upload")
    saved = SimpleNamespace(capture_id="saved_1", origin="upload",
                            to_dict=lambda: {"capture_id": "saved_1", "source_id": "cam_source_a", "origin": "upload"})
    request = SimpleNamespace(state=SimpleNamespace(request_id="req_source_guard"))
    with patch.object(dataset.camera_frame_service, "latest_frame", return_value=frame), patch.object(
            dataset.dataset_capture_service, "capture_frame", return_value=saved) as write:
        for source, origin in (("cam_source_b", "upload"), ("cam_source_a", "simulation")):
            try:
                dataset.capture_latest_frame(CaptureFrameRequest(session_id="guard_test",
                    expected_source_id=source, expected_origin=origin), request)
            except AppError as error:
                assert error.code == ErrorCode.CAMERA_NOT_CONNECTED and error.status_code == 409
            else:
                raise AssertionError("Capture accepted changed source/mode")
        write.assert_not_called()
        for payload in (CaptureFrameRequest(session_id="guard_test", expected_source_id="cam_source_a", expected_origin="upload"),
                        CaptureFrameRequest(session_id="guard_test")):
            result = dataset.capture_latest_frame(payload, request)
            assert result["data"]["source_id"] == "cam_source_a"
            assert result["meta"]["request_id"] == "req_source_guard"
        assert write.call_count == 2
    for source in ("", "x" * 161):
        try:
            CaptureFrameRequest(expected_source_id=source)
        except ValueError:
            pass
        else:
            raise AssertionError("Invalid source identity accepted")
    src = ROOT / "apps/pc-studio/frontend/src"
    capture = (src / "pages/DatasetCapturePage.tsx").read_text(encoding="utf-8")
    train = (src / "pages/TrainExportPage.tsx").read_text(encoding="utf-8")
    review = (src / "pages/DatasetReviewPage.tsx").read_text(encoding="utf-8")
    native = (src / "components/NativeProjectionView.tsx").read_text(encoding="utf-8")
    api = (src / "api.ts").read_text(encoding="utf-8")
    assert "expected_source_id: expectedSource, expected_origin: expectedOrigin" in capture
    assert "cameraStatus.active_source_id && cameraStatus.origin" in capture and "!cameraStatus.stale" in capture
    assert "fetchDatasetStatusStrict" in capture
    assert "fetchTrainingStatusStrict(signal)" in train and "fetchTrainingDatasetStatusStrict(signal)" in train
    assert "setStatus(null);" in train and "setManagedDataset(null);" in train
    assert "currentDataset.stale" in train and "currentDataset.ready" in train
    assert "if (!status.ready || status.stale" in review
    assert "fetchTrainingStatusStrict(signal?: AbortSignal)" in api
    assert "fetchTrainingDatasetStatusStrict(signal?: AbortSignal)" in api
    assert ":$"+"{sourceId}" in native and "key={" in native
    print("[PASS] Capture source/mode mismatch rejected before persistence; legacy callers unaffected")
    print("[PASS] Fail-closed training and dataset status, fresh readiness and source-scoped native view")


if __name__ == "__main__":
    main()
