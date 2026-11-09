"""The emergency route cannot be confirmed by one positive frame per camera."""
from pathlib import Path
from tempfile import TemporaryDirectory
import time

from test_v0519_emergency_evidence import setup, frame, ingest


def main() -> None:
    with TemporaryDirectory(prefix="aitl-v0521-") as folder:
        clock = [100.0]
        service = setup(Path(folder), clock)
        t0 = int(time.time() * 1000) - 3000
        initial_a = frame("sim_a", 1, t0, ["ambulance"])
        ingest(service, initial_a, frame("sim_b", 1, t0, []))
        # One new positive on the other camera is not longitudinal evidence.
        state = ingest(service, initial_a, frame("sim_b", 2, t0 + 1100, ["ambulance"]))
        assert state["crosswalks"]["cross_b"]["emergency_priority"] is None, state
        # Two new positive frames from B can confirm despite A becoming negative.
        state = ingest(service, frame("sim_a", 2, t0 + 2100, []),
                       frame("sim_b", 3, t0 + 2200, ["ambulance"]))
        assert state["crosswalks"]["cross_b"]["emergency_priority"], state
        assert state["hardware_actuation_enabled"] is False
    print("[PASS] separate cameras cannot manufacture two observations of one ambulance")


if __name__ == "__main__":
    main()
