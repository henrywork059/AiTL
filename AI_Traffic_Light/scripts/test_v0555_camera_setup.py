"""V0555 connection/setup regression; uses fake HTTP responses, not ESP hardware."""
from __future__ import annotations

from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/pc-studio/backend"))

from app.core.error_codes import ErrorCode
from app.core.exceptions import AppError
from app.services.remote_camera import CAMERA_PROTOCOL, FRAME_PROTOCOL, RemoteCameraService
from app.services.remote_camera_manager import RemoteCameraManager, DEFAULT_CAMERA_SETTINGS


def must_reject(action, code):
    try:
        action()
    except AppError as exc:
        assert exc.code == code, (exc.code, code)
    else:
        raise AssertionError("Expected invalid camera setup to be rejected")


def main():
    with TemporaryDirectory() as tmp:
        registry = Path(tmp) / "remote_cameras.json"
        calls = []
        reachable = False

        def requester(host, path, method, query):
            calls.append((host, path, method))
            if path == "/status" and not reachable:
                raise AppError(ErrorCode.CAMERA_NOT_CONNECTED, "ESP unavailable",
                               status_code=502, details={"host": host, "http_status": 503})
            assert path in ("/status", "/stop"), "Connect must not start or configure the stream"
            return {"protocol": CAMERA_PROTOCOL, "stream_protocol": FRAME_PROTOCOL,
                    "camera_ready": True, "session_active": False,
                    "settings": dict(DEFAULT_CAMERA_SETTINGS), "test_host": host}

        def factory(**kwargs):
            service = RemoteCameraService(**kwargs)
            service._json_requester = requester
            return service

        manager = RemoteCameraManager(registry_path=registry, session_factory=factory)
        for host in ("8.8.8.8", "172.32.0.1", "192.168.1.256", "http://192.168.1.80", "192.168.01.80", "::1"):
            must_reject(lambda host=host: manager.save_profile(host=host, source_id="bad"),
                        ErrorCode.CAMERA_SOURCE_INVALID)
        must_reject(lambda: manager.save_profile(host="192.168.1.80", source_id="bad id"),
                    ErrorCode.CAMERA_SOURCE_INVALID)
        must_reject(lambda: manager.save_profile(host="192.168.1.80", source_id="bad", target_fps=31),
                    ErrorCode.INVALID_REQUEST)
        must_reject(lambda: manager.save_profile(host="192.168.1.80", source_id="bad",
                                                settings={"jpeg_quality": 3}), ErrorCode.INVALID_REQUEST)
        assert not manager.status()["cameras"] and not calls

        host_a, host_b = "192.168.1.80", "192.168.1.81"
        manager.save_profile(host=host_a, source_id="cam_a", target_fps=20,
                             settings={"jpeg_quality": 19})
        must_reject(lambda: manager.save_profile(host=host_a, source_id="duplicate"),
                    ErrorCode.CAMERA_SOURCE_INVALID)
        manager.save_profile(host=host_b, source_id="cam_b", select=False)
        must_reject(lambda: manager.connect(host=host_a, source_id="cam_a"), ErrorCode.CAMERA_NOT_CONNECTED)
        failed = manager.status()
        assert failed["active_source_id"] == "cam_a" and failed["configured"] is False
        assert failed["last_error"] == "ESP unavailable"
        assert failed["device_contract"]["health"]["state"] == "error"
        assert failed["device_contract"]["capabilities"]["camera_input"]["available"] is False
        by_id = {item["source_id"]: item for item in failed["cameras"]}
        assert by_id["cam_a"]["last_error"] == "ESP unavailable"
        assert by_id["cam_b"]["last_error"] is None
        assert by_id["cam_a"]["settings"]["jpeg_quality"] == 19
        assert all(path == "/status" for _, path, _ in calls)
        # Restart retains configuration, not a stale runtime error or a live session.
        reloaded = RemoteCameraManager(registry_path=registry, session_factory=factory)
        saved = reloaded.status()
        assert saved["target_fps"] == 20 and saved["settings"]["jpeg_quality"] == 19
        assert saved["device_contract"]["health"]["state"] == "not_connected"
        assert not reloaded._sessions

        reachable = True
        connected = manager.connect(host=host_a, source_id="cam_a")
        assert connected["configured"] and connected["device_reachable"]
        assert connected["last_error"] is None and not connected["streaming"]
        assert connected["device_contract"]["health"]["state"] == "connected"
        assert connected["device"]["test_host"] == host_a

        # Deterministically change selection during A's network refresh. The
        # returned selected fields must all describe B, not A's old probe result.
        a = manager._sessions["cam_a"]
        original_status = a.status
        def switch_during_refresh(*, refresh_device=False):
            if refresh_device:
                manager.select("cam_b")
            return original_status(refresh_device=False)
        with patch.object(a, "status", side_effect=switch_during_refresh):
            switched = manager.status(refresh_device=True)
        assert switched["active_source_id"] == switched["source_id"] == "cam_b"
        assert switched["host"] == host_b
        assert not switched["configured"] and not switched["device_reachable"]
        assert switched["device"] == {} and switched["last_error"] is None
        assert switched["device_contract"]["source_id"] == "cam_b"
        assert switched["device_contract"]["health"]["state"] == "not_connected"
        by_id = {item["source_id"]: item for item in switched["cameras"]}
        assert by_id["cam_a"]["device_contract"]["health"]["state"] == "connected"
        assert by_id["cam_b"]["device_contract"]["health"]["state"] == "not_connected"
        manager.delete_profile("cam_b")
        assert manager.status()["active_source_id"] == "cam_a"
        manager.disconnect()
        assert manager.status()["device_contract"]["health"]["state"] == "not_connected"
        manager.stop()
        assert all(path in ("/status", "/stop") for _, path, _ in calls)
    print("[PASS] V0555 invalid profiles, saved failed probe, explicit retry, restart, two-camera refresh identity and removal")


if __name__ == "__main__":
    main()
