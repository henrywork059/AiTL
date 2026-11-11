"""V0540: camera uploads reject oversized streamed bodies before full buffering."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import asyncio
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/pc-studio/backend"))

from app.core.error_codes import ErrorCode  # noqa: E402
from app.core.exceptions import AppError  # noqa: E402
from app.routes import camera as camera_route  # noqa: E402
from app.services.camera_frames import MAX_FRAME_BYTES  # noqa: E402


class ChunkedRequest:
    def __init__(self, chunks: list[bytes]) -> None:
        self.chunks = chunks
        self.received = 0
        self.headers = {"content-type": "image/png"}
        self.state = SimpleNamespace(request_id="req_camera_upload_stream")

    async def stream(self):
        for chunk in self.chunks:
            self.received += 1
            yield chunk

    async def body(self):
        raise AssertionError("Camera upload must not buffer an unbounded request body")


def main() -> None:
    received: list[tuple[str, str, bytes]] = []

    def fake_upload(*, source_id: str, content_type: str, content: bytes, validate_decode: bool):
        assert validate_decode is True, "Legacy HTTP uploads must validate complete image decoding"
        received.append((source_id, content_type, content))
        return SimpleNamespace(metadata=lambda: {"size_bytes": len(content)})

    with patch.object(camera_route.camera_frame_service, "store_upload", side_effect=fake_upload):
        small = ChunkedRequest([b"abc", b"de"])
        response = asyncio.run(camera_route.upload_camera_frame(small, source_id="camera_a"))
        assert response["data"]["size_bytes"] == 5
        assert received[-1] == ("camera_a", "image/png", b"abcde")
        assert small.received == 2

        # An HTTP body may arrive as thousands of tiny chunks. Aggregation
        # must preserve bytes without retaining a separate object per chunk.
        fragments = ChunkedRequest([b"a"] * 4096 + [b"", b"b"])
        response = asyncio.run(camera_route.upload_camera_frame(fragments, source_id="camera_fragments"))
        assert response["data"]["size_bytes"] == 4097
        assert received[-1] == ("camera_fragments", "image/png", b"a" * 4096 + b"b")
        assert fragments.received == 4098

        boundary = ChunkedRequest([b"x" * (MAX_FRAME_BYTES - 1), b"z"])
        response = asyncio.run(camera_route.upload_camera_frame(boundary, source_id="camera_b"))
        assert response["data"]["size_bytes"] == MAX_FRAME_BYTES
        assert len(received[-1][2]) == MAX_FRAME_BYTES

        before = len(received)
        oversize = ChunkedRequest([b"x" * MAX_FRAME_BYTES, b"z", b"must-not-consume"])
        try:
            asyncio.run(camera_route.upload_camera_frame(oversize, source_id="camera_c"))
        except AppError as exc:
            assert exc.code == ErrorCode.CAMERA_FRAME_TOO_LARGE
            assert exc.status_code == 413
            assert exc.details["max_size_bytes"] == MAX_FRAME_BYTES
            assert exc.details["size_bytes"] == MAX_FRAME_BYTES + 1
        else:
            raise AssertionError("Oversized camera frame was accepted")
        assert oversize.received == 2, "Stopped reading immediately after size limit"
        assert len(received) == before, "Oversized frame reached the image validator"

    print("[PASS] bounded 8 MiB camera uploads preserve fragmented bodies without per-chunk buffering")


if __name__ == "__main__":
    main()
