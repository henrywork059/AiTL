"""Deterministic ATL1 framing checks (no ESP or external socket)."""
from io import BytesIO
from pathlib import Path
import sys
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/pc-studio/backend"))
from app.services import camera_tcp_transport as tcp


class Fragmented(BytesIO):
    def read(self, size=-1):
        return super().read(min(size, 3))


class FragmentedSocket:
    def __init__(self, content):
        self.data = BytesIO(content)
        self.shutdown = Mock(side_effect=OSError)
        self.close = Mock()

    def recv_into(self, buffer):
        content = self.data.read(min(len(buffer), 3))
        buffer[:len(content)] = content
        return len(content)


def rejects(error, content):
    try:
        tcp._read_frame_packet(Fragmented(content))
    except error:
        return
    raise AssertionError(f"Expected {error.__name__}")


def main():
    jpeg = b"\xff\xd8" + b"payload" * 10 + b"\xff\xd9"
    wire = tcp._encode_frame_packet(jpeg, sequence=0x100000001, source_uptime_ms=123)
    stream = Fragmented(wire + wire)
    for _ in range(2):
        packet = tcp._read_frame_packet(stream)
        assert (packet.sequence, packet.source_uptime_ms, packet.content, packet.worker_stop) == (1, 123, jpeg, None)
    assert tcp._read_frame_packet(stream) is None
    print("[PASS] fragmented framing, two packets, uint32 wrap and clean EOF")
    sock = FragmentedSocket(wire)
    wrapped = tcp._TcpFrameStream(sock)
    assert wrapped.read_exact(0) == b""
    assert tcp._read_frame_packet(wrapped).content == jpeg
    assert tcp._read_frame_packet(wrapped) is None
    wrapped.close()
    wrapped.close()
    sock.shutdown.assert_called_once()
    sock.close.assert_called_once()
    assert wrapped.closed
    print("[PASS] exact socket read and idempotent shutdown on shutdown error")
    rejects(EOFError, wire[:5])
    rejects(EOFError, wire[:-1])
    rejects(ValueError, b"NOPE" + wire[4:])
    rejects(ValueError, tcp.FRAME_HEADER.pack(tcp.FRAME_MAGIC, 0, 1, 0))
    rejects(ValueError, tcp.FRAME_HEADER.pack(tcp.FRAME_MAGIC, tcp.MAX_FRAME_BYTES + 1, 1, 0))
    rejects(ValueError, tcp._encode_frame_packet(b"bad JPEG"))
    try:
        tcp._read_frame_packet(tcp._TcpFrameStream(FragmentedSocket(wire[:-1])))
    except EOFError:
        pass
    else:
        raise AssertionError("Partial socket payload must raise EOFError")
    print("[PASS] truncated header/payload, invalid magic/length/JPEG and partial socket payload")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
