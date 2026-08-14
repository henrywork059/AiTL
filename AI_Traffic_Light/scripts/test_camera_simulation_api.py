"""Focused FastAPI checks for V016 camera simulation controls."""
from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "apps" / "pc-studio" / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from app.core.exceptions import (  # noqa: E402
    AppError,
    app_error_handler,
    request_validation_error_handler,
    unhandled_exception_handler,
)
from app.core.middleware import RequestContextMiddleware  # noqa: E402
from app.routes.camera import router as camera_router  # noqa: E402
from app.services.camera_frames import camera_frame_service  # noqa: E402


def build_test_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(RequestContextMiddleware)
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, request_validation_error_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
    app.include_router(camera_router, prefix="/api/camera")
    return app


def assert_envelope(response, *, expected_status: int = 200) -> dict:
    assert response.status_code == expected_status, response.text
    payload = response.json()
    assert payload["ok"] is (expected_status < 400)
    assert payload["meta"]["request_id"]
    return payload


def main() -> int:
    camera_frame_service.set_simulation(False)
    client = TestClient(build_test_app())

    start = assert_envelope(client.post("/api/camera/simulation/start"))
    assert start["data"]["simulation_enabled"] is True
    assert start["data"]["simulation_density"] == "normal"

    busy = assert_envelope(
        client.post("/api/camera/simulation/settings", json={"density": "busy"}),
    )
    assert busy["data"]["simulation_density"] == "busy"

    paused = assert_envelope(
        client.post("/api/camera/simulation/settings", json={"paused": True}),
    )
    assert paused["data"]["simulation_paused"] is True
    frame_number = paused["data"]["frame_number"]

    frame = client.get("/api/camera/frame", headers={"X-Request-ID": "req_v016_binary"})
    assert frame.status_code == 200
    assert frame.headers["content-type"].startswith("image/png")
    assert frame.headers["x-request-id"] == "req_v016_binary"
    assert int(frame.headers["x-frame-number"]) == frame_number

    invalid = assert_envelope(
        client.post("/api/camera/simulation/settings", json={"density": "extreme"}),
        expected_status=422,
    )
    assert invalid["error"]["code"] == "ATL-API-002"

    resumed = assert_envelope(
        client.post("/api/camera/simulation/settings", json={"paused": False}),
    )
    assert resumed["data"]["simulation_paused"] is False

    stopped = assert_envelope(client.post("/api/camera/simulation/stop"))
    assert stopped["data"]["simulation_enabled"] is False

    pause_while_stopped = assert_envelope(
        client.post("/api/camera/simulation/settings", json={"paused": True}),
        expected_status=409,
    )
    assert pause_while_stopped["error"]["code"] == "ATL-CAMERA-004"

    print("[PASS] simulation settings API preserves standard envelopes and request IDs")
    print("[PASS] density and pause/resume settings are exposed through thin camera routes")
    print("[PASS] binary camera frame includes X-Request-ID")
    print("[PASS] invalid settings use stable existing error codes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
