"""ATL1 packet framing and exact-length socket reads; no session ownership."""
from __future__ import annotations

from dataclasses import dataclass
import socket
import struct
from threading import Event
from typing import BinaryIO

from app.services.camera_frames import MAX_FRAME_BYTES

FRAME_MAGIC = b"ATL1"
FRAME_HEADER = struct.Struct("!4sIII")


@dataclass(frozen=True)
class _FramePacket:
    """One V037/V036-compatible source frame after the fixed binary header is decoded."""

    sequence: int
    source_uptime_ms: int
    content: bytes
    # Local cancellation identity; not part of ATL1 wire data.
    worker_stop: Event | None = None


class _TcpFrameStream:
    """Small socket wrapper with exact-length reads and deterministic shutdown."""

    def __init__(self, sock: socket.socket) -> None:
        self._socket = sock
        self.closed = False

    def read_exact(self, size: int) -> bytes:
        if size <= 0:
            return b""

        buffer = bytearray(size)
        view = memoryview(buffer)
        offset = 0
        while offset < size:
            received = self._socket.recv_into(view[offset:])
            if received == 0:
                if offset == 0:
                    return b""
                raise EOFError("TCP JPEG frame ended before the declared length was received.")
            offset += received
        return bytes(buffer)

    def close(self) -> None:
        if self.closed:
            return
        self.closed = True
        try:
            self._socket.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        self._socket.close()


def _read_exact(stream: BinaryIO, size: int) -> bytes:
    """Read exactly size bytes from real or test stream objects."""
    exact_reader = getattr(stream, "read_exact", None)
    if callable(exact_reader):
        return exact_reader(size)

    chunks = bytearray()
    while len(chunks) < size:
        chunk = stream.read(size - len(chunks))
        if not chunk:
            if not chunks:
                return b""
            raise EOFError("TCP JPEG frame ended before the declared length was received.")
        chunks.extend(chunk)
    return bytes(chunks)


def _encode_frame_packet(
    content: bytes,
    *,
    sequence: int = 1,
    source_uptime_ms: int = 0,
) -> bytes:
    """Test/helper encoder for the V037/V036-compatible fixed-header JPEG stream."""
    return FRAME_HEADER.pack(
        FRAME_MAGIC,
        len(content),
        sequence & 0xFFFFFFFF,
        source_uptime_ms & 0xFFFFFFFF,
    ) + content


def _read_frame_packet(stream: BinaryIO) -> _FramePacket | None:
    header = _read_exact(stream, FRAME_HEADER.size)
    if not header:
        return None
    if len(header) != FRAME_HEADER.size:
        raise EOFError("TCP JPEG frame header was incomplete.")

    magic, payload_length, sequence, source_uptime_ms = FRAME_HEADER.unpack(header)
    if magic != FRAME_MAGIC:
        raise ValueError("ESP stream protocol magic did not match AiTL TCP JPEG v1.")
    if payload_length <= 0 or payload_length > MAX_FRAME_BYTES:
        raise ValueError("ESP TCP JPEG payload length is outside the accepted frame size.")

    content = _read_exact(stream, payload_length)
    if len(content) != payload_length:
        raise EOFError("ESP TCP JPEG payload ended before the declared length was received.")
    if not content.startswith(b"\xff\xd8") or not content.endswith(b"\xff\xd9"):
        raise ValueError("ESP TCP frame did not contain a complete JPEG image.")

    return _FramePacket(
        sequence=sequence,
        source_uptime_ms=source_uptime_ms,
        content=content,
    )
