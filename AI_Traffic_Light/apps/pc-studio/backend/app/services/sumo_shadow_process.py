"""Optional libsumo child process; private local pipe, never a TraCI listener."""
from __future__ import annotations

from importlib.metadata import version
import multiprocessing as mp
import os
from pathlib import Path

from app.services.sumo_shadow_adapter import ShadowAgent, STEP_S
from app.services.sumo_shadow_fixture import PhaseMap, PHASES, native_netconvert

from app.services.sumo_lane_scenarios import choose_permission, observe_lanes
from app.services.sumo_corridor import JUNCTIONS, load_corridor, observe_permissions, validate_phases

PIN = "1.28.0"


def _worker(pipe, root: str, seed: int) -> None:
    _run_worker(pipe, root, seed, controlled=False)


def _controlled_worker(pipe, root: str, seed: int) -> None:
    _run_worker(pipe, root, seed, controlled=True)


def _lane_worker(pipe, root: str, seed: int) -> None:
    _run_worker(pipe, root, seed, controlled=True, lane_scenario=True)


def _corridor_worker(pipe, root: str, seed: int) -> None:
    _run_worker(pipe, root, seed, controlled=True, corridor=True)


def _run_worker(pipe, root: str, seed: int, *, controlled: bool, lane_scenario: bool = False, corridor: bool = False) -> None:
    engine = None
    started = False
    try:
        for name in ("libsumo", "traci", "sumolib", "sumo-data"):
            if version(name) != PIN:
                raise RuntimeError(f"Unexpected {name} version")
        if controlled:
            os.environ["SUMO_HOME"] = str(native_netconvert().parent.parent)
        import libsumo as engine
        engine.start(["sumo", "-n", str(Path(root) / "network.xml"),
                      "-r", str(Path(root) / "routes.xml"), "--seed", str(seed),
                      "--step-length", str(STEP_S), "--time-to-teleport", "-1",
                      "--no-step-log", "true"])
        started = True
        if engine.getVersion()[1].split()[-1] != PIN:
            raise RuntimeError("Unexpected native engine version")
        maps = (load_corridor(Path(root) / "network.xml") if corridor else
                {"C": PhaseMap.load(Path(root) / "network.xml")} if controlled else {})
        if maps and set(engine.trafficlight.getIDList()) != set(maps):
            raise RuntimeError("Unexpected native traffic lights")
        for junction, mapping in maps.items():
            links = engine.trafficlight.getControlledLinks(junction)
            if len(links) != len(mapping.links) or any(
                len(group) != 1 or tuple(group[0][:2]) != expected[:2]
                for group, expected in zip(links, mapping.links)
            ):
                raise RuntimeError("Native controlled links differ from fixture")
            engine.trafficlight.setRedYellowGreenState(junction, "r" * len(links))
        phase_map = maps.get("C")
        pipe.send(("ok", None))
        tick = 0
        while True:
            command = pipe.recv()
            if command == "close":
                break
            state = None
            if corridor:
                if not isinstance(command, tuple) or len(command) != 2 or command[0] != "step":
                    raise ValueError("Invalid corridor command")
                state = observe_permissions(engine, maps, command[1])
                for junction, permission in state.items():
                    engine.trafficlight.setRedYellowGreenState(junction, permission)
                    if engine.trafficlight.getRedYellowGreenState(junction) != permission:
                        raise RuntimeError("Corridor permission readback mismatch")
            elif phase_map is not None:
                if not isinstance(command, tuple) or len(command) != 2 or command[0] != "step" or command[1] not in PHASES:
                    raise ValueError("Invalid shadow phase command")
                occupied = dict(
                    vehicle_inside=any(engine.vehicle.getRoadID(i).startswith(":C_") for i in engine.vehicle.getIDList()),
                    pedestrian_inside=any(engine.person.getRoadID(i) in phase_map.crossing_edges for i in engine.person.getIDList()))
                state = (choose_permission(phase_map, command[1], observe_lanes(engine), **occupied)
                         if lane_scenario else phase_map.state(command[1], **occupied))
                engine.trafficlight.setRedYellowGreenState("C", state)
                if engine.trafficlight.getRedYellowGreenState("C") != state:
                    raise RuntimeError("Shadow permission readback mismatch")
            elif command != "step":
                raise ValueError("Unknown shadow command")
            engine.simulationStep()
            if corridor:
                if any(engine.trafficlight.getRedYellowGreenState(j) != state[j] for j in JUNCTIONS):
                    raise RuntimeError("Corridor permission changed during step")
            elif state is not None and engine.trafficlight.getRedYellowGreenState("C") != state:
                raise RuntimeError("Shadow permission changed during step")
            tick += 1
            if abs(engine.simulation.getTime() - tick * STEP_S) > 1e-6:
                raise RuntimeError("Clock mismatch")
            rows = []
            for kind, domain in (("vehicle", engine.vehicle), ("pedestrian", engine.person)):
                for ident in domain.getIDList():
                    x, y = domain.getPosition(ident)
                    rows.append(ShadowAgent(kind, ident, x, y, domain.getSpeed(ident),
                                            domain.getRoadID(ident)))
            result = (tuple(rows), tuple(engine.simulation.getArrivedIDList()),
                      tuple(engine.simulation.getArrivedPersonIDList()))
            pipe.send(("ok", result + (state,) if controlled else result))
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
    def __init__(self, root: Path, seed: int, *, controlled: bool = False, lane_scenario: bool = False, corridor: bool = False, _target=None, _timeout: float = 15.0, _launcher=None):
        root = root.resolve(strict=True)
        if not all((root / name).is_file() for name in ("network.xml", "routes.xml")):
            raise ValueError("Missing generated shadow fixture")
        if type(seed) is not int or not 0 <= seed <= 2**31 - 1:
            raise ValueError("Invalid seed")
        if (lane_scenario or corridor) and not controlled or lane_scenario and corridor:
            raise ValueError("Lane scenario requires protected phase mapping")
        self._timeout = _timeout
        self._controlled = controlled
        self._corridor = corridor
        self._phase = {j: "all_red" for j in JUNCTIONS} if corridor else "all_red"
        self.last_permission: str | dict[str, str] | None = None
        self._agents = ()
        self.arrived: set[str] = set()
        self.person_arrived: set[str] = set()
        # Optional private launcher for the midblock worker only. Keep existing
        # spawn transport for finite, shadow and corridor sessions.
        if _launcher is not None:
            if not controlled or corridor or lane_scenario or _target is not None:
                raise ValueError("Unsupported private worker launcher")
            self._pipe,self.proc=_launcher(root,seed)
            try:
                self._receive()
            except BaseException:
                self.close()
                raise
            return
        ctx = mp.get_context("spawn")
        self._pipe, child = ctx.Pipe()
        self.proc = ctx.Process(target=_target or (_corridor_worker if corridor else _lane_worker if lane_scenario else _controlled_worker if controlled else _worker), args=(child, str(root), seed), daemon=True)
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

    def set_phase(self, phase: str) -> None:
        if self._corridor or not self._controlled or phase not in PHASES:
            raise ValueError("Invalid virtual shadow phase")
        self._phase = phase

    def set_junction_phases(self, phases: dict[str, str]) -> None:
        if not self._corridor:
            raise ValueError("Not a corridor session")
        self._phase = validate_phases(phases)

    def advance(self) -> None:
        try:
            self._pipe.send(("step", self._phase) if self._controlled else "step")
            result = self._receive()
            self._agents, arrived, persons = result[:3]
            self.last_permission = result[3] if self._controlled else None
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
