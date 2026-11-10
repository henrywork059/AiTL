"""A timed-out inference shutdown must not orphan a still-running worker."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/pc-studio/backend"))
from app.services.multi_camera_inference import MultiCameraInferenceService  # noqa: E402


class DelayedThread:
    def __init__(self) -> None:
        self.alive = True
        self.join_timeout = None

    def is_alive(self) -> bool:
        return self.alive

    def join(self, timeout: float | None = None) -> None:
        self.join_timeout = timeout  # Simulate a timed-out join without sleeping.


def main() -> None:
    service = MultiCameraInferenceService()
    old_worker = DelayedThread()
    service._thread = old_worker
    service._results["camera"] = {"frame": {"timestamp_ms": 1}}
    service._keys["camera"] = ("old",)

    service.stop()
    assert old_worker.join_timeout == 2.0
    assert service._stop.is_set()
    assert service._thread is old_worker, "Live worker reference must survive a timed-out join"
    assert service._results == {} and service._keys == {}

    service.start()
    assert service._thread is old_worker, "Do not create a second worker while the first is alive"
    assert service._stop.is_set(), "The pending stop request must remain set"

    old_worker.alive = False
    service._run = lambda: None  # A completed old worker permits a clean new start.
    service.start()
    new_worker = service._thread
    assert new_worker is not old_worker and not service._stop.is_set()
    new_worker.join(timeout=1.0)
    service.stop()
    assert service._thread is None

    print("[PASS] timed-out inference shutdown retains worker; restart cannot overlap")


if __name__ == "__main__":
    main()
