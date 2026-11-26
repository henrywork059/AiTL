"""Explicitly selected isolated corridor session, never a camera or live signal owner."""
from pathlib import Path
from tempfile import TemporaryDirectory

from app.services.sumo_corridor import generate_corridor
from app.services.sumo_shadow_process import LibsumoSession


class CorridorSession(LibsumoSession):
    def __init__(self, seed: int):
        self._temp = TemporaryDirectory(prefix="mesh-corridor-")
        root = Path(self._temp.name)
        try:
            generate_corridor(root, seed)
            super().__init__(root, seed, controlled=True, corridor=True)
        except BaseException:
            self._temp.cleanup()
            raise

    def close(self) -> None:
        try:
            super().close()
        finally:
            self._temp.cleanup()
