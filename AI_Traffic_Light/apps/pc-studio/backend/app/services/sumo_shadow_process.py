"""Optional libsumo child process; private local pipe, never a TraCI listener."""
from __future__ import annotations

from importlib.metadata import version
import multiprocessing as mp
from pathlib import Path

from app.services.sumo_shadow_adapter import ShadowAgent, STEP_S

PIN = "1.28.0"


def _worker(pipe, root: str, seed: int) -> None:
    engine = None
    started = False
    try:
        for name in ("libsumo", "traci", "sumolib", "sumo-data"):
            if version(name) != PIN:
                raise RuntimeError(f"Unexpected {name} version")
        import libsumo as engine
        engine.start(["sumo", "-n", str(Path(root) / "network.xml"),
                      "-r", str(Path(root) / "routes.xml"), "--seed", str(seed),
                      "--step-length", str(STEP_S), "--time-to-teleport", "-1",
                      "--no-step-log", "true"])
        started = True
        if engine.getVersion()[1].split()[-1] != PIN:
            raise RuntimeError("Unexpected native engine version")
        pipe.send(("ok", None))
        tick = 0
        while True:
            command = pipe.recv()
            if command == "close":
                break
            if command != "step":
                raise ValueError("Unknown shadow command")
            engine.simulationStep()
            tick += 1
            if abs(engine.simulation.getTime() - tick * STEP_S) > 1e-6:
                raise RuntimeError("Clock mismatch")
            rows = []
            for kind, domain in (("vehicle", engine.vehicle), ("pedestrian", engine.person)):
                for ident in domain.getIDList():
                    x, y = domain.getPosition(ident)
                    rows.append(ShadowAgent(kind, ident, x, y, domain.getSpeed(ident),
                                            domain.getRoadID(ident)))
            pipe.send(("ok", (tuple(rows), tuple(engine.simulation.getArrivedIDList()),
                              tuple(engine.simulation.getArrivedPersonIDList()))))
    except EOFError:
        pass
    except Exception as exc:
        try:
            pipe.send(("error", f"{type(exc).__name__}: {str(exc)[:300]}"))
        except (OSError, EOFError):
            pass
    finally:
        try:
            if started:
                engine.close()
        finally:
            pipe.close()


class LibsumoSession:
    """Single-owner session for a trusted, generated synthetic fixture only.

    No engine import in the parent, public API, shell, or physical-control path.
    A failed or timed-out request closes/reaps the child before returning.
    """
    def __init__(self, root: Path, seed: int, *, _target=_worker, _timeout: float = 15.0):
        root = root.resolve(strict=True)
        if not all((root / name).is_file() for name in ("network.xml", "routes.xml")):
            raise ValueError("Missing generated shadow fixture")
        if type(seed) is not int or not 0 <= seed <= 2**31 - 1:
            raise ValueError("Invalid seed")
        self._timeout = _timeout
        self._agents = ()
        self.arrived: set[str] = set()
        self.person_arrived: set[str] = set()
        ctx = mp.get_context("spawn")
        self._pipe, child = ctx.Pipe()
        self.proc = ctx.Process(target=_target, args=(child, str(root), seed), daemon=True)
        try:
            self.proc.start()
            child.close()
            self._receive()
        except BaseException:
            self.close()
            raise
        finally:
            child.close()

    def _receive(self):
        if not self._pipe.poll(self._timeout):
            raise TimeoutError("Shadow worker timed out")
        status, payload = self._pipe.recv()
        if status != "ok":
            raise RuntimeError(f"Shadow worker failed: {payload}")
        return payload

    def advance(self) -> None:
        try:
            self._pipe.send("step")
            self._agents, arrived, persons = self._receive()
            self.arrived.update(arrived)
            self.person_arrived.update(persons)
        except BaseException:
            self.close()
            raise

    def agents(self) -> tuple[ShadowAgent, ...]:
        return self._agents

    def close(self) -> None:
        self._agents = ()
        if not self._pipe.closed:
            try:
                self._pipe.send("close")
            except (OSError, EOFError):
                pass
            finally:
                self._pipe.close()
        if self.proc.pid is None:
            return
        self.proc.join(2)
        if self.proc.is_alive():
            self.proc.terminate()
            self.proc.join(2)
        if self.proc.is_alive():
            self.proc.kill()
            self.proc.join(3)
        if self.proc.is_alive():
            raise RuntimeError("Shadow process could not be reaped")
