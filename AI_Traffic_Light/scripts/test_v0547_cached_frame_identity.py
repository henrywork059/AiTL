from __future__ import annotations

from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "apps" / "pc-studio" / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.services.camera_frames import CameraFrameService
from app.services import remote_camera_manager as rcm
from test_remote_camera_multi import FakeSession, jpeg


def main() -> int:
    frames = CameraFrameService()
    now = [10000]
    with tempfile.TemporaryDirectory() as directory, patch.object(rcm, "camera_frame_service", frames):
        manager = rcm.RemoteCameraManager(
            registry_path=Path(directory) / "cameras.json", session_factory=FakeSession
        )
        manager._now_ms = lambda: now[0]
        for source, host in (("cam_a", "192.168.1.81"), ("cam_b", "192.168.1.82")):
            manager.save_profile(source_id=source, host=host)
            manager.connect(source_id=source, host=host)
            manager.start_stream(settings=dict(rcm.DEFAULT_CAMERA_SETTINGS), target_fps=15)

        a, b = manager._sessions["cam_a"], manager._sessions["cam_b"]
        b.emit(1, jpeg(90))
        selected_b = frames.latest_frame()
        assert selected_b is not None and selected_b.source_id == "cam_b"
        assert selected_b.received_at_ms == 10000

        now[0] = 10020
        a.emit(1, jpeg(60))
        background_a = next(f for f in manager.frames_for_inference() if f.source_id == "cam_a")
        assert background_a.received_at_ms == 10020
        assert background_a.frame_number != selected_b.frame_number
        assert frames.latest_frame() is selected_b
        print("[PASS] background packet has distinct identity without replacing selected frame")

        now[0] = 10100
        manager.select("cam_a")
        assert frames.latest_frame() is background_a
        assert frames.latest_frame().received_at_ms == 10020
        assert manager.wait_for_new_frame(selected_b.frame_number, 0) is background_a
        assert manager.wait_for_new_frame(background_a.frame_number, 0) is None
        print("[PASS] promotion preserves receive time, identity and relay semantics")

        manager.select("cam_b")
        assert frames.latest_frame() is selected_b
        manager.select("cam_a")
        assert frames.latest_frame() is background_a
        assert manager.frame_for_preview("cam_a") is background_a
        print("[PASS] A/B/A replay retains the same observation across consumers")

        # A device sequence restart is not a globally reusable observation ID.
        a.emit(1, jpeg(61))
        newer = frames.latest_frame()
        assert newer is not None and newer.frame_number > background_a.frame_number
        assert newer.received_at_ms == 10100
        a.emit(2, jpeg(62))
        same_ms = frames.latest_frame()
        assert same_ms.received_at_ms == newer.received_at_ms
        assert same_ms.frame_number != newer.frame_number
        print("[PASS] distinct accepted packets receive distinct IDs even in the same millisecond")

        now[0] = 11000
        manager.select("cam_b")
        assert frames.latest_frame() is None
        print("[PASS] stale cache remains rejected")

        b.emit(2, jpeg(91))
        latest_b = frames.latest_frame()
        assert latest_b.source_id == "cam_b" and latest_b.received_at_ms == 11000
        now[0] = 11050
        # Model a simulation ownership transition without starting the renderer.
        frames._simulation_enabled = True
        manager.sync_after_simulation_change()
        assert frames._uploaded_frame is None
        frames._simulation_enabled = False
        manager.sync_after_simulation_change()
        assert frames.latest_frame() is latest_b
        print("[PASS] simulation return preserves fresh cached observation identity")

        uploaded = frames.store_upload(source_id="receiver", content_type="image/jpeg", content=jpeg(3))
        assert uploaded.frame_number > latest_b.frame_number and frames.latest_frame() is uploaded
        assert uploaded.origin == "upload"
        print("[PASS] ordinary HTTP upload still allocates and publishes a new frame")

        manager.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
